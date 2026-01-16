"""
Schema fetcher module for retrieving database schema information.
"""

import logging
from typing import Dict, Any, List, Optional
from database_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SchemaFetcher:
    """Fetch and format database schema information."""
    
    def __init__(self, connection: DatabaseConnection):
        """
        Initialize schema fetcher.
        
        Args:
            connection: Database connection instance
        """
        self.connection = connection
    
    def get_full_schema(self) -> Dict[str, Any]:
        """
        Get full database schema.
        
        Returns:
            Schema dictionary
        """
        try:
            return self.connection.get_schema()
        except Exception as e:
            logger.error(f"Error fetching schema: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific table including row count.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Table information dictionary
        """
        try:
            schema = self.connection.get_schema(table_name)
            
            # Get row count if possible (optimized query)
            try:
                # Use efficient COUNT query
                result = self.connection.execute_query(f"SELECT COUNT(*) as count FROM {table_name} LIMIT 1")
                if result.get('rows'):
                    schema['row_count'] = result['rows'][0].get('count', 0)
                else:
                    schema['row_count'] = None
            except Exception as e:
                logger.debug(f"Could not get row count for {table_name}: {e}")
                schema['row_count'] = None
            
            return schema
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            raise
    
    def list_all_tables(self) -> List[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        try:
            return self.connection.list_tables()
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column dictionaries
        """
        try:
            schema = self.connection.get_schema(table_name)
            return schema.get('columns', [])
        except Exception as e:
            logger.error(f"Error getting table columns: {e}")
            raise
    
    def format_schema_for_display(self, schema: Dict[str, Any]) -> str:
        """
        Format schema as a readable string.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            Formatted string
        """
        if 'table_name' in schema:
            # Single table schema
            output = [f"Table: {schema['table_name']}"]
            if 'row_count' in schema:
                output.append(f"Rows: {schema['row_count']}")
            output.append("\nColumns:")
            
            for col in schema.get('columns', []):
                col_info = f"  - {col.get('name', 'unknown')}"
                if 'type' in col:
                    col_info += f" ({col['type']})"
                if col.get('primary_key'):
                    col_info += " [PRIMARY KEY]"
                if col.get('not_null'):
                    col_info += " [NOT NULL]"
                output.append(col_info)
            
            return "\n".join(output)
        else:
            # Full database schema
            output = [f"Database: {schema.get('database', 'unknown')}"]
            output.append(f"Tables: {len(schema.get('tables', {}))}")
            output.append("\nTable List:")
            
            for table_name, table_schema in schema.get('tables', {}).items():
                output.append(f"  - {table_name}")
                if 'row_count' in table_schema:
                    output.append(f"    Rows: {table_schema['row_count']}")
            
            return "\n".join(output)
