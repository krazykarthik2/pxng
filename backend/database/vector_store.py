import faiss
import numpy as np
import json
import os
from typing import List, Dict, Any, Tuple

class VectorStore:
    def __init__(self, dimension: int, index_path: str = None):
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = index_path.replace('.index', '.json') if index_path else None
        
        if index_path and os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.index = faiss.IndexFlatL2(dimension)
            self.metadata = {}
    
    def save(self):
        if self.index_path:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f)
    
    def add_vector(self, vector_id: str, vector: np.ndarray, metadata: Dict[str, Any] = None):
        if vector_id in self.metadata:
            # Update existing vector
            idx = self.metadata[vector_id]['index']
            # Faiss doesn't support direct updates, so we need to remove and re-add
            # This is a simplified approach - in production, batch updates would be better
            self._update_vector(idx, vector)
        else:
            # Add new vector
            idx = self.index.ntotal
            self.index.add(np.array([vector], dtype=np.float32))
            
        # Update metadata
        self.metadata[vector_id] = {
            'index': idx,
            'metadata': metadata or {}
        }
        
        # Save changes
        self.save()
        return vector_id
    
    def _update_vector(self, idx: int, vector: np.ndarray):
        # This is a simplified approach - in production, use batch operations
        # or a different index type that supports updates
        temp_index = faiss.IndexFlatL2(self.dimension)
        for i in range(self.index.ntotal):
            if i != idx:
                v = self.index.reconstruct(i)
                temp_index.add(np.array([v], dtype=np.float32))
            else:
                temp_index.add(np.array([vector], dtype=np.float32))
        self.index = temp_index
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple[str, float, Dict]]:
        # Search the index
        distances, indices = self.index.search(np.array([query_vector], dtype=np.float32), k)
        
        # Map results to vector_ids and metadata
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # -1 indicates no match found
                # Find vector_id by index
                vector_id = None
                for vid, data in self.metadata.items():
                    if data['index'] == idx:
                        vector_id = vid
                        break
                
                if vector_id:
                    results.append((
                        vector_id, 
                        float(distances[0][i]),
                        self.metadata[vector_id]['metadata']
                    ))
                    
        return results
    
    def delete_vector(self, vector_id: str):
        if vector_id in self.metadata:
            # Remove from metadata
            idx = self.metadata[vector_id]['index']
            del self.metadata[vector_id]
            
            # Rebuild index without this vector
            vectors = []
            for vid, data in self.metadata.items():
                if data['index'] > idx:
                    # Update indices for vectors that came after the deleted one
                    self.metadata[vid]['index'] -= 1
                vector = self.index.reconstruct(data['index'])
                vectors.append(vector)
            
            # Recreate index
            self.index = faiss.IndexFlatL2(self.dimension)
            if vectors:
                self.index.add(np.array(vectors, dtype=np.float32))
            
            # Save changes
            self.save()
            return True
        return False