# openschichtplaner5-cli/src/openschichtplaner5_cli/utils/parsing.py
"""
Advanced parsing utilities for CLI arguments and filters.
"""

import re
import shlex
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from ..core.exceptions import CommandError


@dataclass
class FilterCondition:
    """Represents a parsed filter condition."""
    field: str
    operator: str
    value: Any
    value_type: str = "string"


class FilterParser:
    """Parses filter expressions into structured conditions."""
    
    # Supported operators in order of precedence
    OPERATORS = [
        '>=', '<=', '!=', '==', '=', '>', '<',
        'contains', 'startswith', 'endswith', 'matches',
        'in', 'not_in', 'is_null', 'not_null'
    ]
    
    # Type conversion patterns
    TYPE_PATTERNS = {
        'int': re.compile(r'^-?\d+$'),
        'float': re.compile(r'^-?\d*\.\d+$'),
        'bool': re.compile(r'^(true|false|yes|no|1|0)$', re.IGNORECASE),
        'date': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'datetime': re.compile(r'^\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}(:\d{2})?$'),
        'list': re.compile(r'^\[.*\]$'),
    }
    
    def parse_filter(self, filter_expr: str) -> FilterCondition:
        """
        Parse a filter expression into a FilterCondition.
        
        Examples:
        - "name=Schmidt"
        - "age>=25"
        - "position!=Manager"
        - "department in [HR,IT,Finance]"
        - "active=true"
        - "start_date>=2024-01-01"
        """
        # Handle quoted expressions
        if '"' in filter_expr or "'" in filter_expr:
            filter_expr = self._handle_quotes(filter_expr)
        
        # Find the operator
        operator = None
        for op in self.OPERATORS:
            if op in filter_expr:
                # Make sure it's not part of a value
                parts = filter_expr.split(op, 1)
                if len(parts) == 2:
                    field, value = parts[0].strip(), parts[1].strip()
                    if field and value:  # Both parts must be non-empty
                        operator = op
                        break
        
        if not operator:
            raise CommandError("filter", f"Invalid filter expression: {filter_expr}")
        
        # Clean field name
        field = field.strip()
        if not field:
            raise CommandError("filter", f"Empty field name in filter: {filter_expr}")
        
        # Parse and convert value
        parsed_value, value_type = self._parse_value(value.strip())
        
        return FilterCondition(
            field=field,
            operator=self._normalize_operator(operator),
            value=parsed_value,
            value_type=value_type
        )
    
    def parse_multiple_filters(self, filter_expressions: List[str]) -> List[FilterCondition]:
        """Parse multiple filter expressions."""
        return [self.parse_filter(expr) for expr in filter_expressions]
    
    def _handle_quotes(self, expr: str) -> str:
        """Handle quoted strings in expressions."""
        # Use shlex to properly handle quotes
        try:
            tokens = shlex.split(expr)
            # Reconstruct with proper spacing
            return ' '.join(tokens)
        except ValueError:
            # If shlex fails, return original
            return expr
    
    def _parse_value(self, value_str: str) -> Tuple[Any, str]:
        """Parse and convert a value string to appropriate type."""
        if not value_str:
            return None, "null"
        
        # Check for null/none
        if value_str.lower() in ('null', 'none', 'empty'):
            return None, "null"
        
        # Check for list notation [a,b,c]
        if self.TYPE_PATTERNS['list'].match(value_str):
            return self._parse_list(value_str), "list"
        
        # Check for boolean
        if self.TYPE_PATTERNS['bool'].match(value_str):
            return self._parse_bool(value_str), "bool"
        
        # Check for date
        if self.TYPE_PATTERNS['date'].match(value_str):
            try:
                return datetime.strptime(value_str, '%Y-%m-%d').date(), "date"
            except ValueError:
                pass
        
        # Check for datetime
        if self.TYPE_PATTERNS['datetime'].match(value_str):
            try:
                # Try different datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M']:
                    try:
                        return datetime.strptime(value_str, fmt), "datetime"
                    except ValueError:
                        continue
            except ValueError:
                pass
        
        # Check for integer
        if self.TYPE_PATTERNS['int'].match(value_str):
            return int(value_str), "int"
        
        # Check for float
        if self.TYPE_PATTERNS['float'].match(value_str):
            return float(value_str), "float"
        
        # Default to string (remove quotes if present)
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1], "string"
        
        return value_str, "string"
    
    def _parse_list(self, list_str: str) -> List[Any]:
        """Parse a list string [a,b,c] into a list of values."""
        # Remove brackets
        inner = list_str[1:-1].strip()
        if not inner:
            return []
        
        # Split by comma and parse each item
        items = []
        for item in inner.split(','):
            item = item.strip()
            if item:
                parsed_item, _ = self._parse_value(item)
                items.append(parsed_item)
        
        return items
    
    def _parse_bool(self, bool_str: str) -> bool:
        """Parse a boolean string."""
        return bool_str.lower() in ('true', 'yes', '1')
    
    def _normalize_operator(self, op: str) -> str:
        """Normalize operator to standard form."""
        # Convert = to == for consistency
        if op == '=':
            return '=='
        return op


