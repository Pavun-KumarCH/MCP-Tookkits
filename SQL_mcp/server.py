"""
SQL/DB Query Tool - Structured data access for analytics, reporting, and decision support.

A production-ready MCP server for:
- Executing SQL queries with security guardrails
- Fetching database schemas
- Listing tables and columns
- Multi-database support (SQLite, PostgreSQL, MySQL, MongoDB)

Security Features:
- Read-only mode enforcement
- SQL injection protection
- Row limit enforcement
- Dangerous operation blocking
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded configuration from {env_path}")
else:
    # Fallback to default .env loading
    load_dotenv()
    logger.warning(f".env file not found at {env_path}, using default environment variables")

# Import our modules
from database_connection import create_connection, DatabaseConnection
from query_validator import QueryValidator
from schema_fetcher import SchemaFetcher

# Import JSON serializer
from json_serializer import serialize_value

# Initialize the MCP server
mcp = FastMCP(
    name="SQL MCP Server",
)

# ============================================================================
# Configuration from .env file (all settings loaded here)
# ============================================================================

# Database Type Configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

# Security Configuration
READ_ONLY = os.getenv("READ_ONLY", "true").lower() == "true"
MAX_ROWS = int(os.getenv("MAX_ROWS", "1000"))
QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", "30"))  # seconds

# SQLite Configuration
_sqlite_path = os.getenv("SQLITE_DATABASE_PATH", "./data/database.db")
if not os.path.isabs(_sqlite_path):
    # Resolve relative to server.py location
    _sqlite_path = str(Path(__file__).parent / _sqlite_path.lstrip('./'))

# PostgreSQL Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "test")

# Database connection parameters dictionary (loaded from .env)
DB_CONFIG = {
    "sqlite": {"database_path": _sqlite_path},
    "postgresql": {
        "host": POSTGRES_HOST, "port": POSTGRES_PORT,
        "database": POSTGRES_DATABASE, "user": POSTGRES_USER, "password": POSTGRES_PASSWORD
    },
    "mysql": {
        "host": MYSQL_HOST, "port": MYSQL_PORT,
        "database": MYSQL_DATABASE, "user": MYSQL_USER, "password": MYSQL_PASSWORD
    },
    "mongodb": {"connection_string": MONGODB_URI, "database_name": MONGODB_DATABASE}
}

# Log configuration on startup (without sensitive data)
def _log_configuration():
    """Log configuration in a clean format."""
    logger.info("=" * 60)
    logger.info("SQL MCP Server Configuration")
    logger.info("=" * 60)
    logger.info(f"Database Type: {DB_TYPE}")
    logger.info(f"Read-Only Mode: {READ_ONLY}")
    logger.info(f"Max Rows: {MAX_ROWS}")
    logger.info(f"Query Timeout: {QUERY_TIMEOUT}s")
    
    if DB_TYPE == "sqlite":
        logger.info(f"SQLite Path: {_sqlite_path}")
    elif DB_TYPE == "postgresql":
        logger.info(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}")
        logger.info(f"User: {POSTGRES_USER}")
    elif DB_TYPE == "mysql":
        logger.info(f"MySQL: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
        logger.info(f"User: {MYSQL_USER}")
    elif DB_TYPE == "mongodb":
        logger.info(f"MongoDB: {MONGODB_URI}")
        logger.info(f"Database: {MONGODB_DATABASE}")
    logger.info("=" * 60)

_log_configuration()


# Initialize connection (lazy) - now supports dynamic connections
_db_connection: Optional[DatabaseConnection] = None
_current_db_config: Optional[Dict[str, Any]] = None
_query_validator: Optional[QueryValidator] = None
_schema_fetcher: Optional[SchemaFetcher] = None


def create_db_connection_from_config(
    db_type: str,
    connection_string: str
) -> DatabaseConnection:
    """
    Create a database connection from connection string.
    
    Args:
        db_type: Type of database (sqlite, postgresql, mysql, mongodb)
        connection_string: Connection string/URL
        
    Returns:
        DatabaseConnection instance
    """
    import urllib.parse
    
    db_type_lower = db_type.lower()
    kwargs = {}
    
    # Parse connection string based on database type
    if db_type_lower == "sqlite":
        # SQLite: file path or sqlite:///path/to/db.db
        if connection_string.startswith("sqlite:///"):
            kwargs["database_path"] = connection_string[10:]  # Remove "sqlite:///"
        elif connection_string.startswith("sqlite:"):
            kwargs["database_path"] = connection_string[7:]  # Remove "sqlite:"
        else:
            kwargs["database_path"] = connection_string
                
    elif db_type_lower in ["postgresql", "postgres"]:
        if connection_string.startswith(("postgresql://", "postgres://")):
            parsed = urllib.parse.urlparse(connection_string)
            kwargs.update({
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip('/') or "postgres",
                "user": parsed.username or "postgres",
                "password": parsed.password or ""
            })
        else:
            raise ValueError("PostgreSQL connection string must start with 'postgresql://' or 'postgres://'")
                    
    elif db_type_lower in ["mysql", "mariadb"]:
        if connection_string.startswith("mysql://"):
            parsed = urllib.parse.urlparse(connection_string)
            kwargs.update({
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 3306,
                "database": parsed.path.lstrip('/') or "mysql",
                "user": parsed.username or "root",
                "password": parsed.password or ""
            })
        else:
            raise ValueError("MySQL connection string must start with 'mysql://'")
                    
    elif db_type_lower == "mongodb":
        kwargs["connection_string"] = connection_string
        # Extract database name from connection string if present
        if "/" in connection_string and not connection_string.endswith("/"):
            db_name = connection_string.split("/")[-1].split("?")[0]
            if db_name:
                kwargs["database_name"] = db_name
        kwargs["database_name"] = kwargs.get("database_name") or "test"
    
    # Create connection
    return create_connection(db_type_lower, **kwargs)


def get_db_connection() -> DatabaseConnection:
    """Get or create database connection (uses default from .env if no dynamic connection set)."""
    global _db_connection, _current_db_config
    
    if _db_connection is None:
        try:
            config = DB_CONFIG.get(DB_TYPE, {})
            _current_db_config = {"type": DB_TYPE, **config}
            
            # For SQLite, ensure directory exists
            if DB_TYPE == "sqlite":
                db_path = Path(config.get("database_path", "./data/database.db"))
                if db_path.parent != Path('.'):
                    db_path.parent.mkdir(parents=True, exist_ok=True)
            
            _db_connection = create_connection(DB_TYPE, **config)
            
            if not _db_connection.test_connection():
                raise ConnectionError(f"Failed to connect to {DB_TYPE} database")
            
            logger.info(f"Connected to {DB_TYPE} database")
        except Exception as e:
            logger.error(f"Error creating database connection: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect to {DB_TYPE} database: {str(e)}")
    return _db_connection


def set_db_connection(db_type: str, connection_string: str):
    """
    Set a new database connection dynamically.
    
    Args:
        db_type: Type of database (sqlite, postgresql, mysql, mongodb)
        connection_string: Connection string/URL
        
    Raises:
        ConnectionError: If connection fails
        ValueError: If parameters are invalid
    """
    global _db_connection, _current_db_config, _schema_fetcher
    
    # Close existing connection
    if _db_connection:
        try:
            _db_connection.close()
        except Exception:
            pass  # Ignore errors when closing
    
    # Create and test new connection
    try:
        _db_connection = create_db_connection_from_config(db_type, connection_string)
        if not _db_connection.test_connection():
            raise ConnectionError(f"Connection test failed for {db_type}")
    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        raise ConnectionError(f"Failed to connect to {db_type}: {str(e)}")
    
    # Reset schema fetcher and store config
    _schema_fetcher = None
    _current_db_config = {
        "type": db_type.lower(),
        "connection_string": connection_string
    }
    
    logger.info(f"Connected to {db_type} database")


def get_query_validator() -> QueryValidator:
    """Get or create query validator."""
    global _query_validator
    if _query_validator is None:
        _query_validator = QueryValidator(read_only=READ_ONLY, max_rows=MAX_ROWS)
    return _query_validator


def get_schema_fetcher() -> SchemaFetcher:
    """Get or create schema fetcher."""
    global _schema_fetcher
    if _schema_fetcher is None:
        _schema_fetcher = SchemaFetcher(get_db_connection())
    return _schema_fetcher


# ============================================================================
# Utility Functions
# ============================================================================

def json_error(message: str, **kwargs) -> str:
    """Create a standardized JSON error response."""
    result = {"error": message, **kwargs}
    return json.dumps(result, indent=2)


def json_success(message: str, **kwargs) -> str:
    """Create a standardized JSON success response."""
    result = {"success": True, "message": message, **kwargs}
    return json.dumps(result, indent=2)


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
def connect_database(db_type: str, connection_string: str) -> str:
    """
    Connect to a database dynamically using a connection string.
    Useful for connecting to different databases at runtime.
    
    Args:
        db_type: Type of database (sqlite, postgresql, mysql, mongodb)
        connection_string: Full connection string/URL
            - SQLite: "/path/to/database.db" or "sqlite:///path/to/database.db"
            - PostgreSQL: "postgresql://user:password@host:port/database"
            - MySQL: "mysql://user:password@host:port/database"
            - MongoDB: "mongodb://host:port/" or "mongodb://user:password@host:port/database"
        
    Returns:
        JSON string containing connection status
    """
    try:
        db_type_lower = db_type.lower()
        
        # Validate database type
        valid_types = ["sqlite", "postgresql", "postgres", "mysql", "mariadb", "mongodb"]
        if db_type_lower not in valid_types:
            return json_error(
                f"Invalid database type: {db_type}. Supported types: {', '.join(valid_types)}"
            )
        
        # Validate connection string
        if not connection_string or not connection_string.strip():
            return json_error("Connection string cannot be empty")
        
        # Set the connection
        set_db_connection(db_type_lower, connection_string.strip())
        
        # Mask password in connection string for response
        masked_connection = connection_string
        if "@" in masked_connection:
            parts = masked_connection.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split(":")
                if len(user_pass) > 1:
                    masked_connection = f"{user_pass[0]}:****@{parts[1]}"
        
        return json_success(
            f"Successfully connected to {db_type} database",
            db_type=db_type_lower,
            connected=True,
            connection_string=masked_connection
        )
    except ConnectionError as e:
        error_msg = str(e)
        # Provide helpful suggestions based on error
        suggestion = ""
        if "Connection refused" in error_msg:
            if db_type_lower in ["postgresql", "postgres"]:
                suggestion = "Check if PostgreSQL is running and verify the port (default: 5432). Try: docker ps | grep postgres"
            elif db_type_lower in ["mysql", "mariadb"]:
                suggestion = "Check if MySQL is running and verify the port (default: 3306). Try: docker ps | grep mysql"
            elif db_type_lower == "mongodb":
                suggestion = "Check if MongoDB is running and verify the port (default: 27017). Try: docker ps | grep mongo"
        elif "unable to open database file" in error_msg.lower():
            suggestion = "Check if the SQLite database path exists and is accessible"
        
        logger.error(f"Connection error: {e}", exc_info=True)
        return json_error(
            f"Failed to connect to database: {error_msg}",
            suggestion=suggestion if suggestion else None
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return json_error(f"Invalid connection string: {str(e)}")
    except Exception as e:
        logger.error(f"Error in connect_database: {e}", exc_info=True)
        return json_error(f"Failed to connect to database: {str(e)}")




@mcp.tool()
def run_query(sql: str, limit: Optional[int] = None) -> str:
    """
    Execute a SQL query with security guardrails. Useful for analytics, reporting, and data retrieval.
    
    Args:
        sql: SQL query to execute
        limit: Optional row limit override (defaults to MAX_ROWS from config)
        
    Returns:
        JSON string containing query results or error message
    """
    try:
        # Validate input
        if not sql or not sql.strip():
            return json_error("SQL query cannot be empty")
        
        # Get validator with optional limit override
        max_rows = limit if limit else MAX_ROWS
        validator = QueryValidator(read_only=READ_ONLY, max_rows=max_rows)
        
        # Validate query
        is_valid, error_msg = validator.validate(sql)
        if not is_valid:
            return json_error(error_msg or "Query validation failed")
        
        # Sanitize and add limit
        sanitized_query = validator.sanitize_query(sql)
        sanitized_query = validator.add_limit_if_needed(sanitized_query)
        
        # Execute query
        result = get_db_connection().execute_query(sanitized_query)
        
        # Format response (results already serialized by database connection)
        if result.get("success"):
            return json_success(
                "Query executed successfully",
                **result
            )
        else:
            return json_error(result.get("error", "Query execution failed"))
            
    except Exception as e:
        logger.error(f"Error in run_query: {e}", exc_info=True)
        error_msg = str(e)
        # Provide more helpful error messages
        if "unrecognized token" in error_msg.lower():
            return json_error(
                f"SQL syntax error: {error_msg}. Please check your query syntax."
            )
        return json_error(f"Failed to execute query: {error_msg}")


@mcp.tool()
def fetch_schema(table_name: Optional[str] = None) -> str:
    """
    Fetch database schema information. Useful for understanding database structure before querying.
    
    Args:
        table_name: Optional table name to get schema for specific table (defaults to all tables)
        
    Returns:
        JSON string containing schema information
    """
    try:
        fetcher = get_schema_fetcher()
        schema = fetcher.get_table_info(table_name) if table_name else fetcher.get_full_schema()
        
        return json_success(
            "Schema fetched successfully",
            schema=schema,
            formatted=fetcher.format_schema_for_display(schema)
        )
    except Exception as e:
        logger.error(f"Error in fetch_schema: {e}", exc_info=True)
        return json_error(f"Failed to fetch schema: {str(e)}")


@mcp.tool()
def list_tables() -> str:
    """
    List all tables in the database. Useful for discovering available data sources.
    
    Returns:
        JSON string containing list of table names
    """
    try:
        fetcher = get_schema_fetcher()
        tables = fetcher.list_all_tables()
        
        return json_success(
            f"Found {len(tables)} tables",
            tables=tables,
            count=len(tables)
        )
    except Exception as e:
        logger.error(f"Error in list_tables: {e}", exc_info=True)
        return json_error(f"Failed to list tables: {str(e)}")


@mcp.tool()
def describe_table(table_name: str) -> str:
    """
    Get detailed information about a specific table including columns, types, row count, and statistics.
    
    Args:
        table_name: Name of the table to describe
        
    Returns:
        JSON string containing table description and statistics
    """
    try:
        fetcher = get_schema_fetcher()
        table_info = fetcher.get_table_info(table_name)
        columns = fetcher.get_table_columns(table_name)
        
        formatted = fetcher.format_schema_for_display(table_info)
        
        # Include statistics in response
        stats = {
            "table_name": table_name,
            "row_count": table_info.get("row_count"),
            "column_count": len(columns),
            "columns": [
                {
                    "name": col.get("name"),
                    "type": col.get("type") or col.get("data_type"),
                    "nullable": not col.get("not_null", False) if "not_null" in col else None,
                    "primary_key": col.get("primary_key", False)
                }
                for col in columns
            ]
        }
        
        return json_success(
            f"Table '{table_name}' described successfully",
            **stats,
            formatted=formatted
        )
    except Exception as e:
        logger.error(f"Error in describe_table: {e}", exc_info=True)
        return json_error(f"Failed to describe table: {str(e)}")












# Run the server
if __name__ == "__main__":
    mcp.run()
