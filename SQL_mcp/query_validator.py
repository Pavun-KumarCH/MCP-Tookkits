"""
Query validator module with SQL injection protection and read-only enforcement.

Security features:
- SQL injection detection
- Read-only mode enforcement
- Row limit enforcement
- Dangerous operation blocking
"""

import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validate SQL queries with security guardrails."""
    
    # Dangerous SQL keywords that modify data
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 
        'UPDATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
        'CALL', 'MERGE', 'COPY', 'LOAD', 'BACKUP', 'RESTORE'
    ]
    
    # Keywords that are allowed in read-only mode
    ALLOWED_KEYWORDS = [
        'SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'PRAGMA',
        'WITH', 'WITH RECURSIVE'
    ]
    
    # SQL injection patterns
    INJECTION_PATTERNS = [
        r'(\bOR\b|\bAND\b)\s*[\'"]?\s*\d+\s*=\s*\d+',  # OR 1=1, AND 1=1
        r'(\bUNION\b.*\bSELECT\b)',  # UNION SELECT
        r'(\bEXEC\b|\bEXECUTE\b)',  # EXEC/EXECUTE
        r'(\bDROP\b.*\bTABLE\b|\bDROP\b.*\bDATABASE\b)',  # DROP TABLE/DATABASE
        r'(\bINSERT\b.*\bINTO\b)',  # INSERT INTO
        r'(\bUPDATE\b.*\bSET\b)',  # UPDATE SET
        r'(\bDELETE\b.*\bFROM\b)',  # DELETE FROM
        r'(\bALTER\b.*\bTABLE\b)',  # ALTER TABLE
        r'(\bCREATE\b.*\bTABLE\b)',  # CREATE TABLE
        r'(\bTRUNCATE\b)',  # TRUNCATE
        r'(\'\s*;\s*--|\'\s*;\s*\/\*|\'\s*;\s*#)',  # SQL comment injection
        r'(\bWAITFOR\b.*\bDELAY\b)',  # Time-based SQL injection
        r'(\bBENCHMARK\b)',  # Benchmark injection
    ]
    
    def __init__(self, read_only: bool = True, max_rows: int = 1000):
        """
        Initialize query validator.
        
        Args:
            read_only: Enforce read-only mode (default: True)
            max_rows: Maximum number of rows to return (default: 1000)
        """
        self.read_only = read_only
        self.max_rows = max_rows
    
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a SQL query.
        
        Args:
            query: SQL query string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        query_upper = query.upper().strip()
        
        # Check for SQL injection patterns
        injection_check = self._check_sql_injection(query)
        if not injection_check[0]:
            logger.warning(f"SQL injection detected: {injection_check[1]}")
            return False, f"Potential SQL injection detected: {injection_check[1]}"
        
        # Check for dangerous keywords
        dangerous_check = self._check_dangerous_keywords(query_upper)
        if not dangerous_check[0]:
            logger.warning(f"Dangerous keyword detected: {dangerous_check[1]}")
            return False, f"Dangerous operation detected: {dangerous_check[1]}"
        
        # Enforce read-only mode
        if self.read_only:
            read_only_check = self._check_read_only(query_upper)
            if not read_only_check[0]:
                logger.warning(f"Read-only violation: {read_only_check[1]}")
                return False, f"Read-only mode: {read_only_check[1]}"
        
        # Check query length
        if len(query) > 100000:  # 100KB limit
            return False, "Query exceeds maximum length of 100KB"
        
        return True, None
    
    def _check_sql_injection(self, query: str) -> Tuple[bool, Optional[str]]:
        """Check for SQL injection patterns."""
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Pattern matched: {pattern}"
        return True, None
    
    def _check_dangerous_keywords(self, query_upper: str) -> Tuple[bool, Optional[str]]:
        """Check for dangerous SQL keywords."""
        for keyword in self.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, query_upper):
                return False, f"Dangerous keyword found: {keyword}"
        return True, None
    
    def _check_read_only(self, query_upper: str) -> Tuple[bool, Optional[str]]:
        """Check if query violates read-only mode."""
        # Check if query starts with allowed keywords
        query_words = query_upper.split()
        if not query_words:
            return False, "Empty query"
        
        query_start = query_words[0]
        
        # Allow SELECT, SHOW, DESCRIBE, EXPLAIN, WITH queries
        if query_start not in self.ALLOWED_KEYWORDS:
            return False, f"Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH queries are allowed in read-only mode"
        
        # Additional check: ensure no write operations anywhere in query
        write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']
        for keyword in write_keywords:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                return False, f"Write operation '{keyword}' is not allowed in read-only mode"
        
        return True, None
    
    def add_limit_if_needed(self, query: str) -> str:
        """
        Add LIMIT clause if not present and query is a SELECT.
        
        Args:
            query: SQL query string
            
        Returns:
            Query with LIMIT clause added if needed
        """
        if not query or not query.strip():
            return query
        
        query_upper = query.upper().strip()
        
        # Only add LIMIT to SELECT queries
        if not query_upper.startswith('SELECT'):
            return query
        
        # Check if LIMIT already exists (check at end of query, not in subqueries)
        # Look for LIMIT at the end of the query (before semicolon if present)
        query_without_semicolon = query.rstrip().rstrip(';')
        query_without_semicolon_upper = query_without_semicolon.upper().strip()
        
        # Check if LIMIT exists at the end
        limit_pattern = r'LIMIT\s+\d+(\s*$|\s*;|\s*--|\s*/\*)'
        if re.search(limit_pattern, query_without_semicolon_upper, re.IGNORECASE):
            # Extract existing limit and ensure it's within max_rows
            limit_match = re.search(r'LIMIT\s+(\d+)', query_without_semicolon_upper, re.IGNORECASE)
            if limit_match:
                existing_limit = int(limit_match.group(1))
                if existing_limit > self.max_rows:
                    # Replace with max_rows - find the last LIMIT occurrence
                    # Use a more precise pattern to replace only the last LIMIT
                    parts = re.split(r'(\s+LIMIT\s+\d+)', query_without_semicolon, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        # Replace the last LIMIT part
                        parts[-2] = f' LIMIT {self.max_rows}'
                        query_without_semicolon = ''.join(parts)
                        query = query_without_semicolon + (';' if query.rstrip().endswith(';') else '')
                        logger.info(f"Limited query to {self.max_rows} rows")
            return query
        
        # Add LIMIT clause at the end (before semicolon if present)
        has_semicolon = query.rstrip().endswith(';')
        query_base = query.rstrip().rstrip(';').rstrip()
        
        # Add LIMIT before any trailing comments
        # Check for comments at the end
        comment_match = re.search(r'(\s*(--.*|/\*.*\*/)\s*)$', query_base, re.DOTALL | re.IGNORECASE)
        if comment_match:
            # Insert LIMIT before comment
            comment = comment_match.group(1)
            query_base = query_base[:comment_match.start()].rstrip()
            query = query_base + f' LIMIT {self.max_rows}' + comment
        else:
            # No comments, just add LIMIT
            query = query_base + f' LIMIT {self.max_rows}'
        
        # Add semicolon back if it was there
        if has_semicolon:
            query += ';'
        
        logger.info(f"Added LIMIT {self.max_rows} to query")
        return query
    
    def sanitize_query(self, query: str) -> str:
        """
        Sanitize query by removing comments and extra whitespace.
        
        Args:
            query: SQL query string
            
        Returns:
            Sanitized query
        """
        # Remove SQL comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)  # Single-line comments
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)  # Multi-line comments
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        return query.strip()


