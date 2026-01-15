"""
Document Parser Tool - Extract structured data from PDFs.

A production-ready MCP server for parsing PDF documents and extracting:
- Text (with NLP preprocessing)
- Tables (JSON/CSV export)
- Images (with metadata)
- Links (hyperlinks and references)
- DOCX support (basic)

Author: Production Tools Suite
Purpose: Contracts, resumes, reports, knowledge ingestion
"""
import json
import os
import base64
import re
import csv
from pathlib import Path
from typing import Optional, Dict, List, Any
from mcp.server.fastmcp import FastMCP

# ============================================================================
# Constants & Configuration
# ============================================================================

# Initialize MCP server
mcp = FastMCP(name="Document Parser Tool")

# Default data directory
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "Document_Parser_MCP" / "data"
if not DEFAULT_DATA_DIR.exists():
    DEFAULT_DATA_DIR = Path(__file__).parent / "data"
if not DEFAULT_DATA_DIR.exists():
    DEFAULT_DATA_DIR = Path.cwd()

# NLP Preprocessing defaults
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100
MAX_BASE64_IMAGE_SIZE = 1024 * 1024  # 1MB


# ============================================================================
# Utility Functions
# ============================================================================

def preprocess_text(text: str, lowercase: bool = True, remove_special_chars: bool = True, 
                    normalize_whitespace: bool = True, remove_extra_spaces: bool = True,
                    keep_numbers: bool = True, keep_basic_punctuation: bool = False) -> str:
    """
    Apply NLP preprocessing to text.
    
    Args:
        text: Input text to preprocess
        lowercase: Convert to lowercase (default: True)
        remove_special_chars: Remove special characters (default: True)
        normalize_whitespace: Normalize whitespace characters (default: True)
        remove_extra_spaces: Remove extra whitespace (default: True)
        keep_numbers: Keep numeric characters (default: True)
        keep_basic_punctuation: Keep basic punctuation like . , ! ? (default: False)
        
    Returns:
        Preprocessed text string
    """
    if not text:
        return ""
    
    processed = text
    
    # Step 1: Lowercase
    if lowercase:
        processed = processed.lower()
    
    # Step 2: Normalize whitespace (replace tabs, newlines, etc. with spaces)
    if normalize_whitespace:
        processed = re.sub(r'\s+', ' ', processed)  # Replace all whitespace with single space
        processed = re.sub(r'\n+', ' ', processed)  # Replace newlines
        processed = re.sub(r'\t+', ' ', processed)  # Replace tabs
        processed = re.sub(r'\r+', ' ', processed)  # Replace carriage returns
    
    # Step 3: Remove special characters
    if remove_special_chars:
        if keep_basic_punctuation:
            # Keep alphanumeric, spaces, and basic punctuation
            pattern = r'[^a-z0-9\s.,!?;:()\-\'"]' if lowercase else r'[^a-zA-Z0-9\s.,!?;:()\-\'"]'
        else:
            # Keep only alphanumeric and spaces
            pattern = r'[^a-z0-9\s]' if lowercase else r'[^a-zA-Z0-9\s]'
        
        if not keep_numbers:
            pattern = pattern.replace('0-9', '')
        
        processed = re.sub(pattern, ' ', processed)
    
    # Step 4: Remove extra spaces
    if remove_extra_spaces:
        processed = re.sub(r'\s+', ' ', processed)  # Multiple spaces to single space
        processed = processed.strip()  # Remove leading/trailing spaces
    
    return processed


