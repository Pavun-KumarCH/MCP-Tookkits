"""
File ingestion module for reading and processing .txt files.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Generator

logger = logging.getLogger(__name__)


class FileIngestion:
    """Handle ingestion of text files."""
    
    def __init__(self, text_folder: str):
        """
        Initialize file ingestion.
        
        Args:
            text_folder: Path to folder containing .txt files
        """
        self.text_folder = Path(text_folder)
        if not self.text_folder.exists():
            raise ValueError(f"Text folder does not exist: {text_folder}")
        if not self.text_folder.is_dir():
            raise ValueError(f"Path is not a directory: {text_folder}")
    
    def get_txt_files(self) -> List[Path]:
        """
        Get all .txt files in the folder.
        
        Returns:
            List of Path objects for .txt files
        """
        txt_files = list(self.text_folder.glob("*.txt"))
        logger.info(f"Found {len(txt_files)} .txt files in {self.text_folder}")
        return txt_files
    
    def read_file(self, file_path: Path) -> str:
        """
        Read content from a text file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def split_into_chunks(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Split text into chunks for embedding with optimized boundary detection.
        
        Args:
            text: Input text
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Validate inputs
        if not text or not text.strip():
            return []
        
        if chunk_size <= 0:
            logger.warning(f"Invalid chunk_size: {chunk_size}, using default 1000")
            chunk_size = 1000
        
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            logger.warning(f"Invalid chunk_overlap: {chunk_overlap}, adjusting to {chunk_size // 5}")
            chunk_overlap = chunk_size // 5
        
        # Return single chunk if text is small enough
        if len(text) <= chunk_size:
            return [text.strip()]
        
        chunks = []
        start = 0
        text_len = len(text)
        
        # Sentence boundary characters for smarter splitting
        sentence_endings = {'.', '!', '?', '\n'}
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            # If not at the end, try to find a good break point
            if end < text_len:
                # Look for sentence boundaries within the last 30% of chunk
                search_start = max(start, end - int(chunk_size * 0.3))
                best_break = -1
                
                # Check for sentence endings
                for i in range(end - 1, search_start - 1, -1):
                    if text[i] in sentence_endings:
                        # Check if followed by space or newline
                        if i + 1 < text_len and (text[i + 1] == ' ' or text[i + 1] == '\n'):
                            best_break = i + 1
                            break
                
                # If no sentence boundary found, look for paragraph breaks
                if best_break == -1:
                    best_break = text.rfind('\n\n', search_start, end)
                    if best_break != -1:
                        best_break += 2
                
                # If still no good break, look for single newline
                if best_break == -1:
                    best_break = text.rfind('\n', search_start, end)
                    if best_break != -1:
                        best_break += 1
                
                # Use break point if found and reasonable
                if best_break != -1 and best_break > start + chunk_size * 0.5:
                    end = best_break
            
            # Extract chunk and add to list
            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Move start forward with overlap
            start = max(start + 1, end - chunk_overlap)
            
            # Prevent infinite loop
            if start >= end:
                start = end
        
        return chunks
    
    def process_file(
        self,
        file_path: Path,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Generator[Dict[str, str], None, None]:
        """
        Process a file and yield chunks with metadata.
        
        Args:
            file_path: Path to the file
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Yields:
            Dictionary with 'text', 'source_file', and 'chunk_index'
        """
        try:
            content = self.read_file(file_path)
            chunks = self.split_into_chunks(content, chunk_size, chunk_overlap)
            
            for idx, chunk in enumerate(chunks):
                if chunk.strip():  # Only yield non-empty chunks
                    yield {
                        "text": chunk,
                        "source_file": str(file_path.name),
                        "chunk_index": idx,
                        "total_chunks": len(chunks)
                    }
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise
    
    def ingest_all_files(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Generator[Dict[str, str], None, None]:
        """
        Process all .txt files in the folder.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Yields:
            Dictionary with 'text', 'source_file', and 'chunk_index'
        """
        txt_files = self.get_txt_files()
        
        for file_path in txt_files:
            logger.info(f"Processing file: {file_path.name}")
            try:
                for chunk_data in self.process_file(file_path, chunk_size, chunk_overlap):
                    yield chunk_data
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue