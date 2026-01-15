"""
Milvus vector database client module for storing and searching embeddings.
"""

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
    MilvusException
)
from typing import List, Dict, Optional, Any
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class MilvusClient:
    """Client for Milvus vector database operations."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "vector_knowledge_base",
        embedding_dim: int = 4096
    ):
        """
        Initialize Milvus client.
        
        Args:
            host: Milvus host address
            port: Milvus port
            collection_name: Name of the collection
            embedding_dim: Dimension of embedding vectors
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.collection = None
        self._connect()
        self._ensure_collection()
    
    def _connect(self):
        """Connect to Milvus server."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            # Check if collection exists
            if utility.has_collection(self.collection_name):
                logger.info(f"Collection '{self.collection_name}' already exists")
                self.collection = Collection(self.collection_name)
                
                # Verify embedding dimension matches
                schema = self.collection.schema
                for field in schema.fields:
                    if field.name == "embedding":
                        # Get dimension from field params
                        existing_dim = None
                        if hasattr(field, 'params') and field.params:
                            existing_dim = field.params.get('dim')
                        elif hasattr(field, 'dim'):
                            existing_dim = field.dim
                        
                        if existing_dim and existing_dim != self.embedding_dim:
                            error_msg = (
                                f"Dimension mismatch: Collection '{self.collection_name}' "
                                f"has dimension {existing_dim}, but expected {self.embedding_dim}. "
                                f"Please drop the collection and recreate it, or set EMBEDDING_DIMENSION={existing_dim} "
                                f"in your .env file."
                            )
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        elif existing_dim:
                            logger.info(f"Collection dimension verified: {existing_dim}")
            else:
                logger.info(f"Creating collection '{self.collection_name}' with dimension {self.embedding_dim}")
                self._create_collection()
            
            # Load collection for use
            self.collection.load()
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def _create_collection(self):
        """Create a new collection with schema."""
        # Define fields
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=100
            ),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=65535
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.embedding_dim
            ),
            FieldSchema(
                name="metadata",
                dtype=DataType.VARCHAR,
                max_length=65535
            ),
            FieldSchema(
                name="source_file",
                dtype=DataType.VARCHAR,
                max_length=500
            ),
            FieldSchema(
                name="created_at",
                dtype=DataType.VARCHAR,
                max_length=100
            )
        ]
        
        # Create schema
        schema = CollectionSchema(
            fields=fields,
            description="Vector Knowledge Base Collection"
        )
        
        # Create collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # Create index on embedding field
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        logger.info(f"Collection '{self.collection_name}' created successfully")
    
    def store_embedding(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        source_file: Optional[str] = None
    ) -> str:
        """
        Store a single embedding in Milvus.
        
        Args:
            text: Original text
            embedding: Embedding vector
            metadata: Optional metadata dictionary
            source_file: Source file path
            
        Returns:
            ID of the stored document
        """
        return self.store_embeddings_batch([{
            "text": text,
            "embedding": embedding,
            "metadata": metadata,
            "source_file": source_file
        }])[0]
    
    def store_embeddings_batch(
        self,
        embeddings_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[str]:
        """
        Store multiple embeddings in Milvus efficiently using batch insertion.
        
        Args:
            embeddings_data: List of dicts with keys: text, embedding, metadata (optional), source_file (optional)
            batch_size: Number of embeddings to insert per batch (default: 100)
            
        Returns:
            List of document IDs
        """
        import json
        
        if not embeddings_data:
            return []
        
        doc_ids = []
        current_batch = []
        
        try:
            for item in embeddings_data:
                # Generate unique ID
                doc_id = str(uuid.uuid4())
                doc_ids.append(doc_id)
                
                # Prepare metadata as JSON string
                metadata_str = ""
                if item.get("metadata"):
                    metadata_str = json.dumps(item["metadata"])
                
                # Prepare data entry
                data_entry = {
                    "id": doc_id,
                    "text": item["text"],
                    "embedding": item["embedding"],
                    "metadata": metadata_str,
                    "source_file": item.get("source_file") or "",
                    "created_at": datetime.now().isoformat()
                }
                
                current_batch.append(data_entry)
                
                # Insert batch when it reaches batch_size
                if len(current_batch) >= batch_size:
                    self.collection.insert(current_batch)
                    current_batch = []
            
            # Insert remaining items
            if current_batch:
                self.collection.insert(current_batch)
            
            # Flush once at the end
            self.collection.flush()
            
            logger.info(f"Stored {len(doc_ids)} embeddings in batch")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Error storing embeddings batch: {e}")
            raise
    
    def search_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters (e.g., {"source_file": "file.txt"})
            
        Returns:
            List of search results with text, metadata, and distance
        """
        try:
            # Build search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            
            # Build expression for filtering if provided
            expr = None
            if filters:
                import json
                conditions = []
                for key, value in filters.items():
                    if key == "source_file":
                        conditions.append(f'source_file == "{value}"')
                    elif key == "metadata":
                        # For metadata, we'd need to parse JSON - simplified here
                        metadata_str = json.dumps(value)
                        conditions.append(f'metadata.like("%{metadata_str}%")')
                
                if conditions:
                    expr = " && ".join(conditions)
            
            # Perform search
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["text", "metadata", "source_file", "created_at"]
            )
            
            # Format results
            formatted_results = []
            for hits in results:
                for hit in hits:
                    result = {
                        "id": hit.id,
                        "text": hit.entity.get("text", ""),
                        "metadata": hit.entity.get("metadata", ""),
                        "source_file": hit.entity.get("source_file", ""),
                        "created_at": hit.entity.get("created_at", ""),
                        "distance": hit.distance
                    }
                    formatted_results.append(result)
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            stats = {
                "collection_name": self.collection_name,
                "num_entities": self.collection.num_entities,
                "is_empty": self.collection.is_empty
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def close(self):
        """Close connection to Milvus."""
        try:
            connections.disconnect("default")
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {e}")
