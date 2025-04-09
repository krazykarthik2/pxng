
from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional

USER_NODE = "User"
GROUP_NODE = "Group"
COMMUNITY_NODE = "Community"
MESSAGE_NODE = "Message"
DOCUMENT_NODE = "Document"
CONTEXT_NODE = "Context"

# Relationship types
MEMBER_OF = "MEMBER_OF"
BELONGS_TO = "BELONGS_TO"
SENT_BY = "SENT_BY"
SENT_TO = "SENT_TO"
HAS_CONTEXT = "HAS_CONTEXT"
CAN_ACCESS = "CAN_ACCESS"
REFERENCES = "REFERENCES"
CONNECTED_TO = "CONNECTED_TO"

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
        
    def _run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def create_user(self, user_id: str, properties: Dict[str, Any]) -> Dict:
        query = """
        CREATE (u:User {id: $user_id, name: $name, email: $email, created_at: datetime()})
        RETURN u
        """
        params = {"user_id": user_id, **properties}
        result = self._run_query(query, params)
        return result[0]["u"] if result else None
    
    def create_group(self, group_id: str, name: str, creator_id: str) -> Dict:
        query = """
        MATCH (creator:User {id: $creator_id})
        CREATE (g:Group {id: $group_id, name: $name, created_at: datetime(), created_by: $creator_id})
        CREATE (g)-[:HAS_CONTEXT]->(:Context {id: $context_id, created_at: datetime()})
        CREATE (creator)-[:MEMBER_OF {role: 'admin', joined_at: datetime()}]->(g)
        RETURN g
        """
        params = {
            "group_id": group_id,
            "name": name,
            "creator_id": creator_id,
            "context_id": f"context-{group_id}"
        }
        result = self._run_query(query, params)
        return result[0]["g"] if result else None
        
    def create_community(self, community_id: str, name: str, creator_id: str) -> Dict:
        query = """
        MATCH (creator:User {id: $creator_id})
        CREATE (c:Community {id: $community_id, name: $name, created_at: datetime(), created_by: $creator_id})
        CREATE (c)-[:HAS_CONTEXT]->(:Context {id: $context_id, created_at: datetime()})
        CREATE (creator)-[:MEMBER_OF {role: 'admin', joined_at: datetime()}]->(c)
        RETURN c
        """
        params = {
            "community_id": community_id,
            "name": name,
            "creator_id": creator_id,
            "context_id": f"context-{community_id}"
        }
        result = self._run_query(query, params)
        return result[0]["c"] if result else None
    
    def add_user_to_group(self, user_id: str, group_id: str, role: str = "member") -> bool:
        query = """
        MATCH (u:User {id: $user_id}), (g:Group {id: $group_id})
        CREATE (u)-[:MEMBER_OF {role: $role, joined_at: datetime()}]->(g)
        RETURN u, g
        """
        params = {"user_id": user_id, "group_id": group_id, "role": role}
        result = self._run_query(query, params)
        return bool(result)
    
    def create_message(self, message_id: str, content: str, sender_id: str, 
                      recipient_id: str, recipient_type: str, vector_id: str) -> Dict:
        query = """
        MATCH (sender:User {id: $sender_id})
        MATCH (recipient) WHERE ID(recipient) = $recipient_id 
        AND (recipient:User OR recipient:Group OR recipient:Community)
        CREATE (m:Message {
            id: $message_id, 
            content: $content, 
            created_at: datetime(),
            vector_id: $vector_id
        })
        CREATE (m)-[:SENT_BY]->(sender)
        CREATE (m)-[:SENT_TO]->(recipient)
        RETURN m
        """
        params = {
            "message_id": message_id,
            "content": content,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "vector_id": vector_id
        }
        result = self._run_query(query, params)
        return result[0]["m"] if result else None
    
    def add_document(self, doc_id: str, name: str, doc_type: str, 
                    owner_id: str, context_id: str, vector_id: str) -> Dict:
        query = """
        MATCH (owner:User {id: $owner_id})
        MATCH (context:Context {id: $context_id})
        CREATE (d:Document {
            id: $doc_id,
            name: $name,
            type: $doc_type,
            uploaded_at: datetime(),
            vector_id: $vector_id
        })
        CREATE (d)-[:BELONGS_TO]->(context)
        CREATE (owner)-[:CAN_ACCESS {permission: 'owner'}]->(d)
        RETURN d
        """
        params = {
            "doc_id": doc_id,
            "name": name,
            "doc_type": doc_type,
            "owner_id": owner_id,
            "context_id": context_id,
            "vector_id": vector_id
        }
        result = self._run_query(query, params)
        return result[0]["d"] if result else None
    
    def get_user_accessible_contexts(self, user_id: str) -> List[Dict]:
        query = """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g)
        MATCH (g)-[:HAS_CONTEXT]->(c:Context)
        RETURN c
        UNION
        MATCH (u:User {id: $user_id})-[:CAN_ACCESS]->(d:Document)
        MATCH (d)-[:BELONGS_TO]->(c:Context)
        RETURN c
        """
        params = {"user_id": user_id}
        return self._run_query(query, params)
    
    def get_relationships_in_group(self, group_id: str) -> List[Dict]:
        query = """
        MATCH (g:Group {id: $group_id})
        MATCH (u1:User)-[:MEMBER_OF]->(g)
        MATCH (u2:User)-[:MEMBER_OF]->(g)
        WHERE u1.id < u2.id  // To avoid duplicate relationships
        MATCH path = (u1)-[r*..3]-(u2)
        RETURN u1, u2, relationships(path) as relationships
        """
        params = {"group_id": group_id}
        return self._run_query(query, params)