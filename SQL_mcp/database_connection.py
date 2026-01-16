"""
Database connection module supporting multiple database backends.

Supports:
- SQLite (via Docker or local file)
- PostgreSQL
- MySQL/MariaDB
- MongoDB (NoSQL)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import json

# Import JSON serializer for date/datetime handling
from json_serializer import serialize_rows, serialize_dict, serialize_value

logger = logging.getLogger(__name__)


class DatabaseConnection(ABC):
    """Abstract base class for database connections."""
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a query and return results."""
        pass
    
    @abstractmethod
    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database or table schema."""
        pass
    
    @abstractmethod
    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        pass
    
    @abstractmethod
    def close(self):
        """Close the database connection."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connection is working."""
        pass


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection."""
    
    def __init__(self, database_path: str):
        """
        Initialize SQLite connection.
        
        Args:
            database_path: Path to SQLite database file or connection string
        """
        import sqlite3
        from pathlib import Path
        
        self.database_path = database_path
        
        # Create directory if it doesn't exist
        db_path = Path(database_path)
        if db_path.parent != Path('.'):
            db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory for SQLite database: {db_path.parent}")
        
        # Connect to database (creates file if it doesn't exist)
        try:
            self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
            logger.info(f"Connected to SQLite database: {database_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to SQLite database at {database_path}: {e}")
            raise ConnectionError(f"SQLite connection failed: {e}")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a SQL query."""
        try:
            cursor = self.conn.cursor()
            
            # Convert params dict to tuple if needed
            param_tuple = tuple(params.values()) if params else None
            
            cursor.execute(query, param_tuple if param_tuple else ())
            
            # Check if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                
                # Convert rows to list of dicts and serialize dates/datetimes
                results = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    # Serialize date/datetime objects
                    serialized_row = serialize_dict(row_dict)
                    results.append(serialized_row)
                
                return {
                    "success": True,
                    "rows": results,
                    "row_count": len(results),
                    "columns": columns
                }
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE)
                self.conn.commit()
                return {
                    "success": True,
                    "rows_affected": cursor.rowcount,
                    "message": "Query executed successfully"
                }
        except Exception as e:
            logger.error(f"Error executing SQLite query: {e}")
            raise
    
    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema."""
        try:
            cursor = self.conn.cursor()
            
            if table_name:
                # Get schema for specific table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                return {
                    "table_name": table_name,
                    "columns": [
                        {
                            "name": col[1],
                            "type": col[2],
                            "not_null": bool(col[3]),
                            "default_value": col[4],
                            "primary_key": bool(col[5])
                        }
                        for col in columns
                    ]
                }
            else:
                # Get all tables schema
                tables = self.list_tables()
                return {
                    "database": self.database_path,
                    "tables": {table: self.get_schema(table) for table in tables}
                }
        except Exception as e:
            logger.error(f"Error getting SQLite schema: {e}")
            raise
    
    def list_tables(self) -> List[str]:
        """List all tables."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            logger.error(f"Error listing SQLite tables: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"SQLite connection test failed: {e}")
            return False
    
    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("SQLite connection closed")


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection."""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        """Initialize PostgreSQL connection."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            try:
                self.conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    connect_timeout=10  # 10 second timeout
                )
                self.conn.set_session(autocommit=False)
                logger.info(f"Connected to PostgreSQL: {host}:{port}/{database}")
            except psycopg2.OperationalError as e:
                error_msg = str(e)
                if "Connection refused" in error_msg:
                    raise ConnectionError(
                        f"Cannot connect to PostgreSQL at {host}:{port}. "
                        f"Check if the server is running and the port is correct (default: 5432). "
                        f"Error: {error_msg}"
                    )
                elif "password authentication failed" in error_msg.lower():
                    raise ConnectionError(
                        f"PostgreSQL authentication failed for user '{user}'. "
                        f"Check username and password."
                    )
                elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                    raise ConnectionError(
                        f"PostgreSQL database '{database}' does not exist. "
                        f"Create it first or use an existing database."
                    )
                else:
                    raise ConnectionError(f"PostgreSQL connection error: {error_msg}")
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a SQL query."""
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params if params else None)
            
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                results = serialize_rows([dict(row) for row in rows])
                return {
                    "success": True,
                    "rows": results,
                    "row_count": len(results),
                    "columns": list(results[0].keys()) if results else []
                }
            else:
                self.conn.commit()
                return {
                    "success": True,
                    "rows_affected": cursor.rowcount,
                    "message": "Query executed successfully"
                }
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error executing PostgreSQL query: {e}")
            raise
    
    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema."""
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            if table_name:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                
                return {
                    "table_name": table_name,
                    "columns": [dict(col) for col in cursor.fetchall()]
                }
            else:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' ORDER BY table_name
                """)
                
                tables = [row['table_name'] for row in cursor.fetchall()]
                return {
                    "database": self.conn.info.dbname,
                    "tables": {table: self.get_schema(table) for table in tables}
                }
        except Exception as e:
            logger.error(f"Error getting PostgreSQL schema: {e}")
            raise
    
    def list_tables(self) -> List[str]:
        """List all tables."""
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            return [row['table_name'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing PostgreSQL tables: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("PostgreSQL connection closed")


class MySQLConnection(DatabaseConnection):
    """MySQL/MariaDB database connection."""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        """Initialize MySQL connection."""
        try:
            import pymysql
            
            try:
                self.conn = pymysql.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=10  # 10 second timeout
                )
                logger.info(f"Connected to MySQL: {host}:{port}/{database}")
            except pymysql.err.OperationalError as e:
                error_code, error_msg = e.args[0], str(e)
                if error_code == 2003:  # Can't connect to MySQL server
                    raise ConnectionError(
                        f"Cannot connect to MySQL at {host}:{port}. "
                        f"Check if the server is running and the port is correct (default: 3306). "
                        f"Error: {error_msg}"
                    )
                elif error_code == 1045:  # Access denied
                    raise ConnectionError(
                        f"MySQL authentication failed for user '{user}'. "
                        f"Check username and password."
                    )
                elif error_code == 1049:  # Unknown database
                    raise ConnectionError(
                        f"MySQL database '{database}' does not exist. "
                        f"Create it first or use an existing database."
                    )
                else:
                    raise ConnectionError(f"MySQL connection error: {error_msg}")
        except ImportError:
            raise ImportError("pymysql is required for MySQL. Install with: pip install pymysql")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a SQL query."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params if params else None)
            
            if query.strip().upper().startswith('SELECT'):
                rows = serialize_rows(cursor.fetchall())
                return {
                    "success": True,
                    "rows": rows,
                    "row_count": len(rows),
                    "columns": list(rows[0].keys()) if rows else []
                }
            else:
                self.conn.commit()
                return {
                    "success": True,
                    "rows_affected": cursor.rowcount,
                    "message": "Query executed successfully"
                }
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error executing MySQL query: {e}")
            raise
    
    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema."""
        try:
            cursor = self.conn.cursor()
            
            if table_name:
                cursor.execute(f"DESCRIBE {table_name}")
                return {
                    "table_name": table_name,
                    "columns": cursor.fetchall()
                }
            else:
                cursor.execute("SHOW TABLES")
                tables = [list(row.values())[0] for row in cursor.fetchall()]
                db_name = self.conn.db.decode() if isinstance(self.conn.db, bytes) else self.conn.db
                
                return {
                    "database": db_name,
                    "tables": {table: self.get_schema(table) for table in tables}
                }
        except Exception as e:
            logger.error(f"Error getting MySQL schema: {e}")
            raise
    
    def list_tables(self) -> List[str]:
        """List all tables."""
        try:
            import pymysql
            
            cursor = self.conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            return [list(row.values())[0] for row in tables]
        except Exception as e:
            logger.error(f"Error listing MySQL tables: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"MySQL connection test failed: {e}")
            return False
    
    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("MySQL connection closed")


class MongoDBConnection(DatabaseConnection):
    """MongoDB connection (NoSQL)."""
    
    def __init__(self, connection_string: str, database_name: str):
        """Initialize MongoDB connection."""
        try:
            from pymongo import MongoClient
            
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            logger.info(f"Connected to MongoDB: {database_name}")
        except ImportError:
            raise ImportError("pymongo is required for MongoDB. Install with: pip install pymongo")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a MongoDB query (converted from SQL-like syntax)."""
        try:
            import json
            from bson import json_util
            
            # Parse MongoDB query (simplified - expects JSON)
            query_dict = json.loads(query) if isinstance(query, str) else query
            
            collection_name = query_dict.get("collection")
            operation = query_dict.get("operation", "find")
            filter_query = query_dict.get("filter", {})
            projection = query_dict.get("projection", {})
            limit = query_dict.get("limit", 1000)
            
            collection = self.db[collection_name]
            
            if operation == "find":
                cursor = collection.find(filter_query, projection).limit(limit)
                results = list(cursor)
                
                # Convert ObjectId to string for JSON serialization
                for doc in results:
                    if '_id' in doc:
                        doc['_id'] = str(doc['_id'])
                
                return {
                    "success": True,
                    "rows": results,
                    "row_count": len(results),
                    "columns": list(results[0].keys()) if results else []
                }
            elif operation == "aggregate":
                pipeline = query_dict.get("pipeline", [])
                cursor = collection.aggregate(pipeline)
                results = list(cursor)
                
                for doc in results:
                    if '_id' in doc:
                        doc['_id'] = str(doc['_id'])
                
                return {
                    "success": True,
                    "rows": results,
                    "row_count": len(results)
                }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}"
                }
        except Exception as e:
            logger.error(f"Error executing MongoDB query: {e}")
            raise
    
    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get MongoDB collection schema."""
        try:
            if table_name:
                collection = self.db[table_name]
                # Sample documents to infer schema
                sample = collection.find_one()
                
                schema = {
                    "collection_name": table_name,
                    "sample_document": sample
                }
                
                if sample:
                    schema["fields"] = list(sample.keys())
                
                return schema
            else:
                collections = self.db.list_collection_names()
                schema = {
                    "database": self.db.name,
                    "collections": {}
                }
                
                for coll_name in collections:
                    schema["collections"][coll_name] = self.get_schema(coll_name)
                
                return schema
        except Exception as e:
            logger.error(f"Error getting MongoDB schema: {e}")
            raise
    
    def list_tables(self) -> List[str]:
        """List all collections."""
        try:
            return self.db.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing MongoDB collections: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection."""
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")
            return False
    
    def close(self):
        """Close connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


def create_connection(db_type: str, **kwargs) -> DatabaseConnection:
    """
    Factory function to create database connections.
    
    Args:
        db_type: Type of database ('sqlite', 'postgresql', 'mysql', 'mongodb')
        **kwargs: Connection parameters
        
    Returns:
        DatabaseConnection instance
    """
    db_type_lower = db_type.lower()
    
    if db_type_lower == 'sqlite':
        database_path = kwargs.get('database_path') or kwargs.get('database')
        if not database_path:
            raise ValueError("SQLite requires 'database_path' parameter")
        return SQLiteConnection(database_path)
    
    elif db_type_lower in ['postgresql', 'postgres']:
        required = ['host', 'port', 'database', 'user', 'password']
        missing = [k for k in required if k not in kwargs]
        if missing:
            raise ValueError(f"PostgreSQL requires: {', '.join(missing)}")
        return PostgreSQLConnection(**{k: kwargs[k] for k in required})
    
    elif db_type_lower in ['mysql', 'mariadb']:
        required = ['host', 'port', 'database', 'user', 'password']
        missing = [k for k in required if k not in kwargs]
        if missing:
            raise ValueError(f"MySQL requires: {', '.join(missing)}")
        return MySQLConnection(**{k: kwargs[k] for k in required})
    
    elif db_type_lower == 'mongodb':
        connection_string = kwargs.get('connection_string') or kwargs.get('uri')
        database_name = kwargs.get('database_name') or kwargs.get('database')
        if not connection_string or not database_name:
            raise ValueError("MongoDB requires 'connection_string' and 'database_name'")
        return MongoDBConnection(connection_string, database_name)
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
