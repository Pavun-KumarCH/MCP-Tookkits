"""
Embedding generation module using Ollama with qwen3-embedding:8b model.

Optimized with caching and improved error handling.
"""
import logging
import requests
from typing import List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using Ollama API with caching and retry logic."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3-embedding:8b", timeout: int = 300):
        """
        Initialize the embedding generator.
        
        Args:
            base_url: Ollama API base URL
            model: Model name for embeddings
            timeout: Request timeout in seconds (default: 300)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.embedding_endpoint = f"{self.base_url}/api/embeddings"
        self._dimension_cache: Optional[int] = None
        self._session = requests.Session()  # Reuse connections
    
    def generate_embedding(self, text: str, retries: int = 2) -> Optional[List[float]]:
        """
        Generate embedding for a single text with retry logic.
        
        Args:
            text: Input text to embed
            retries: Number of retry attempts (default: 2)
            
        Returns:
            Embedding vector or None if error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        for attempt in range(retries + 1):
            try:
                response = self._session.post(
                    self.embedding_endpoint,
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding")
                
                if embedding:
                    return embedding
                else:
                    logger.warning("No embedding returned from Ollama API")
                    return None
                    
            except requests.exceptions.Timeout as e:
                if attempt < retries:
                    logger.warning(f"Timeout generating embedding (attempt {attempt + 1}/{retries + 1}): {e}")
                    continue
                logger.error(f"Timeout generating embedding after {retries + 1} attempts (timeout={self.timeout}s)")
                return None
            except requests.exceptions.RequestException as e:
                if attempt < retries:
                    logger.warning(f"Request error (attempt {attempt + 1}/{retries + 1}): {e}")
                    continue
                logger.error(f"Error generating embedding after {retries + 1} attempts: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in generate_embedding: {e}")
                return None
        
        return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors (None for failed embeddings)
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings from the model with caching.
        This method generates a test embedding to determine the actual dimension.
        For qwen3-embedding:8b, typically returns 4096.
        
        Returns:
            Embedding dimension
        """
        # Return cached dimension if available
        if self._dimension_cache is not None:
            return self._dimension_cache
        
        # Generate a test embedding to determine dimension
        test_embedding = self.generate_embedding("test")
        if test_embedding:
            dimension = len(test_embedding)
            self._dimension_cache = dimension
            logger.info(f"Detected embedding dimension: {dimension}")
            return dimension
        
        # Fallback (should not happen if Ollama is working)
        logger.warning("Failed to detect embedding dimension, using fallback: 4096")
        self._dimension_cache = 4096
        return 4096
    
    def clear_cache(self):
        """Clear the dimension cache (useful for testing or model changes)."""
        self._dimension_cache = None