def preprocess_text_chunks(text: str, chunk_size: int = 1000, overlap: int = 100,
                          lowercase: bool = True, remove_special_chars: bool = True,
                          normalize_whitespace: bool = True, remove_extra_spaces: bool = True) -> List[str]:
    """
    Preprocess text and split into chunks.
    
    Args:
        text: Input text to preprocess and chunk
        chunk_size: Size of each chunk in characters (default: 1000)
        overlap: Overlap between chunks in characters (default: 100)
        lowercase: Convert to lowercase (default: True)
        remove_special_chars: Remove special characters (default: True)
        normalize_whitespace: Normalize whitespace (default: True)
        remove_extra_spaces: Remove extra spaces (default: True)
        
    Returns:
        List of preprocessed text chunks
    """
    # First preprocess the entire text
    processed_text = preprocess_text(
        text,
        lowercase=lowercase,
        remove_special_chars=remove_special_chars,
        normalize_whitespace=normalize_whitespace,
        remove_extra_spaces=remove_extra_spaces
    )
    
    # Split into chunks
    chunks = []
    start = 0
    text_length = len(processed_text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = processed_text[start:end]
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk.strip())
        start = end - overlap  # Overlap for context
    
    return chunks


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
        **kwargs: Additional data to include
        
    Returns:
        JSON string with success and data
    """
    result = {"success": True, "message": message, **kwargs}
    return json.dumps(result, indent=2)


def resolve_file_path(file_path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Resolve file path to absolute Path object.
    
    Args:
        file_path: Path string (relative or absolute)
        base_dir: Base directory for relative paths
        
    Returns:
        Resolved absolute Path object
    """
    # Handle absolute paths
    if os.path.isabs(file_path):
        return Path(file_path)
    
    # Handle relative paths starting with .. or ./
    if file_path.startswith('..') or file_path.startswith('./'):
        return Path(file_path).resolve()
    
    # Handle paths starting with "data/" - resolve relative to current directory
    if file_path.startswith('data/'):
        return Path(file_path).resolve()
    
    # Handle simple relative paths (relative to base_dir)
    if base_dir is None:
        base_dir = DEFAULT_DATA_DIR
    
    # Resolve relative to base_dir
    resolved = (base_dir / file_path).resolve()
    return resolved


# ============================================================================
# PDF Parsing Functions
# ============================================================================

