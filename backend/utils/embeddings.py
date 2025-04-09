import numpy as np
from typing import List, Dict, Any
import openai
import hashlib
import json

class EmbeddingService:
    def __init__(self, openai_api_key: str, embedding_model: str = "text-embedding-3-small"):
        self.api_key = openai_api_key
        self.model = embedding_model
        openai.api_key = openai_api_key
        
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text using OpenAI's embedding API"""
        response = openai.Embedding.create(
            model=self.model,
            input=text
        )
        embedding = response["data"][0]["embedding"]
        return np.array(embedding, dtype=np.float32)
    
    def get_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings for multiple texts in one API call"""
        response = openai.Embedding.create(
            model=self.model,
            input=texts
        )
        embeddings = [np.array(item["embedding"], dtype=np.float32) 
                     for item in response["data"]]
        return embeddings
    
    def generate_vector_id(self, content: Dict[str, Any], prefix: str = "vec") -> str:
        """Generate a deterministic ID for a vector based on its content"""
        content_str = json.dumps(content, sort_keys=True)
        hash_obj = hashlib.sha256(content_str.encode())
        return f"{prefix}-{hash_obj.hexdigest()[:16]}"