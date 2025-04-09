from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os
import dotenv
import uuid
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel
from database.neo4j_client import Neo4jClient
from database.vector_store import VectorStore
from utils.embeddings import EmbeddingService
# Load environment variables
dotenv.load_dotenv()

app = FastAPI(title="Chat App with Neo4j and RAG")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients and services
neo4j_client = Neo4jClient(
    uri=os.getenv("NEO4J_URI"),
    user=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

vector_store = VectorStore(
    dimension=1536,  # For OpenAI embeddings
    index_path=os.getenv("FAISS_INDEX_PATH", "data/vectors.index")
)

embedding_service = EmbeddingService(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
)

from services.chat_service import ChatService
from services.document_service import DocumentService   
from services.rag_service    import RAGService
# Initialize services
chat_service = ChatService(neo4j_client, vector_store, embedding_service)
document_service = DocumentService(neo4j_client, vector_store, embedding_service)
rag_service = RAGService(
    neo4j_client, 
    vector_store, 
    embedding_service,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    llm_model=os.getenv("LLM_MODEL", "gpt-3.5-turbo")
)

# JWT Authentication
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 60 * 24  # 24 hours

# Models
class User(BaseModel):
    email: str
    name: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class MessageCreate(BaseModel):
    content: str
    recipient_id: str
    recipient_type: str

class QueryRequest(BaseModel):
    query: str
    context_ids: Optional[List[str]] = None

# Auth dependency
def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
            
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Routes
@app.post("/api/auth/register", response_model=Token)
async def register(user: User):
    # Check if user exists
    existing_user = neo4j_client._run_query(
        "MATCH (u:User {email: $email}) RETURN u",
        {"email": user.email}
    )
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password (in production, use proper password hashing)
    hashed_password = user.password  # Replace with proper hashing
    
    # Create user
    user_id = str(uuid.uuid4())
    neo4j_client.create_user(
        user_id=user_id,
        properties={
            "name": user.name,
            "email": user.email,
            "password": hashed_password
        }
    )
    
    # Create token
    token_data = {
        "sub": user_id,
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION)
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
async def login(email: str = Form(...), password: str = Form(...)):
    # Find user
    user_result = neo4j_client._run_query(
        "MATCH (u:User {email: $email}) RETURN u.id as id, u.password as password",
        {"email": email}
    )
    
    if not user_result or user_result[0]["password"] != password:  # In production, use proper password verification
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create token
    user_id = user_result[0]["id"]
    token_data = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION)
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/groups")
async def create_group(name: str = Form(...), user_id: str = Depends(get_current_user)):
    group_id = str(uuid.uuid4())
    group = neo4j_client.create_group(
        group_id=group_id,
        name=name,
        creator_id=user_id
    )
    return {"id": group_id, "name": name, "created_by": user_id}

@app.post("/api/communities")
async def create_community(name: str = Form(...), user_id: str = Depends(get_current_user)):
    community_id = str(uuid.uuid4())
    community = neo4j_client.create_community(
        community_id=community_id,
        name=name,
        creator_id=user_id
    )
    return {"id": community_id, "name": name, "created_by": user_id}

@app.post("/api/groups/{group_id}/members")
async def add_member_to_group(
    group_id: str, 
    member_id: str = Form(...), 
    role: str = Form("member"),
    user_id: str = Depends(get_current_user)
):
    # Check if user is admin of the group
    admin_check = neo4j_client._run_query(
        """
        MATCH (u:User {id: $user_id})-[r:MEMBER_OF]->(g:Group {id: $group_id})
        WHERE r.role = 'admin'
        RETURN count(u) > 0 as is_admin
        """,
        {"user_id": user_id, "group_id": group_id}
    )
    
    if not admin_check or not admin_check[0]["is_admin"]:
        raise HTTPException(status_code=403, detail="Only group admins can add members")
    
    # Add member
    success = neo4j_client.add_user_to_group(member_id, group_id, role)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add member")
        
    return {"success": True}