class ArgumentValidator:
    """Validates and processes command line arguments."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_dbf_path(self, path: str) -> Optional[str]:
        """Validate DBF directory path."""
        from pathlib import Path
        
        if not path:
            self.errors.append("DBF path cannot be empty")
            return None
        
        path_obj = Path(path).expanduser().resolve()
        
        if not path_obj.exists():
            self.errors.append(f"DBF path does not exist: {path_obj}")
            return None
        
        if not path_obj.is_dir():
            self.errors.append(f"DBF path is not a directory: {path_obj}")
            return None
        
        # Check for at least one DBF file
        dbf_files = list(path_obj.glob("*.DBF")) + list(path_obj.glob("*.dbf"))
        if not dbf_files:
            self.warnings.append(f"No DBF files found in directory: {path_obj}")
        
        return str(path_obj)
    
    def validate_output_format(self, format_name: str, valid_formats: List[str]) -> bool:
        """Validate output format."""
        if format_name not in valid_formats:
            self.errors.append(f"Invalid format '{format_name}'. Valid formats: {', '.join(valid_formats)}")
            return False
        return True
    
    def validate_date_string(self, date_str: str, field_name: str = "date") -> Optional[date]:
        """Validate and parse date string."""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            self.errors.append(f"Invalid {field_name} format. Expected YYYY-MM-DD, got: {date_str}")
            return None
    
    def validate_employee_id(self, emp_id: int) -> bool:
        """Validate employee ID."""
        if emp_id <= 0:
            self.errors.append(f"Employee ID must be positive, got: {emp_id}")
            return False
        return True
    
    def validate_group_id(self, group_id: int) -> bool:
        """Validate group ID."""
        if group_id <= 0:
            self.errors.append(f"Group ID must be positive, got: {group_id}")
            return False
        return True
    
    def validate_limit(self, limit: int) -> bool:
        """Validate result limit."""
        if limit <= 0:
            self.errors.append(f"Limit must be positive, got: {limit}")
            return False
        if limit > 10000:
            self.warnings.append(f"Very large limit specified: {limit}")
        return True
    
    def validate_file_output(self, file_path: str) -> Optional[str]:
        """Validate output file path."""
        from pathlib import Path
        
        if not file_path:
            return None
        
        path_obj = Path(file_path).expanduser().resolve()
        
        # Check if parent directory exists
        if not path_obj.parent.exists():
            self.errors.append(f"Output directory does not exist: {path_obj.parent}")
            return None
        
        # Check if parent is writable
        import os
        if not os.access(path_obj.parent, os.W_OK):
            self.errors.append(f"Cannot write to output directory: {path_obj.parent}")
            return None
        
        # Warn if file already exists
        if path_obj.exists():
            self.warnings.append(f"Output file already exists and will be overwritten: {path_obj}")
        
        return str(path_obj)
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return bool(self.errors)
    
    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return bool(self.warnings)
    
    def get_error_summary(self) -> str:
        """Get formatted error summary."""
        if not self.errors:
            return "No errors"
        
        summary = f"Found {len(self.errors)} error(s):\n"
        for i, error in enumerate(self.errors, 1):
            summary += f"  {i}. {error}\n"
        
        return summary.rstrip()
    
    def get_warning_summary(self) -> str:
        """Get formatted warning summary."""
        if not self.warnings:
            return "No warnings"
        
        summary = f"Found {len(self.warnings)} warning(s):\n"
        for i, warning in enumerate(self.warnings, 1):
            summary += f"  {i}. {warning}\n"
        
        return summary.rstrip()
    
    def reset(self) -> None:
        """Reset validation state."""
        self.errors.clear()
        self.warnings.clear()


def smart_type_conversion(value: str) -> Any:
    """Smart type conversion for command line values."""
    parser = FilterParser()
    converted_value, _ = parser._parse_value(value)
    return converted_value


def parse_key_value_pairs(expressions: List[str]) -> Dict[str, Any]:
    """Parse key=value expressions into a dictionary."""
    result = {}
    parser = FilterParser()
    
    for expr in expressions:
        if '=' not in expr:
            raise CommandError("parsing", f"Invalid key=value expression: {expr}")
        
        key, value = expr.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        if not key:
            raise CommandError("parsing", f"Empty key in expression: {expr}")
        
        converted_value, _ = parser._parse_value(value)
        result[key] = converted_value
    
    return result