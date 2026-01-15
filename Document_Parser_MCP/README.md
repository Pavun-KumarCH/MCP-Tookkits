# Document Parser MCP Tool

**Production-ready PDF parser** extracting text, tables, images, and links with NLP preprocessing. Built for contracts, resumes, reports, and knowledge ingestion.

---

## 🚀 Quick Start

```bash
# Install dependencies
uv sync  # or: pip install pdfplumber pymupdf python-docx

# Run server
python server.py
```

---

## 📋 What I Built

### Core Functions

1. **`parse_pdf()`** - Comprehensive PDF parser
   - Extracts: text, tables, images, links
   - Saves with NLP preprocessing (lowercase, no special chars, chunked)
   - Returns structured JSON

2. **`extract_tables()`** - Table-only extraction
   - Fast table extraction
   - Exports to JSON/CSV

3. **`parse_docx()`** - DOCX parser
   - Basic Word document parsing

### Key Features

✅ **NLP Preprocessing** - Automatic text cleaning (lowercase, special char removal, chunking)  
✅ **Smart File Naming** - Uses PDF filename as prefix (`contract_text_preprocessed.txt`)  
✅ **Multiple Formats** - Tables saved as JSON + CSV  
✅ **Image Extraction** - With metadata and optional saving  
✅ **Production Ready** - Robust error handling, modular design

---

## 💻 Usage Examples

### Basic PDF Parsing

```python
import json

# Parse everything
result = parse_pdf("contract.pdf")
data = json.loads(result)

print(f"Pages: {data['metadata']['total_pages']}")
print(f"Tables: {data['tables_count']}")
print(f"Images: {data['images_count']}")
```

### Save with NLP Preprocessing

```python
# Save text (preprocessed), tables, and images
result = parse_pdf(
    "contract.pdf",
    save_text=True,      # Saves preprocessed text
    save_tables=True,    # Saves JSON + CSV
    save_images=True     # Saves images
)

data = json.loads(result)

# Access saved files
for file_info in data.get('text_saved_files', []):
    print(f"Saved: {file_info['filename']}")
    # Files: contract_text_preprocessed.txt, contract_text_chunks.txt
```

### Extract Tables Only

```python
# Fast table extraction
result = extract_tables("report.pdf", save_tables=True)
data = json.loads(result)

for table in data['tables']:
    print(f"Page {table['page']}: {table['rows']} rows")
    # Files: report_table_p1_t1.json, report_table_p1_t1.csv
```

---

## 📁 File Structure

```
extracted/
├── text/
│   ├── contract_text_preprocessed.txt      # Full preprocessed text
│   ├── contract_text_chunks.txt           # Chunked text (1000 chars)
│   └── contract_text_pages_preprocessed.txt # Page-by-page
├── tables/
│   ├── contract_table_p1_t1.json          # Table 1, page 1 (JSON)
│   └── contract_table_p1_t1.csv           # Table 1, page 1 (CSV)
└── images/
    └── contract_image_p1_i1.png           # Image 1, page 1
```

**Naming Convention:** `{filename}_{type}_p{page}_{identifier}.{ext}`

---

## 🔧 Function Reference

### `parse_pdf(file_path, ...)`

**Parameters:**
- `file_path` (str) - PDF path (relative or absolute)
- `extract_tables` (bool) - Extract tables? Default: `True`
- `extract_images` (bool) - Extract images? Default: `True`
- `extract_links` (bool) - Extract links? Default: `True`
- `save_text` (bool) - Save preprocessed text? Default: `False`
- `save_tables` (bool) - Save tables? Default: `False`
- `save_images` (bool) - Save images? Default: `False`
- `output_dir` (str) - Custom output directory (optional)

**Returns:** JSON string with extracted data

**Example:**
```python
parse_pdf("doc.pdf", save_text=True, save_tables=True)
```

---

### `extract_tables(file_path, save_tables, output_dir)`

