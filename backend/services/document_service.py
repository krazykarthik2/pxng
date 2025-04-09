import uuid
from datetime import datetime
from typing import Dict, List, Any, BinaryIO, Optional
import PyPDF2
import docx
from ..database.neo4j_client import Neo4jClient
from ..database.vector_store import VectorStore
from ..utils.embeddings import EmbeddingService

class DocumentService:
    def __init__(
        self, 
        neo4j_client: Neo4jClient,
        vector_store: VectorStore,
        embedding_service: EmbeddingService
    ):
        self.neo4j_client = neo4j_client
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def upload_document(
        self,
        file_obj: BinaryIO,
        filename: str,
        owner_id: str,
        context_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Dict[str, Any]:
        # 1. Extract text from document
        file_extension = filename.split('.')[-1].lower()
        if file_extension == 'pdf':
            text = self._extract_text_from_pdf(file_obj)
        elif file_extension in ['docx', 'doc']:
            text = self._extract_text_from_docx(file_obj)
        elif file_extension in ['txt', 'md']:
            text = file_obj.read().decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # 2. Chunk the document
        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        
        # 3. Generate embeddings for chunks
        embeddings = self.embedding_service.get_batch_embeddings(chunks)
        
        # 4. Store document in Neo4j
        doc_id = str(uuid.uuid4())
        document = self.neo4j_client.add_document(
            doc_id=doc_id,
            name=filename,
            doc_type=file_extension,
            owner_id=owner_id,
            context_id=context_id,
            vector_id=f"doc-{doc_id}"  # Main document reference
        )
        
        # 5. Store document chunks in vector store
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"chunk-{doc_id}-{i}"
            metadata = {
                "document_id": doc_id,
                "document_name": filename,
                "chunk_index": i,
                "content": chunk,
                "type": "document_chunk",
                "context_id": context_id,
                "owner_id": owner_id,
                "timestamp": datetime.now().isoformat()
            }
            self.vector_store.add_vector(chunk_id, embedding, metadata)
        
        return {
            "id": doc_id,
            "name": filename,
            "type": file_extension,
            "owner_id": owner_id,
            "context_id": context_id,
            "chunk_count": len(chunks),
            "upload_timestamp": document.get("uploaded_at")
        }
    
    def _extract_text_from_pdf(self, file_obj: BinaryIO) -> str:
        pdf_reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def _extract_text_from_docx(self, file_obj: BinaryIO) -> str:
        doc = docx.Document(file_obj)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    
    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to find a period, newline, or space to break at
            if end < len(text):
                for breakpoint in ['.', '\n', ' ']:
                    pos = text.rfind(breakpoint, start, end)
                    if pos > start:
                        end = pos + 1
                        break
                        
            chunks.append(text[start:end])
            start = end - chunk_overlap
            
        return chunks
    
    def share_document(
        self,
        doc_id: str,
        owner_id: str,
        target_id: str,
        target_type: str,  # 'user', 'group', or 'community'
        permission: str = 'read'  # 'read', 'write', 'admin'
    ) -> bool:
        # Check if the user is the owner
        owner_check = self.neo4j_client._run_query(
            """
            MATCH (u:User {id: $owner_id})-[r:CAN_ACCESS]->(d:Document {id: $doc_id})
            WHERE r.permission = 'owner'
            RETURN count(u) > 0 as is_owner
            """,
            {"owner_id": owner_id, "doc_id": doc_id}
        )
        
        if not owner_check or not owner_check[0]["is_owner"]:
            return False
            
        # Share with target based on type
        if target_type == 'user':
            query = """
            MATCH (u:User {id: $target_id}), (d:Document {id: $doc_id})
            CREATE (u)-[:CAN_ACCESS {permission: $permission}]->(d)
            RETURN count(u) > 0 as success
            """
        else:
            # For groups and communities, share with all members
            query = """
            MATCH (target {id: $target_id}), (d:Document {id: $doc_id})
            WHERE target:Group OR target:Community
            CREATE (target)-[:CAN_ACCESS {permission: $permission}]->(d)
            WITH target, d
            MATCH (u:User)-[:MEMBER_OF]->(target)
            CREATE (u)-[:CAN_ACCESS {permission: $permission}]->(d)
            RETURN count(u) > 0 as success
            """
            
        result = self.neo4j_client._run_query(
            query,
            {"target_id": target_id, "doc_id": doc_id, "permission": permission}
        )
        
        return result and result[0]["success"]