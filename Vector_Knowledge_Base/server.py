"""
Vector Knowledge Base Tool - Long-term memory access using Milvus vector database.

A production-ready MCP server for:
- Storing embeddings from text files
- Searching embeddings for RAG, user memory, and context recall

Backend: Milvus (via Docker)
Embeddings: Ollama with qwen3-embedding:8b model
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our modules
from embeddings import EmbeddingGenerator
from milvus_client import MilvusClient
from file_ingestion import FileIngestion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(
    name="Vector Knowledge Base Tool",
)

# Constants
SUPPORTED_EXTENSIONS = {
    '.txt': 'text',
    '.json': 'json',
    '.pdf': 'pdf',
    '.doc': 'doc',
    '.docx': 'docx'
}

# Configuration from environment variables
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-embedding:8b")
COLLECTION_NAME = os.getenv("MILVUS_COLLECTION", "vector_knowledge_base")
# Get embedding dimension from env, or None to auto-detect
_embedding_dim_env = os.getenv("EMBEDDING_DIMENSION")
EMBEDDING_DIMENSION = int(_embedding_dim_env) if _embedding_dim_env else None
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", "1000"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "200"))
# Timeout configurations
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 5 minutes default
MILVUS_TIMEOUT = int(os.getenv("MILVUS_TIMEOUT", "60"))  # 1 minute default

# Default text folder path
_default_text_folder = os.getenv("DEFAULT_TEXT_FOLDER")
if _default_text_folder:
    # If provided as env var, resolve it
    if os.path.isabs(_default_text_folder):
        DEFAULT_TEXT_FOLDER = Path(_default_text_folder)
    else:
        # Relative to project root
        DEFAULT_TEXT_FOLDER = Path(__file__).parent.parent / _default_text_folder
else:
    # Fallback to default location
    DEFAULT_TEXT_FOLDER = Path(__file__).parent.parent / "Document_Parser_MCP" / "data" / "extracted" / "text"
    if not DEFAULT_TEXT_FOLDER.exists():
        DEFAULT_TEXT_FOLDER = Path(__file__).parent / "data" / "extracted" / "text"

# Initialize clients (lazy initialization)
_embedding_generator = None
_milvus_client = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create embedding generator instance."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            timeout=OLLAMA_TIMEOUT
        )
    return _embedding_generator


def get_milvus_client() -> MilvusClient:
    """Get or create Milvus client instance."""
    global _milvus_client
    if _milvus_client is None:
        # Detect embedding dimension from model (more reliable than hardcoded value)
        embedding_gen = get_embedding_generator()
        embedding_dim = embedding_gen.get_embedding_dimension()
        
        # Override with env var if explicitly set
        if EMBEDDING_DIMENSION is not None:
            embedding_dim = EMBEDDING_DIMENSION
            logger.info(f"Using embedding dimension from environment: {embedding_dim}")
        else:
            logger.info(f"Auto-detected embedding dimension: {embedding_dim}")
        
        _milvus_client = MilvusClient(
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            collection_name=COLLECTION_NAME,
            embedding_dim=embedding_dim
        )
    return _milvus_client


# ============================================================================
# Validation Functions
# ============================================================================

def validate_text_input(text: str, max_length: int = 100000) -> Tuple[bool, Optional[str]]:
    """
    Validate text input for embedding operations.
    
    Args:
        text: Text to validate
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        return False, "Text cannot be empty"
    if not isinstance(text, str):
        return False, "Text must be a string"
    if len(text) > max_length:
        return False, f"Text exceeds maximum length of {max_length} characters"
    return True, None