def extract_text_with_pdfplumber(file_path: Path, save_text: bool = False, output_dir: Optional[Path] = None, base_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract text content from PDF using pdfplumber.
    
    Args:
        file_path: Path to PDF file
        save_text: Whether to save text to file
        output_dir: Directory to save text file
        base_filename: Base filename for saved files
        
    Returns:
        Dictionary with text content and metadata
    """
    try:
        import pdfplumber
        
        text_content = []
        metadata = {}
        saved_files = []
        
        with pdfplumber.open(file_path) as pdf:
            metadata = {
                "total_pages": len(pdf.pages),
                "metadata": pdf.metadata or {},
            }
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append({
                        "page": page_num,
                        "text": page_text,
                        "chars": len(page_text),
                    })
        
        full_text = "\n\n".join([p["text"] for p in text_content])
        
        # Save text to file if requested
        if save_text and output_dir and base_filename:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Preprocess text for saving
            preprocessed_text = preprocess_text(
                full_text,
                lowercase=True,
                remove_special_chars=True,
                normalize_whitespace=True,
                remove_extra_spaces=True,
                keep_numbers=True,
                keep_basic_punctuation=False
            )
            
            # Save preprocessed full text
            text_filename = f"{base_filename}_text_preprocessed.txt"
            text_path = output_dir / text_filename
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(preprocessed_text)
            saved_files.append({
                "type": "full_text_preprocessed",
                "filename": text_filename,
                "path": str(text_path),
                "size": len(preprocessed_text.encode('utf-8'))
            })
            
            # Save preprocessed text chunks
            chunks = preprocess_text_chunks(
                full_text,
                chunk_size=DEFAULT_CHUNK_SIZE,
                overlap=DEFAULT_CHUNK_OVERLAP,
                lowercase=True,
                remove_special_chars=True,
                normalize_whitespace=True,
                remove_extra_spaces=True
            )
            
            chunks_filename = f"{base_filename}_text_chunks.txt"
            chunks_path = output_dir / chunks_filename
            with open(chunks_path, 'w', encoding='utf-8') as f:
                for i, chunk in enumerate(chunks, 1):
                    f.write(f"\n{'='*80}\n")
                    f.write(f"CHUNK {i} (Length: {len(chunk)} chars)\n")
                    f.write(f"{'='*80}\n\n")
                    f.write(chunk)
                    f.write("\n\n")
            saved_files.append({
                "type": "text_chunks",
                "filename": chunks_filename,
                "path": str(chunks_path),
                "chunks_count": len(chunks)
            })
            
            # Save preprocessed page-by-page text
            pages_filename = f"{base_filename}_text_pages_preprocessed.txt"
            pages_path = output_dir / pages_filename
            with open(pages_path, 'w', encoding='utf-8') as f:
                for page_data in text_content:
                    preprocessed_page = preprocess_text(
                        page_data['text'],
                        lowercase=True,
                        remove_special_chars=True,
                        normalize_whitespace=True,
                        remove_extra_spaces=True,
                        keep_numbers=True,
                        keep_basic_punctuation=False
                    )
                    f.write(f"\n{'='*80}\n")
                    f.write(f"PAGE {page_data['page']} (Preprocessed)\n")
                    f.write(f"{'='*80}\n\n")
                    f.write(preprocessed_page)
                    f.write("\n\n")
            saved_files.append({
                "type": "pages_text_preprocessed",
                "filename": pages_filename,
                "path": str(pages_path),
            })
        
        result = {
            "text": full_text,
            "pages": text_content,
            "metadata": metadata,
        }
        
        if saved_files:
            result["saved_files"] = saved_files
        
        return result
    except ImportError:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
    except Exception as e:
        raise Exception(f"Error extracting text: {str(e)}")


def extract_tables_with_pdfplumber(file_path: Path, save_tables: bool = False, output_dir: Optional[Path] = None, base_filename: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract tables from PDF using pdfplumber.
    
    Args:
        file_path: Path to PDF file
        save_tables: Whether to save tables to files
        output_dir: Directory to save table files
        base_filename: Base filename for saved files
        
    Returns:
        List of tables with data and metadata
    """
    try:
        import pdfplumber
        
        all_tables = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                
                for table_num, table in enumerate(tables, 1):
                    if table:
                        # Convert table to structured format
                        table_data = {
                            "page": page_num,
                            "table_number": table_num,
                            "rows": len(table),
                            "columns": len(table[0]) if table else 0,
                            "data": table,
                            "headers": table[0] if table else [],
                        }
                        all_tables.append(table_data)
                        
                        # Save table to file if requested
                        if save_tables and output_dir and base_filename:
                            output_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Save as JSON
                            json_filename = f"{base_filename}_table_p{page_num}_t{table_num}.json"
                            json_path = output_dir / json_filename
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(table_data, f, indent=2, ensure_ascii=False)
                            
                            # Save as CSV
                            csv_filename = f"{base_filename}_table_p{page_num}_t{table_num}.csv"
                            csv_path = output_dir / csv_filename
                            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.writer(f)
                                for row in table:
                                    writer.writerow(row)
                            
                            table_data["saved_files"] = {
                                "json": {
                                    "filename": json_filename,
                                    "path": str(json_path)
                                },
                                "csv": {
                                    "filename": csv_filename,
                                    "path": str(csv_path)
                                }
                            }
        
        return all_tables
    except ImportError:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
    except Exception as e:
        raise Exception(f"Error extracting tables: {str(e)}")


def extract_images_with_pymupdf(file_path: Path, save_images: bool = False, output_dir: Optional[Path] = None, base_filename: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract images from PDF using PyMuPDF (fitz).
    
    Args:
        file_path: Path to PDF file
        save_images: Whether to save images to disk
        output_dir: Directory to save images (defaults to file directory)
        base_filename: Base filename for saved images (without extension)
        
    Returns:
        List of images with metadata
    """
    try:
        import fitz  # PyMuPDF
        
        images = []
        
        if save_images and output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_document = fitz.open(file_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_info = {
                    "page": page_num + 1,
                    "image_index": img_index + 1,
                    "format": image_ext,
                    "size_bytes": len(image_bytes),
                    "width": base_image.get("width", 0),
                    "height": base_image.get("height", 0),
                    "colorspace": base_image.get("colorspace", "unknown"),
                }
                
                if save_images and output_dir:
                    # Use base_filename if provided, otherwise use default naming
                    if base_filename:
                        image_filename = f"{base_filename}_image_p{page_num + 1}_i{img_index + 1}.{image_ext}"
                    else:
                        image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                    image_path = output_dir / image_filename
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    image_info["saved_path"] = str(image_path)
                    image_info["filename"] = image_filename
                
                # Include base64 encoded image for small images
                if len(image_bytes) < MAX_BASE64_IMAGE_SIZE:
                    image_info["base64"] = base64.b64encode(image_bytes).decode('utf-8')
                
                images.append(image_info)
        
        pdf_document.close()
        return images
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required. Install with: pip install pymupdf")
    except Exception as e:
        raise Exception(f"Error extracting images: {str(e)}")


def extract_links_with_pymupdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract links from PDF using PyMuPDF (fitz).
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of links with metadata
    """
    try:
        import fitz  # PyMuPDF
        
        all_links = []
        
        pdf_document = fitz.open(file_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            links = page.get_links()
            
            for link_index, link in enumerate(links):
                link_info = {
                    "page": page_num + 1,
                    "link_index": link_index + 1,
                    "type": link.get("kind", "unknown"),
                    "uri": link.get("uri", ""),
                    "page_destination": link.get("page", None),
                    "rect": link.get("from", {}),  # Bounding rectangle
                }
                
                # Clean up empty values
                link_info = {k: v for k, v in link_info.items() if v}
                all_links.append(link_info)
        
        pdf_document.close()
        return all_links
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required. Install with: pip install pymupdf")
    except Exception as e:
        raise Exception(f"Error extracting links: {str(e)}")


# ============================================================================
# Document Parser Tool Functions
# ============================================================================

@mcp.tool()
def parse_pdf(
    file_path: str,
    extract_tables: bool = True,
    extract_images: bool = True,
    extract_links: bool = True,
    save_images: bool = False,
    save_text: bool = False,
    save_tables: bool = False,
    output_dir: Optional[str] = None
) -> str:
    """
    Parse PDF file and extract text, tables, images, and links. Useful for contracts, resumes, and reports.
    
    Args:
        file_path: Path to PDF file (relative to data directory or absolute path)
        extract_tables: Whether to extract tables (default: True)
        extract_images: Whether to extract images (default: True)
        extract_links: Whether to extract links (default: True)
        save_images: Whether to save images to disk (default: False)
        save_text: Whether to save extracted text to files (default: False)
        save_tables: Whether to save extracted tables to files (default: False)
        output_dir: Directory to save extracted content (defaults to file directory/extracted)
        
    Returns:
        JSON string containing parsed document data
    """
    try:
        # Resolve file path
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json_error(f"PDF file not found at {full_path}")
        
        if not full_path.suffix.lower() == '.pdf':
            return json_error(f"File is not a PDF: {full_path}")
        
        # Prepare base filename (without extension) for saved files
        base_filename = full_path.stem
        
        # Set up output directories
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = full_path.parent / "extracted"
        
        text_dir = output_path / "text" if save_text else None
        tables_dir = output_path / "tables" if save_tables else None
        images_dir = output_path / "images" if save_images else None
        
        result = {
            "file_path": str(full_path),
            "filename": full_path.name,
            "file_size": full_path.stat().st_size,
            "base_filename": base_filename,
        }
        
        # Extract text
        try:
            text_data = extract_text_with_pdfplumber(full_path, save_text, text_dir, base_filename)
            result["text"] = text_data["text"]
            result["text_pages"] = text_data["pages"]
            result["metadata"] = text_data["metadata"]
            if "saved_files" in text_data:
                result["text_saved_files"] = text_data["saved_files"]
        except Exception as e:
            result["text_error"] = str(e)
        
        # Extract tables
        if extract_tables:
            try:
                tables = extract_tables_with_pdfplumber(full_path, save_tables, tables_dir, base_filename)
                result["tables"] = tables
                result["tables_count"] = len(tables)
                
                # Collect saved table files
                if save_tables:
                    saved_table_files = []
                    for table in tables:
                        if "saved_files" in table:
                            saved_table_files.append(table["saved_files"])
                    if saved_table_files:
                        result["tables_saved_files"] = saved_table_files
            except Exception as e:
                result["tables_error"] = str(e)
                result["tables"] = []
        
        # Extract images
        if extract_images:
            try:
                images = extract_images_with_pymupdf(full_path, save_images, images_dir, base_filename)
                result["images"] = images
                result["images_count"] = len(images)
            except Exception as e:
                result["images_error"] = str(e)
                result["images"] = []
        
        # Extract links
        if extract_links:
            try:
                links = extract_links_with_pymupdf(full_path)
                result["links"] = links
                result["links_count"] = len(links)
            except Exception as e:
                result["links_error"] = str(e)
                result["links"] = []
        
        # Add output directory info if anything was saved
        if save_text or save_tables or save_images:
            result["output_directory"] = str(output_path)
        
        return json.dumps(result, indent=2, default=str)
    
    except Exception as e:
        return json_error(f"Error parsing PDF: {str(e)}")


@mcp.tool()
def extract_tables(file_path: str, save_tables: bool = False, output_dir: Optional[str] = None) -> str:
    """
    Extract only tables from a PDF file. Useful for structured data extraction from reports.
    
    Args:
        file_path: Path to PDF file (relative to data directory or absolute path)
        save_tables: Whether to save tables to files (default: False)
        output_dir: Directory to save table files (defaults to file directory/tables)
        
    Returns:
        JSON string containing extracted tables
    """
    try:
        # Resolve file path
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json_error(f"PDF file not found at {full_path}")
        
        if not full_path.suffix.lower() == '.pdf':
            return json_error(f"File is not a PDF: {full_path}")
        
        # Prepare base filename
        base_filename = full_path.stem
        
        # Set up output directory
        if output_dir:
            tables_dir = Path(output_dir)
        else:
            tables_dir = full_path.parent / "tables"
        
        # Extract tables
        try:
            tables = extract_tables_with_pdfplumber(full_path, save_tables, tables_dir, base_filename)
            
            result = {
                "file_path": str(full_path),
                "filename": full_path.name,
                "base_filename": base_filename,
                "tables_count": len(tables),
                "tables": tables,
            }
            
            # Collect saved table files
            if save_tables:
                saved_table_files = []
                for table in tables:
                    if "saved_files" in table:
                        saved_table_files.append(table["saved_files"])
                if saved_table_files:
                    result["tables_saved_files"] = saved_table_files
                result["output_directory"] = str(tables_dir)
            
            return json.dumps(result, indent=2, default=str)
        except ImportError as e:
            return json_error(f"Required library not installed: {str(e)}")
        except Exception as e:
            return json_error(f"Error extracting tables: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error in extract_tables: {str(e)}")


@mcp.tool()
def parse_docx(file_path: str) -> str:
    """
    Parse DOCX file and extract content. (Placeholder for future implementation)
    
    Args:
        file_path: Path to DOCX file (relative to data directory or absolute path)
        
    Returns:
        JSON string containing parsed document data
    """
    try:
        # Resolve file path
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json_error(f"DOCX file not found at {full_path}")
        
        if not full_path.suffix.lower() in ['.docx', '.doc']:
            return json_error(f"File is not a DOCX file: {full_path}")
        
        try:
            from docx import Document
            
            doc = Document(full_path)
            
            # Extract text
            paragraphs = [para.text for para in doc.paragraphs]
            
            # Extract tables
            tables_data = []
            for table_num, table in enumerate(doc.tables, 1):
                table_rows = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_rows.append(row_data)
                tables_data.append({
                    "table_number": table_num,
                    "rows": len(table_rows),
                    "data": table_rows,
                })
            
            result = {
                "file_path": str(full_path),
                "filename": full_path.name,
                "text": "\n".join(paragraphs),
                "paragraphs_count": len(paragraphs),
                "tables_count": len(tables_data),
                "tables": tables_data,
            }
            
            return json.dumps(result, indent=2, default=str)
        except ImportError:
            return json_error("python-docx library is required. Install with: pip install python-docx")
        except Exception as e:
            return json_error(f"Error parsing DOCX: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error in parse_docx: {str(e)}")


if __name__ == "__main__":
    mcp.run()