**Parameters:**
- `file_path` (str) - PDF path
- `save_tables` (bool) - Save to files? Default: `False`
- `output_dir` (str) - Output directory (optional)

**Returns:** JSON string with tables

**Example:**
```python
extract_tables("report.pdf", save_tables=True)
```

---

### `parse_docx(file_path)`

**Parameters:**
- `file_path` (str) - DOCX path

**Returns:** JSON string with text and tables

**Example:**
```python
parse_docx("resume.docx")
```

---

## 🧠 NLP Preprocessing

When `save_text=True`, text is automatically preprocessed:

1. **Lowercasing** - All text to lowercase
2. **Special Character Removal** - Removes @#$%^&*() etc.
3. **Whitespace Normalization** - Normalizes tabs, newlines, spaces
4. **Chunking** - Splits into 1000-char chunks (100-char overlap)

**Use Cases:**
- Embedding generation
- Search indexing
- NLP pipelines
- Knowledge base ingestion

---

## 🏗️ Architecture

### Code Structure

```
server.py
├── Constants & Config
│   ├── DEFAULT_DATA_DIR
│   ├── DEFAULT_CHUNK_SIZE
│   └── MAX_BASE64_IMAGE_SIZE
├── Utility Functions
│   ├── preprocess_text() - NLP preprocessing
│   ├── preprocess_text_chunks() - Text chunking
│   ├── json_error/json_success() - Response helpers
│   └── resolve_file_path() - Path resolution
├── PDF Extraction Functions
│   ├── extract_text_with_pdfplumber()
│   ├── extract_tables_with_pdfplumber()
│   ├── extract_images_with_pymupdf()
│   └── extract_links_with_pymupdf()
└── MCP Tool Functions
    ├── parse_pdf() - Main parser
    ├── extract_tables() - Table extractor
    └── parse_docx() - DOCX parser
```

### Design Decisions

1. **Dual Library Approach** - pdfplumber (text/tables) + PyMuPDF (images/links)
2. **Modular Functions** - Each extraction type is separate
3. **Error Resilience** - Continues even if one extraction fails
4. **Consistent Naming** - All files use PDF filename prefix

---

## 📦 Dependencies

- `pdfplumber>=0.11.0` - Text and table extraction
- `pymupdf>=1.24.0` - Image and link extraction
- `python-docx>=1.2.0` - DOCX parsing

---

## 🎯 Production Use Cases

| Use Case | Functions | Why |
|----------|-----------|-----|
| **Contracts** | `parse_pdf()` | Extract terms, tables, signatures |
| **Resumes** | `parse_pdf()` | Extract skills, experience, links |
| **Reports** | `extract_tables()` | Fast table extraction |
| **Knowledge Base** | `parse_pdf(save_text=True)` | Preprocessed text for embeddings |

---

## 💡 Interview Talking Points

**What I Built:**
- Production-ready PDF parser with NLP preprocessing
- Modular design with separate extraction functions
- Smart file naming using PDF filename prefix
- Handles text, tables, images, links, and DOCX

**Key Technical Decisions:**
- Used pdfplumber for accurate table extraction
- Used PyMuPDF for fast image/link extraction
- Implemented NLP preprocessing pipeline
- Consistent file naming convention

**Challenges Solved:**
- Path resolution (relative/absolute)
- Error handling (continues on partial failures)
- Memory efficiency (chunking large texts)
- File organization (structured output directories)

---

## 📝 Response Format

All functions return JSON:

```json
{
  "file_path": "/path/to/file.pdf",
  "filename": "file.pdf",
  "base_filename": "file",
  "metadata": {"total_pages": 10},
  "text": "Extracted text...",
  "tables_count": 3,
  "tables": [...],
  "images_count": 2,
  "images": [...],
  "links_count": 5,
  "links": [...],
  "text_saved_files": [...],  // If save_text=True
  "tables_saved_files": [...], // If save_tables=True
  "output_directory": "..."     // If any save=True
}
```

---

**Built for production document processing** 🚀
