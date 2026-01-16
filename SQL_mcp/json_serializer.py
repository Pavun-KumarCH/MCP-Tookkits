"""
JSON serialization utilities for database results.
Handles date, datetime, and other non-JSON-serializable types.
"""

import json
import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def serialize_value(value: Any) -> Any:
    """
    Serialize a value to JSON-safe format.
    
    Args:
        value: Value to serialize
        
    Returns:
        JSON-serializable value
    """
    if value is None:
        return None
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, time):
        return value.isoformat()
    elif isinstance(value, timedelta):
        return str(value)
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    elif isinstance(value, (dict, Dict)):
        return serialize_dict(value)
    elif isinstance(value, (list, tuple, List)):
        return [serialize_value(item) for item in value]
    elif isinstance(value, (int, float, str, bool)):
        return value
    else:
        # Try to convert to string as fallback
        try:
            return str(value)
        except Exception as e:
            logger.warning(f"Could not serialize value {type(value)}: {e}")
            return None


def serialize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a dictionary with date/datetime handling.
    
    Args:
        data: Dictionary to serialize
        
    Returns:
        Serialized dictionary
    """
    return {key: serialize_value(value) for key, value in data.items()}


def serialize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Serialize a list of row dictionaries.
    
    Args:
        rows: List of row dictionaries
        
    Returns:
        List of serialized row dictionaries
    """
    return [serialize_dict(row) for row in rows]
