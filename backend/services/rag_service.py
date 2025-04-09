from typing import List, Dict, Any, Optional
import openai
from ..database.neo4j_client import Neo4jClient
from ..database.vector_store import VectorStore
from ..utils.embeddings import EmbeddingService

class RAGService:
    def __init__(
        self, 
        neo4j_client: Neo4jClient,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        openai_api_key: str,
        llm_model: str = "gpt-3.5-turbo"
    ):
        self.neo4j_client = neo4j_client
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        self.llm_model = llm_model
        
    def answer_query(self, query: str, user_id: str, 
                    context_ids: List[str] = None, 
                    max_context_items: int = 10) -> Dict[str, Any]:
        # 1. Get query embedding
        query_embedding = self.embedding_service.get_embedding(query)
        
        # 2. If no specific context_ids provided, get all contexts accessible to user
        if not context_ids:
            user_contexts = self.neo4j_client.get_user_accessible_contexts(user_id)
            context_ids = [ctx["c"]["id"] for ctx in user_contexts]
        
        # 3. Search vector store for relevant content across accessible contexts
        relevant_items = self._search_across_contexts(
            query_embedding, context_ids, max_items=max_context_items
        )
        
        # 4. Create prompt with context
        prompt = self._create_rag_prompt(query, relevant_items)
        
        # 5. Generate response using LLM
        response = self._generate_response(prompt)
        
        # 6. Return response with sources
        return {
            "answer": response,
            "sources": [item["metadata"] for item in relevant_items]
        }
    
    def _search_across_contexts(
        self, 
        query_embedding: Any, 
        context_ids: List[str],
        max_items: int = 10
    ) -> List[Dict[str, Any]]:
        # Search vector store
        all_results = self.vector_store.search(query_embedding, k=max_items*2)
        
        # Filter results by context
        filtered_results = []
        for vector_id, score, metadata in all_results:
            if metadata.get("context_id") in context_ids:
                filtered_results.append({
                    "vector_id": vector_id,
                    "score": score,
                    "metadata": metadata,
                    "content": metadata.get("content", "")
                })
                
                if len(filtered_results) >= max_items:
                    break
                    
        return filtered_results
    
    def _create_rag_prompt(self, query: str, context_items: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join([
            f"[{item['metadata'].get('type', 'Content')}]: {item['content']}"
            for item in context_items
        ])
        
        return f"""Answer the following query based on the context provided below. 
If the context doesn't contain relevant information to answer the query, 
say that you don't have enough information and suggest what might help.

Context:
{context_text}

Query: {query}

Answer:"""
    
    def _generate_response(self, prompt: str) -> str:
        response = openai.ChatCompletion.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers queries based on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content