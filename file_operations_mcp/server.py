import os
import json
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    name="File Operations Tool",
)

# Constants
DATA_DIR = Path(__file__).parent / "data"
SUPPORTED_EXTENSIONS = {
    '.txt': 'text',
    '.json': 'json',
    '.pdf': 'pdf',
    '.doc': 'doc',
    '.docx': 'docx'
}


# ============================================================================
# Common Utility Functions
# ============================================================================

def resolve_path(path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Resolve path to absolute Path object.
    Handles both relative paths (from base directory) and absolute paths.
    
    Args:
        path: Path string (relative or absolute)
        base_dir: Base directory for relative paths. Defaults to DATA_DIR.
        
    Returns:
        Resolved absolute Path object
    """
    if base_dir is None:
        base_dir = DATA_DIR
    
    if os.path.isabs(path):
        return Path(path)
    return base_dir / path


def resolve_file_path(file_path: str) -> Path:
    """
    Resolve file path to absolute Path object.
    Convenience wrapper for resolve_path().
    
    Args:
        file_path: Path string (relative or absolute)
        
    Returns:
        Resolved absolute Path object
    """
    return resolve_path(file_path)


def resolve_directory_path(directory_path: str) -> Path:
    """
    Resolve directory path to absolute Path object.
    Convenience wrapper for resolve_path().
    
    Args:
        directory_path: Path string (relative or absolute)
        
    Returns:
        Resolved absolute Path object
    """
    return resolve_path(directory_path)


def get_file_type(file_path: Path, file_type_hint: Optional[str] = None) -> str:
    """
    Determine file type from extension or hint.
    
    Args:
        file_path: Path object to the file
        file_type_hint: Optional type hint
        
    Returns:
        File type string (txt, json, pdf, doc, docx)
    """
    if file_type_hint:
        return file_type_hint.lower().lstrip('.')
    return file_path.suffix.lower().lstrip('.')


def ensure_directory_exists(file_path: Path) -> None:
    """
    Ensure parent directory exists, create if necessary.
    
    Args:
        file_path: Path object to the file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def json_error(message: str) -> str:
    """
    Create a standardized JSON error response.
    
    Args:
        message: Error message
        
    Returns:
        JSON string with error
    """
    return json.dumps({"error": message}, indent=2)


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


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


# ============================================================================
# File Reader Functions
# ============================================================================

def _read_text_file(file_path: Path) -> str:
    """Read text file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def _read_json_file(file_path: Path) -> str:
    """Read and format JSON file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)


def _read_pdf_file(file_path: Path) -> str:
    """Read PDF file and extract text content."""
    try:
        import PyPDF2
    except ImportError:
        raise ImportError("PyPDF2 library is required for PDF files. Install it with: pip install PyPDF2")
    
    with open(file_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        text_content = []
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text_content.append(f"--- Page {page_num} ---\n{page.extract_text()}\n")
        return "\n".join(text_content)


def _read_doc_file(file_path: Path) -> str:
    """Read DOC/DOCX file and extract text content."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx library is required for DOC/DOCX files. Install it with: pip install python-docx")
    
    doc = Document(file_path)
    text_content = [paragraph.text for paragraph in doc.paragraphs]
    return "\n".join(text_content)


# File reader registry
FILE_READERS = {
    'txt': _read_text_file,
    'json': _read_json_file,
    'pdf': _read_pdf_file,
    'doc': _read_doc_file,
    'docx': _read_doc_file,
}


# ============================================================================
# File Writer Functions
# ============================================================================

def _write_text_file(file_path: Path, content: str) -> None:
    """Write content to text file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def _write_json_file(file_path: Path, content: str) -> None:
    """Write content to JSON file."""
    try:
        json_data = json.loads(content)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # If not valid JSON, write as-is
        _write_text_file(file_path, content)


def _write_pdf_file(file_path: Path, content: str) -> None:
    """Write content to PDF file."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        raise ImportError("reportlab library is required for PDF writing. Install it with: pip install reportlab")
    
    pdf_path = file_path.with_suffix('.pdf')
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    y = height - 50
    lines = content.split('\n')
    for line in lines:
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, line[:80])  # Limit line length
        y -= 15
    
    c.save()


def _write_doc_file(file_path: Path, content: str) -> None:
    """Write content to DOCX file."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx library is required for DOC/DOCX writing. Install it with: pip install python-docx")
    
    doc_path = file_path.with_suffix('.docx')
    doc = Document()
    
    paragraphs = content.split('\n')
    for para_text in paragraphs:
        if para_text.strip():
            doc.add_paragraph(para_text)
    
    doc.save(doc_path)


# File writer registry
FILE_WRITERS = {
    'txt': _write_text_file,
    'json': _write_json_file,
    'pdf': _write_pdf_file,
    'doc': _write_doc_file,
    'docx': _write_doc_file,
}