@app.post("/api/messages")
async def send_message(
    message: MessageCreate,
    user_id: str = Depends(get_current_user)
):
    # Verify user can send message to recipient
    if message.recipient_type in ["group", "community"]:
        member_check = neo4j_client._run_query(
            f"""
            MATCH (u:User {{id: $user_id}})-[:MEMBER_OF]->(r:{message.recipient_type.capitalize()} {{id: $recipient_id}})
            RETURN count(u) > 0 as is_member
            """,
            {"user_id": user_id, "recipient_id": message.recipient_id}
        )
        
        if not member_check or not member_check[0]["is_member"]:
            raise HTTPException(
                status_code=403, 
                detail=f"You must be a member of the {message.recipient_type} to send messages"
            )
    
    # Send message
    result = chat_service.send_message(
        content=message.content,
        sender_id=user_id,
        recipient_id=message.recipient_id,
        recipient_type=message.recipient_type
    )
    
    return result

@app.get("/api/messages")
async def get_messages(
    recipient_id: str,
    recipient_type: str,
    limit: int = 50,
    before: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    # Check access
    if recipient_type in ["group", "community"]:
        member_check = neo4j_client._run_query(
            f"""
            MATCH (u:User {{id: $user_id}})-[:MEMBER_OF]->(r:{recipient_type.capitalize()} {{id: $recipient_id}})
            RETURN count(u) > 0 as is_member
            """,
            {"user_id": user_id, "recipient_id": recipient_id}
        )
        
        if not member_check or not member_check[0]["is_member"]:
            raise HTTPException(
                status_code=403, 
                detail=f"You must be a member of the {recipient_type} to view messages"
            )
    
    # Get messages
    messages = chat_service.get_messages(
        user_id=user_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        limit=limit,
        before_timestamp=before
    )
    
    return messages

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    context_id: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    # Verify user has access to the context
    context_check = neo4j_client._run_query(
        """
        MATCH (c:Context {id: $context_id})
        MATCH (g)-[:HAS_CONTEXT]->(c)
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g)
        RETURN count(u) > 0 as has_access
        """,
        {"context_id": context_id, "user_id": user_id}
    )
    
    if not context_check or not context_check[0]["has_access"]:
        raise HTTPException(status_code=403, detail="You don't have access to this context")
    
    # Upload document
    result = document_service.upload_document(
        file_obj=file.file,
        filename=file.filename,
        owner_id=user_id,
        context_id=context_id
    )
    
    return result

@app.post("/api/documents/{doc_id}/share")
async def share_document(
    doc_id: str,
    target_id: str = Form(...),
    target_type: str = Form(...),
    permission: str = Form("read"),
    user_id: str = Depends(get_current_user)
):
    # Share document
    success = document_service.share_document(
        doc_id=doc_id,
        owner_id=user_id,
        target_id=target_id,
        target_type=target_type,
        permission=permission
    )
    
    if not success:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to share this document"
        )
        
    return {"success": True}

@app.post("/api/rag/query")
async def query_rag(
    query_request: QueryRequest,
    user_id: str = Depends(get_current_user)
):
    # Query RAG system
    response = rag_service.answer_query(
        query=query_request.query,
        user_id=user_id,
        context_ids=query_request.context_ids
    )
    
    return response

@app.get("/api/contexts")
async def get_contexts(user_id: str = Depends(get_current_user)):
    # Get all contexts accessible to the user
    contexts = neo4j_client.get_user_accessible_contexts(user_id)
    return contexts

@app.get("/api/groups/{group_id}/relationships")
async def get_group_relationships(
    group_id: str,
    user_id: str = Depends(get_current_user)
):
    # Check if user is member of the group
    member_check = neo4j_client._run_query(
        """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group {id: $group_id})
        RETURN count(u) > 0 as is_member
        """,
        {"user_id": user_id, "group_id": group_id}
    )
    
    if not member_check or not member_check[0]["is_member"]:
        raise HTTPException(
            status_code=403, 
            detail="You must be a member of the group to view relationships"
        )
    
    # Get relationships
    relationships = neo4j_client.get_relationships_in_group(group_id)
    return relationships

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)