def validate_metadata(metadata_str: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate and parse metadata JSON string.
    
    Args:
        metadata_str: JSON string to validate
        
    Returns:
        Tuple of (metadata_dict, error_message)
    """
    if not metadata_str:
        return None, None
    
    try:
        metadata_dict = json.loads(metadata_str)
        if not isinstance(metadata_dict, dict):
            return None, "Metadata must be a JSON object"
        return metadata_dict, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in metadata: {str(e)}"


# ============================================================================
# Utility Functions
# ============================================================================

def json_error(message: str, **kwargs) -> str:
    """
    Create a standardized JSON error response.
    
    Args:
        message: Error message
        **kwargs: Additional error data
        
    Returns:
        JSON string with error
    """
    result = {"error": message, **kwargs}
    return json.dumps(result, indent=2)


def json_success(message: str, **kwargs) -> str:
    """
    Create a standardized JSON success response.
    
    Args:
        message: Success message
        **kwargs: Additional data
        
    Returns:
        JSON string with success data
    """
    result = {"success": True, "message": message, **kwargs}
    return json.dumps(result, indent=2)


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
def store_embedding(
    text: str,
    metadata: Optional[str] = None,
    source_file: Optional[str] = None
) -> str:
    """
    Store an embedding in the vector database. Useful for RAG and user memory storage.
    
    Args:
        text: Text content to embed and store
        metadata: Optional JSON string with metadata (e.g., '{"user_id": "123", "category": "notes"}')
        source_file: Optional source file name/path
        
    Returns:
        JSON string containing the stored document ID and status
    """
    try:
        # Validate text input
        is_valid, error_msg = validate_text_input(text)
        if not is_valid:
            return json_error(error_msg or "Invalid text input")
        
        # Parse and validate metadata if provided
        metadata_dict = None
        if metadata:
            metadata_dict, error_msg = validate_metadata(metadata)
            if error_msg:
                return json_error(error_msg)
        
        # Generate embedding
        embedding_gen = get_embedding_generator()
        embedding = embedding_gen.generate_embedding(text)
        
        if embedding is None:
            return json_error(
                "Failed to generate embedding. Check Ollama connection and timeout settings.",
                suggestion="Try increasing OLLAMA_TIMEOUT in .env file if processing large texts"
            )
        
        # Store in Milvus
        milvus = get_milvus_client()
        doc_id = milvus.store_embedding(
            text=text,
            embedding=embedding,
            metadata=metadata_dict,
            source_file=source_file
        )
        
        return json_success(
            "Embedding stored successfully",
            document_id=doc_id,
            text_length=len(text)
        )
    except Exception as e:
        logger.error(f"Error in store_embedding: {e}", exc_info=True)
        return json_error(f"Failed to store embedding: {str(e)}")


@mcp.tool()
def search_embedding(
    query: str,
    top_k: int = 5,
    filters: Optional[str] = None
) -> str:
    """
    Search for similar embeddings in the vector database. Useful for RAG, context recall, and user memory retrieval.
    
    Args:
        query: Search query text
        top_k: Number of results to return (default: 5)
        filters: Optional JSON string with filters (e.g., '{"source_file": "document.txt"}')
        
    Returns:
        JSON string containing search results with text, metadata, and similarity scores
    """
    try:
        # Validate query input
        is_valid, error_msg = validate_text_input(query, max_length=50000)
        if not is_valid:
            return json_error(error_msg or "Invalid query input")
        
        # Validate top_k
        if top_k <= 0 or top_k > 100:
            return json_error("top_k must be between 1 and 100")
        
        # Parse and validate filters if provided
        filters_dict = None
        if filters:
            filters_dict, error_msg = validate_metadata(filters)
            if error_msg:
                return json_error(f"Invalid filters: {error_msg}")
        
        # Generate query embedding
        embedding_gen = get_embedding_generator()
        query_embedding = embedding_gen.generate_embedding(query)
        
        if query_embedding is None:
            return json_error("Failed to generate query embedding. Check Ollama connection.")
        
        # Search in Milvus
        milvus = get_milvus_client()
        results = milvus.search_embedding(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters_dict
        )
        
        # Format results
        formatted_results = []
        for result in results:
            # Parse metadata JSON string if present
            metadata = result.get("metadata", "")
            if metadata:
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    pass  # Keep as string if not valid JSON
            
            formatted_results.append({
                "id": result.get("id"),
                "text": result.get("text", ""),
                "metadata": metadata,
                "source_file": result.get("source_file", ""),
                "created_at": result.get("created_at", ""),
                "distance": result.get("distance", 0.0),
                "similarity": 1.0 / (1.0 + result.get("distance", 1.0))  # Convert distance to similarity
            })
        
        return json_success(
            f"Found {len(formatted_results)} results",
            query=query,
            results=formatted_results
        )
    except Exception as e:
        logger.error(f"Error in search_embedding: {e}", exc_info=True)
        return json_error(f"Failed to search embeddings: {str(e)}")


@mcp.tool()
def ingest_text_folder(
    text_folder: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> str:
    """
    Ingest all .txt files from a folder into the vector database. Useful for bulk knowledge ingestion.
    
    Args:
        text_folder: Path to folder containing .txt files (defaults to DEFAULT_TEXT_FOLDER from .env)
        chunk_size: Maximum size of each text chunk (defaults to DEFAULT_CHUNK_SIZE from .env)
        chunk_overlap: Overlap between chunks (defaults to DEFAULT_CHUNK_OVERLAP from .env)
        
    Returns:
        JSON string containing ingestion statistics
    """
    try:
        # Use defaults from environment if not provided
        if chunk_size is None:
            chunk_size = DEFAULT_CHUNK_SIZE
        if chunk_overlap is None:
            chunk_overlap = DEFAULT_CHUNK_OVERLAP
        
        # Determine folder path
        if text_folder:
            folder_path = Path(text_folder)
        else:
            folder_path = DEFAULT_TEXT_FOLDER
        
        if not folder_path.exists():
            return json_error(f"Text folder does not exist: {folder_path}")
        
        # Initialize ingestion and clients
        ingestion = FileIngestion(str(folder_path))
        embedding_gen = get_embedding_generator()
        milvus = get_milvus_client()
        
        # Process files with batch optimization
        total_chunks = 0
        total_files = 0
        stored_count = 0
        failed_count = 0
        batch_size = 50  # Process embeddings in batches for better performance
        batch_data = []
        
        logger.info(f"Starting ingestion from {folder_path} (chunk_size={chunk_size}, chunk_overlap={chunk_overlap})")
        
        for chunk_data in ingestion.ingest_all_files(chunk_size, chunk_overlap):
            total_chunks += 1
            
            # Track files and log progress
            if chunk_data.get("chunk_index", 0) == 0:
                total_files += 1
                logger.info(f"Processing file {total_files}: {chunk_data.get('source_file')}")
            
            try:
                # Generate embedding
                embedding = embedding_gen.generate_embedding(chunk_data["text"])
                
                if embedding is None:
                    failed_count += 1
                    continue
                
                # Prepare batch data
                metadata = {
                    "chunk_index": chunk_data.get("chunk_index"),
                    "total_chunks": chunk_data.get("total_chunks")
                }
                
                batch_data.append({
                    "text": chunk_data["text"],
                    "embedding": embedding,
                    "metadata": metadata,
                    "source_file": chunk_data.get("source_file")
                })
                
                # Store batch when it reaches batch_size
                if len(batch_data) >= batch_size:
                    try:
                        milvus.store_embeddings_batch(batch_data, batch_size=batch_size)
                        stored_count += len(batch_data)
                        batch_data = []
                    except Exception as e:
                        logger.error(f"Error storing batch: {e}")
                        failed_count += len(batch_data)
                        batch_data = []
                
                # Log progress every 10 chunks
                if total_chunks % 10 == 0:
                    logger.info(f"Processed {total_chunks} chunks, stored {stored_count}, failed {failed_count}")
                
            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                failed_count += 1
                continue
        
        # Store remaining batch
        if batch_data:
            try:
                milvus.store_embeddings_batch(batch_data, batch_size=len(batch_data))
                stored_count += len(batch_data)
            except Exception as e:
                logger.error(f"Error storing final batch: {e}")
                failed_count += len(batch_data)
        
        return json_success(
            "Ingestion completed",
            total_files=total_files,
            total_chunks=total_chunks,
            stored_count=stored_count,
            failed_count=failed_count,
            folder_path=str(folder_path)
        )
    except Exception as e:
        logger.error(f"Error in ingest_text_folder: {e}", exc_info=True)
        return json_error(f"Failed to ingest text folder: {str(e)}")


@mcp.tool()
def get_collection_stats() -> str:
    """
    Get statistics about the vector database collection. Useful for monitoring and debugging.
    
    Returns:
        JSON string containing collection statistics
    """
    try:
        milvus = get_milvus_client()
        stats = milvus.get_collection_stats()
        
        return json_success(
            "Collection statistics retrieved",
            **stats
        )
    except Exception as e:
        logger.error(f"Error in get_collection_stats: {e}", exc_info=True)
        return json_error(f"Failed to get collection stats: {str(e)}")


# Run the server
if __name__ == "__main__":
    mcp.run()