@mcp.tool()
def read_file(file_path: str) -> str:
    """
    Read content from a file. Supports PDF, JSON, TXT, and DOC files.
    
    Args:
        file_path: Path to the file relative to the data directory, or absolute path
        
    Returns:
        Content of the file as a string
    """
    try:
        # Resolve file path using common utility
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json_error(f"File not found at {full_path}")
        
        # Get file type from extension
        file_type = get_file_type(full_path)
        
        # Use appropriate reader from registry
        if file_type in FILE_READERS:
            reader_func = FILE_READERS[file_type]
            return reader_func(full_path)
        
        # Fallback: try to read as text for unknown extensions
        try:
            return _read_text_file(full_path)
        except UnicodeDecodeError:
            return json_error(f"Cannot read file {file_path}. Unsupported file type or binary file.")
    
    except ImportError as e:
        return json_error(str(e))
    except Exception as e:
        return json_error(f"Error reading file: {str(e)}")

@mcp.tool()
def write_file(file_path: str, content: str, file_type: Optional[str] = None) -> str:
    """
    Write content to a file. Supports PDF, JSON, TXT, and DOC files.
    
    Args:
        file_path: Path to the file relative to the data directory, or absolute path
        content: Content to write to the file
        file_type: Optional file type hint ('txt', 'json', 'pdf', 'doc'). If not provided, inferred from extension
        
    Returns:
        Success message or error message
    """
    try:
        # Resolve file path using common utility
        full_path = resolve_file_path(file_path)
        
        # Ensure directory exists using common utility
        ensure_directory_exists(full_path)
        
        # Get file type using common utility
        file_ext = get_file_type(full_path, file_type)
        
        # Default to text if no extension or type hint
        if not file_ext and not file_type:
            file_ext = 'txt'
        
        # Use appropriate writer from registry
        if file_ext in FILE_WRITERS:
            writer_func = FILE_WRITERS[file_ext]
            writer_func(full_path, content)
            return json_success(
                f"Successfully wrote {file_ext.upper()} content",
                file_path=str(full_path),
                file_type=file_ext
            )
        
        # Fallback: write as text
        _write_text_file(full_path, content)
        return json_success(
            "Successfully wrote content",
            file_path=str(full_path),
            file_type="txt"
        )
    
    except ImportError as e:
        return json_error(str(e))
    except Exception as e:
        return json_error(f"Error writing file: {str(e)}")

# ============================================================================
# Directory Explorer Tool Functions
# ============================================================================

