# Vector Knowledge Base Tool

A production-ready MCP server for long-term memory access using Milvus vector database and Ollama embeddings. Optimized for performance with batch operations, connection pooling, and intelligent caching.

## 🚀 Features

- **Store Embeddings**: Store text with embeddings and metadata (single or batch)
- **Search Embeddings**: Semantic search for RAG, user memory, and context recall
- **Bulk Ingestion**: Ingest all .txt files from a folder automatically with optimized batch processing
- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **Performance Optimized**: Batch operations, connection reuse, and intelligent caching
- **Auto-Dimension Detection**: Automatically detects embedding dimensions from the model
- **Smart Chunking**: Intelligent text chunking with sentence boundary detection

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Performance Optimization](#performance-optimization)
- [API Reference](#api-reference)
- [Use Cases](#use-cases)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture

### Modules

1. **`embeddings.py`**: Ollama API integration
   - Connection pooling with session reuse
   - Retry logic with exponential backoff
   - Dimension caching to avoid repeated API calls
   - Timeout handling

2. **`milvus_client.py`**: Milvus vector database operations
   - Batch insertion for improved performance
   - Collection dimension validation
   - Connection management
   - Search with filtering support

3. **`file_ingestion.py`**: Text file processing
   - Smart chunking with sentence boundary detection
   - Generator-based processing for memory efficiency
   - Support for large files

4. **`server.py`**: MCP server with tool endpoints
   - Input validation
   - Error handling
   - Progress logging

## 📦 Prerequisites

### 1. Milvus (via Docker)

Start Milvus using Docker:

```bash
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest \
  standalone
```

Verify Milvus is running:
```bash
docker ps | grep milvus
```

### 2. Ollama with qwen3-embedding:8b

Install and pull the embedding model:

```bash
# Install Ollama (if not already installed)
# Visit https://ollama.ai for installation instructions

# Pull the embedding model
ollama pull qwen3-embedding:8b
```

Ensure Ollama is running:
```bash
ollama serve
```

Verify the model:
```bash
ollama list
ollama show qwen3-embedding:8b
```

## 🔧 Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

## ⚙️ Configuration

All configuration is managed through the `.env` file. Copy `.env.example` to `.env` and customize as needed.

### Configuration Options

#### Milvus Configuration
- `MILVUS_HOST`: Milvus host address (default: `localhost`)
- `MILVUS_PORT`: Milvus port (default: `19530`)
- `MILVUS_COLLECTION`: Collection name (default: `vector_knowledge_base`)

#### Ollama Configuration
- `OLLAMA_BASE_URL`: Ollama API URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: Embedding model name (default: `qwen3-embedding:8b`)
- `OLLAMA_TIMEOUT`: Request timeout in seconds (default: `300` = 5 minutes)

#### Embedding Configuration
- `EMBEDDING_DIMENSION`: Embedding dimension (default: auto-detect, typically `4096` for qwen3-embedding:8b)
  - Leave unset to auto-detect from model (recommended)
  - Set explicitly if you have an existing collection with a specific dimension

#### File Ingestion Configuration
- `DEFAULT_TEXT_FOLDER`: Path to folder with .txt files (default: `../Document_Parser_MCP/data/extracted/text`)
  - Can be absolute or relative path
- `DEFAULT_CHUNK_SIZE`: Default chunk size in characters (default: `1000`)
- `DEFAULT_CHUNK_OVERLAP`: Default chunk overlap in characters (default: `200`)

#### Timeout Configuration
- `OLLAMA_TIMEOUT`: Ollama API timeout in seconds (default: `300`)
- `MILVUS_TIMEOUT`: Milvus operation timeout in seconds (default: `60`)

### Example `.env` File

```bash
# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=vector_knowledge_base

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-embedding:8b
OLLAMA_TIMEOUT=300

# Embedding Configuration (leave empty to auto-detect)
EMBEDDING_DIMENSION=

# File Ingestion
DEFAULT_TEXT_FOLDER=../Document_Parser_MCP/data/extracted/text
DEFAULT_CHUNK_SIZE=1000
DEFAULT_CHUNK_OVERLAP=200

# Timeouts
MILVUS_TIMEOUT=60
```

## 📖 Usage

### MCP Tools

#### 1. `store_embedding`

Store a single text with embedding:

```python
store_embedding(
    text="Your text content here",
    metadata='{"user_id": "123", "category": "notes"}',  # Optional JSON string
    source_file="document.txt"  # Optional
)
```

**Response:**
```json
{
  "success": true,
  "message": "Embedding stored successfully",
  "document_id": "uuid-here",
  "text_length": 42
}
```

#### 2. `search_embedding`

Search for similar texts:

```python
search_embedding(
    query="What is machine learning?",
    top_k=5,  # Number of results (1-100)
    filters='{"source_file": "document.txt"}'  # Optional JSON string
)
```

**Response:**
```json
{
  "success": true,
  "message": "Found 5 results",
  "query": "What is machine learning?",
  "results": [
    {
      "id": "uuid-here",
      "text": "Machine learning is...",
      "metadata": {...},
      "source_file": "document.txt",
      "created_at": "2024-01-15T10:30:00",
      "distance": 0.123,
      "similarity": 0.890
    }
  ]
}
```

#### 3. `ingest_text_folder`

Bulk ingest all .txt files from a folder with optimized batch processing:

```python
ingest_text_folder(
    text_folder="/path/to/text/folder",  # Optional, defaults to DEFAULT_TEXT_FOLDER
    chunk_size=1000,  # Optional, defaults to DEFAULT_CHUNK_SIZE
    chunk_overlap=200  # Optional, defaults to DEFAULT_CHUNK_OVERLAP
)
```

**Response:**
```json
{
  "success": true,
  "message": "Ingestion completed",
  "total_files": 5,
  "total_chunks": 42,
  "stored_count": 40,
  "failed_count": 2,
  "folder_path": "/path/to/folder"
}
```

**Note:** This function processes files in batches of 50 for optimal performance.

#### 4. `get_collection_stats`

Get statistics about the vector database:

```python
get_collection_stats()
```

**Response:**
```json
{
  "success": true,
  "message": "Collection statistics retrieved",
  "collection_name": "vector_knowledge_base",
  "num_entities": 1000,
  "is_empty": false
}
```

## ⚡ Performance Optimization

### Batch Operations

The tool automatically uses batch operations for improved performance:

- **Embedding Storage**: Batches of 50 embeddings are inserted together
- **Connection Reuse**: HTTP sessions are reused for Ollama API calls
- **Dimension Caching**: Embedding dimensions are cached after first detection

### Recommended Settings

For **large-scale ingestion**:
```bash
# Increase timeout for large texts
OLLAMA_TIMEOUT=600  # 10 minutes

# Adjust chunk size based on your content
DEFAULT_CHUNK_SIZE=2000  # Larger chunks = fewer API calls
DEFAULT_CHUNK_OVERLAP=400
```

For **real-time queries**:
```bash
# Keep default timeouts
OLLAMA_TIMEOUT=300
MILVUS_TIMEOUT=60
```

### Performance Tips

1. **Batch Processing**: Use `ingest_text_folder` for bulk operations instead of multiple `store_embedding` calls
2. **Chunk Size**: Larger chunks reduce API calls but may lose granularity
3. **Connection Pooling**: The tool automatically reuses HTTP connections
4. **Dimension Caching**: First call detects dimension, subsequent calls use cache

## 📚 API Reference

### EmbeddingGenerator (`embeddings.py`)

#### `generate_embedding(text: str, retries: int = 2) -> Optional[List[float]]`
Generate embedding for a single text with retry logic.

**Parameters:**
- `text`: Input text to embed
- `retries`: Number of retry attempts (default: 2)

**Returns:** Embedding vector or None if error

#### `get_embedding_dimension() -> int`
Get embedding dimension with caching.

**Returns:** Embedding dimension (typically 4096 for qwen3-embedding:8b)

### MilvusClient (`milvus_client.py`)

#### `store_embedding(text, embedding, metadata=None, source_file=None) -> str`
Store a single embedding.

#### `store_embeddings_batch(embeddings_data, batch_size=100) -> List[str]`
Store multiple embeddings efficiently.

**Parameters:**
- `embeddings_data`: List of dicts with keys: `text`, `embedding`, `metadata` (optional), `source_file` (optional)
- `batch_size`: Number of embeddings per batch (default: 100)

#### `search_embedding(query_embedding, top_k=5, filters=None) -> List[Dict]`
Search for similar embeddings.

**Parameters:**
- `query_embedding`: Query embedding vector
- `top_k`: Number of results (default: 5)
- `filters`: Optional filter dict (e.g., `{"source_file": "doc.txt"}`)

### FileIngestion (`file_ingestion.py`)

#### `split_into_chunks(text, chunk_size=1000, chunk_overlap=200) -> List[str]`
Split text into chunks with intelligent boundary detection.

**Features:**
- Sentence boundary detection
- Paragraph break detection
- Overlap handling
- Empty chunk filtering

## 🎯 Use Cases

### 1. RAG (Retrieval-Augmented Generation)
Store documents and retrieve relevant context for LLM prompts:

```python
# Store documents
store_embedding(
    text=document_content,
    metadata='{"type": "document", "category": "technical"}',
    source_file="technical_doc.txt"
)

# Retrieve context
results = search_embedding(
    query="How does the system work?",
    top_k=3
)
```

### 2. User Memory
Store user preferences and history:

```python
store_embedding(
    text="User prefers dark mode and Python programming",
    metadata='{"user_id": "123", "type": "preference"}'
)

# Recall user preferences
preferences = search_embedding(
    query="What are user 123's preferences?",
    filters='{"user_id": "123"}'
)
```

### 3. Context Recall
Retrieve relevant information from past conversations:

```python
# Store conversation context
store_embedding(
    text=conversation_summary,
    metadata='{"conversation_id": "abc123", "timestamp": "2024-01-15"}'
)

# Recall context
context = search_embedding(
    query="What did we discuss about the project?",
    filters='{"conversation_id": "abc123"}'
)
```

## 🔍 Troubleshooting

### Common Issues

#### Milvus Connection Issues

**Problem:** Cannot connect to Milvus

**Solutions:**
```bash
# Check if Milvus is running
docker ps | grep milvus

# Check Milvus logs
docker logs milvus-standalone

# Verify host and port in .env
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

#### Ollama Connection Issues

**Problem:** Cannot connect to Ollama or generate embeddings

**Solutions:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Verify model is available
ollama list
ollama show qwen3-embedding:8b

# Check Ollama logs
# (Ollama logs are typically in the terminal where it's running)
```

#### Dimension Mismatch Error

**Problem:** `Dimension mismatch: Collection has dimension X, but expected Y`

**Solutions:**
1. **Option 1:** Drop and recreate the collection (if empty or can re-ingest)
2. **Option 2:** Set `EMBEDDING_DIMENSION` in `.env` to match existing collection

```bash
# In .env file
EMBEDDING_DIMENSION=3072  # or whatever dimension your collection uses
```

#### Timeout Errors

**Problem:** `Request timed out` or `MCP error -32001`

**Solutions:**
```bash
# Increase timeout in .env
OLLAMA_TIMEOUT=600  # 10 minutes for large texts
MILVUS_TIMEOUT=120  # 2 minutes for slow operations
```

#### Empty Embeddings

**Problem:** Embedding generation returns None

**Solutions:**
- Check Ollama is running and accessible
- Verify model is pulled: `ollama list`
- Check text is not empty
- Review Ollama logs for errors
- Increase timeout if processing very large texts

### Debug Mode

Enable debug logging by setting log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Performance Benchmarks

Typical performance on a modern machine:

- **Single Embedding**: ~100-500ms (depending on text length)
- **Batch of 50 Embeddings**: ~5-15 seconds
- **Search (top_k=5)**: ~50-200ms
- **Ingestion Rate**: ~100-500 chunks/minute (depending on text complexity)

## 🔒 Best Practices

1. **Use Batch Operations**: Always use `ingest_text_folder` for bulk operations
2. **Monitor Timeouts**: Adjust timeouts based on your text sizes
3. **Validate Input**: The tool validates inputs, but ensure text quality
4. **Regular Backups**: Milvus data is persistent, but consider backups
5. **Dimension Consistency**: Keep embedding dimensions consistent across collections
6. **Chunk Size**: Balance between granularity and performance (1000-2000 chars recommended)

## 📝 License

Production Tools Suite

## 🤝 Contributing

This is part of the Production Tools Suite. For issues or contributions, please refer to the main project repository.

## 📞 Support

For issues related to:
- **Milvus**: Check [Milvus documentation](https://milvus.io/docs)
- **Ollama**: Check [Ollama documentation](https://github.com/ollama/ollama)
- **MCP**: Check [MCP documentation](https://modelcontextprotocol.io)

---

**Version:** 1.0.0  
**Last Updated:** January 2025
