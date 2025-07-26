# openschichtplaner5-cli/src/openschichtplaner5_cli/output/tables.py
"""
Table formatting utilities.
"""

from typing import Any, Dict, List, Optional
from .formatters import TableFormatter, FormatConfig


def create_table(records: List[Dict[str, Any]], 
                fields: Optional[List[str]] = None,
                title: Optional[str] = None,
                config: Optional[FormatConfig] = None) -> str:
    """Create a formatted table from records."""
    formatter = TableFormatter(config)
    return formatter.format(records, fields, title)


def format_record_table(records: List[Any], 
                       title: Optional[str] = None) -> str:
    """Format arbitrary record objects as a table."""
    if not records:
        return "No records found."
    
    # Convert objects to dictionaries
    dict_records = []
    for record in records:
        if hasattr(record, '__dict__'):
            dict_records.append(record.__dict__)
        elif isinstance(record, dict):
            dict_records.append(record)
        else:
            # Try to convert to dict
            try:
                dict_records.append(vars(record))
            except TypeError:
                dict_records.append({'value': str(record)})
    
    return create_table(dict_records, title=title)