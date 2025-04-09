import uuid
from typing import Dict, List, Any, Optional
from ..database.neo4j_client import Neo4jClient
from ..database.vector_store import VectorStore
from ..utils.embeddings import EmbeddingService

class ChatService:
    def __init__(
        self, 
        neo4j_client: Neo4jClient,
        vector_store: VectorStore,
        embedding_service: EmbeddingService
    ):
        self.neo4j_client = neo4j_client
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def send_message(
        self, 
        content: str,
        sender_id: str,
        recipient_id: str,
        recipient_type: str  # 'user', 'group', or 'community'
    ) -> Dict[str, Any]:
        # 1. Generate embedding for message
        embedding = self.embedding_service.get_embedding(content)
        
        # 2. Store embedding in vector store
        message_id = str(uuid.uuid4())
        vector_id = self.embedding_service.generate_vector_id(
            {"content": content, "message_id": message_id}, 
            prefix="msg"
        )
        
        # Get context ID based on recipient type
        context_id = None
        if recipient_type in ['group', 'community']:
            context = self.neo4j_client._run_query(
                f"""
                MATCH (n:{recipient_type.capitalize()} {{id: $id}})-[:HAS_CONTEXT]->(c:Context)
                RETURN c.id as context_id
                """,
                {"id": recipient_id}
            )
            if context:
                context_id = context[0]["context_id"]
        
        # Store embedding with metadata
        metadata = {
            "message_id": message_id,
            "content": content,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "recipient_type": recipient_type,
            "type": "message",
            "timestamp": datetime.now().isoformat(),
            "context_id": context_id
        }
        self.vector_store.add_vector(vector_id, embedding, metadata)
        
        # 3. Store message in Neo4j
        message = self.neo4j_client.create_message(
            message_id=message_id,
            content=content,
            sender_id=sender_id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            vector_id=vector_id
        )
        
        return {
            "id": message_id,
            "content": content,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "recipient_type": recipient_type,
            "vector_id": vector_id,
            "timestamp": message.get("created_at")
        }
    
    def get_messages(
        self,
        user_id: str,
        recipient_id: str,
        recipient_type: str,
        limit: int = 50,
        before_timestamp: str = None
    ) -> List[Dict[str, Any]]:
        # Query to get messages for a specific chat
        query_params = {
            "user_id": user_id,
            "recipient_id": recipient_id,
            "limit": limit
        }
        
        timestamp_condition = ""
        if before_timestamp:
            timestamp_condition = "AND m.created_at < datetime($before_timestamp)"
            query_params["before_timestamp"] = before_timestamp
            
        if recipient_type == "user":
            # Direct messages between two users
            query = f"""
            MATCH (m:Message)-[:SENT_BY]->(sender:User)
            MATCH (m)-[:SENT_TO]->(recipient:User)
            WHERE 
                ((sender.id = $user_id AND recipient.id = $recipient_id) OR
                (sender.id = $recipient_id AND recipient.id = $user_id))
                {timestamp_condition}
            RETURN 
                m.id as message_id,
                m.content as content,
                sender.id as sender_id,
                recipient.id as recipient_id,
                m.created_at as timestamp,
                m.vector_id as vector_id
            ORDER BY m.created_at DESC
            LIMIT $limit
            """
        else:
            # Group or community messages
            query = f"""
            MATCH (m:Message)-[:SENT_BY]->(sender:User)
            MATCH (m)-[:SENT_TO]->(recipient)
            WHERE 
                recipient.id = $recipient_id AND
                EXISTS( (sender)-[:MEMBER_OF]->(recipient) ) AND
                EXISTS( (:User {{id: $user_id}})-[:MEMBER_OF]->(recipient) )
                {timestamp_condition}
            RETURN 
                m.id as message_id,
                m.content as content,
                sender.id as sender_id,
                recipient.id as recipient_id,
                m.created_at as timestamp,
                m.vector_id as vector_id
            ORDER BY m.created_at DESC
            LIMIT $limit
            """
            
        result = self.neo4j_client._run_query(query, query_params)
        
        # Format messages
        messages = [{
            "id": msg["message_id"],
            "content": msg["content"],
            "sender_id": msg["sender_id"],
            "recipient_id": msg["recipient_id"],
            "timestamp": msg["timestamp"],
            "vector_id": msg["vector_id"]
        } for msg in result]
        
        return messages