@mcp.tool()
def list_directory(directory_path: str = ".") -> str:
    """
    List files and directories in a given path. Useful for ingestion pipelines and repo scanning.
    
    Args:
        directory_path: Path to the directory relative to the data directory, or absolute path. Defaults to current data directory.
        
    Returns:
        JSON string containing list of files and directories with their metadata
    """
    try:
        # Resolve directory path using common utility
        full_path = resolve_directory_path(directory_path)
        
        if not full_path.exists():
            return json_error(f"Directory not found at {full_path}")
        
        if not full_path.is_dir():
            return json_error(f"Path is not a directory: {full_path}")
        
        items = []
        try:
            for item in sorted(full_path.iterdir()):
                try:
                    stat_info = item.stat()
                    item_info = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat_info.st_size if item.is_file() else None,
                        "size_formatted": format_file_size(stat_info.st_size) if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "extension": item.suffix if item.is_file() else None,
                    }
                    items.append(item_info)
                except (OSError, PermissionError) as e:
                    # Skip items we can't access
                    items.append({
                        "name": item.name,
                        "type": "unknown",
                        "error": str(e)
                    })
        except PermissionError as e:
            return json_error(f"Permission denied: {str(e)}")
        
        result = {
            "path": str(full_path),
            "total_items": len(items),
            "items": items
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json_error(f"Error listing directory: {str(e)}")


@mcp.tool()
def file_metadata(file_path: str) -> str:
    """
    Get detailed metadata about a file or directory. Useful for data discovery and ingestion pipelines.
    
    Args:
        file_path: Path to the file relative to the data directory, or absolute path
        
    Returns:
        JSON string containing file metadata (size, modified time, permissions, type, etc.)
    """
    try:
        # Resolve file path using common utility
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json.dumps({"error": f"File not found at {full_path}"}, indent=2)
        
        try:
            stat_info = full_path.stat()
            
            # Get file type
            file_type = "directory" if full_path.is_dir() else "file"
            file_ext = full_path.suffix.lower() if full_path.is_file() else None
            
            # Get permissions
            mode = stat_info.st_mode
            permissions = {
                "readable": os.access(full_path, os.R_OK),
                "writable": os.access(full_path, os.W_OK),
                "executable": os.access(full_path, os.X_OK),
                "octal": oct(stat.S_IMODE(mode))
            }
            
            metadata = {
                "path": str(full_path),
                "name": full_path.name,
                "type": file_type,
                "extension": file_ext,
                "size_bytes": stat_info.st_size if full_path.is_file() else None,
                "size_formatted": format_file_size(stat_info.st_size) if full_path.is_file() else None,
                "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "permissions": permissions,
                "is_file": full_path.is_file(),
                "is_dir": full_path.is_dir(),
                "is_symlink": full_path.is_symlink(),
            }
            
            # Add file-specific info
            if full_path.is_file():
                metadata["file_type"] = get_file_type(full_path)
                metadata["supported_format"] = file_ext in SUPPORTED_EXTENSIONS
            
            return json.dumps(metadata, indent=2)
        
        except (OSError, PermissionError) as e:
            return json_error(f"Cannot access file metadata: {str(e)}")
    
    except Exception as e:
        return json_error(f"Error getting file metadata: {str(e)}")


@mcp.tool()
def file_search(query: str, search_path: str = ".", recursive: bool = True) -> str:
    """
    Search for files by name pattern. Useful for repo scanning and data discovery.
    
    Args:
        query: Search query (filename pattern, supports wildcards)
        search_path: Path to search in relative to the data directory, or absolute path. Defaults to current data directory.
        recursive: Whether to search recursively in subdirectories. Defaults to True.
        
    Returns:
        JSON string containing list of matching file paths
    """
    try:
        # Resolve search path using common utility
        full_path = resolve_directory_path(search_path)
        
        if not full_path.exists():
            return json_error(f"Search path not found at {full_path}")
        
        if not full_path.is_dir():
            return json_error(f"Search path is not a directory: {full_path}")
        
        matches = []
        query_lower = query.lower()
        
        try:
            if recursive:
                # Recursive search
                for item in full_path.rglob("*"):
                    if item.is_file() and query_lower in item.name.lower():
                        matches.append({
                            "path": str(item),
                            "name": item.name,
                            "relative_path": str(item.relative_to(full_path)),
                            "size": item.stat().st_size,
                            "size_formatted": format_file_size(item.stat().st_size),
                            "extension": item.suffix
                        })
            else:
                # Non-recursive search
                for item in full_path.iterdir():
                    if item.is_file() and query_lower in item.name.lower():
                        matches.append({
                            "path": str(item),
                            "name": item.name,
                            "size": item.stat().st_size,
                            "size_formatted": format_file_size(item.stat().st_size),
                            "extension": item.suffix
                        })
        except (OSError, PermissionError) as e:
            return json_error(f"Error during search: {str(e)}")
        
        result = {
            "query": query,
            "search_path": str(full_path),
            "recursive": recursive,
            "matches_found": len(matches),
            "matches": matches
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json_error(f"Error searching files: {str(e)}")


@mcp.tool()
def file_rename(file_path: str, new_name: str) -> str:
    """
    Rename a file or directory.
    
    Args:
        file_path: Path to the file relative to the data directory, or absolute path
        new_name: New name for the file (without path, just the name)
        
    Returns:
        Success message or error message
    """
    try:
        # Resolve file path using common utility
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json_error(f"File not found at {full_path}")
        
        # Validate new name
        if not new_name or '/' in new_name or '\\' in new_name:
            return json_error("Invalid new name. Use only filename without path.")
        
        # Create new path
        new_path = full_path.parent / new_name
        
        if new_path.exists():
            return json_error(f"File already exists at {new_path}")
        
        # Rename the file
        full_path.rename(new_path)
        
        return json_success(
            f"Successfully renamed to {new_name}",
            old_path=str(full_path),
            new_path=str(new_path)
        )
    
    except PermissionError as e:
        return json_error(f"Permission denied: {str(e)}")
    except Exception as e:
        return json_error(f"Error renaming file: {str(e)}")


@mcp.tool()
def file_delete(file_path: str) -> str:
    """
    Delete a file or directory. Use with caution!
    
    Args:
        file_path: Path to the file relative to the data directory, or absolute path
        
    Returns:
        Success message or error message
    """
    try:
        # Resolve file path using common utility
        full_path = resolve_file_path(file_path)
        
        if not full_path.exists():
            return json_error(f"File not found at {full_path}")
        
        # Safety check: prevent deletion outside data directory for relative paths
        if not os.path.isabs(file_path):
            try:
                full_path.resolve().relative_to(DATA_DIR.resolve())
            except ValueError:
                return json_error("Cannot delete files outside the data directory")
        
        # Delete file or directory
        if full_path.is_dir():
            shutil.rmtree(full_path)
            item_type = "directory"
        else:
            full_path.unlink()
            item_type = "file"
        
        return json_success(
            f"Successfully deleted {item_type}",
            deleted_path=str(full_path),
            type=item_type
        )
    
    except PermissionError as e:
        return json_error(f"Permission denied: {str(e)}")
    except Exception as e:
        return json_error(f"Error deleting file: {str(e)}")

if __name__ == "__main__":
    mcp.run()