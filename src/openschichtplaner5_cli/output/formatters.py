# openschichtplaner5-cli/src/openschichtplaner5_cli/output/formatters.py
"""
Advanced output formatters for CLI results.
"""

import json
import calendar
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from ..core.exceptions import OutputFormatError


@dataclass
class FormatConfig:
    """Configuration for output formatting."""
    color_output: bool = True
    max_field_width: int = 50
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    truncate_long_fields: bool = True


class BaseFormatter:
    """Base class for all formatters."""
    
    def __init__(self, config: Optional[FormatConfig] = None):
        self.config = config or FormatConfig()
    
    def _truncate_text(self, text: str, max_width: int = None) -> str:
        """Truncate text if too long."""
        if not self.config.truncate_long_fields:
            return text
        
        max_width = max_width or self.config.max_field_width
        if len(text) <= max_width:
            return text
        
        return text[:max_width - 3] + "..."
    
    def _format_value(self, value: Any) -> str:
        """Format a single value for display."""
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, date):
            return value.strftime(self.config.date_format)
        elif isinstance(value, datetime):
            return value.strftime(f"{self.config.date_format} {self.config.time_format}")
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)


class TableFormatter(BaseFormatter):
    """Formats data as ASCII tables."""
    
    def format(self, records: List[Dict[str, Any]], 
               fields: Optional[List[str]] = None,
               title: Optional[str] = None) -> str:
        """Format records as a table."""
        if not records:
            return "No records found."
        
        # Determine fields to display
        if not fields:
            # Use all fields except internal ones
            fields = [k for k in records[0].keys() 
                     if not k.startswith('_') and not k.endswith('_related')]
        
        # Calculate column widths
        widths = {}
        for field in fields:
            # Start with field name width
            widths[field] = len(field)
            
            # Check all record values
            for record in records:
                value_str = self._format_value(record.get(field))
                if self.config.truncate_long_fields:
                    value_str = self._truncate_text(value_str)
                widths[field] = max(widths[field], len(value_str))
        
        # Build table
        lines = []
        
        # Title
        if title:
            total_width = sum(widths.values()) + (len(fields) - 1) * 3  # 3 for " | "
            lines.append(title.center(total_width))
            lines.append("=" * total_width)
        
        # Header
        header_parts = []
        for field in fields:
            header_parts.append(f"{field:{widths[field]}}")
        lines.append(" | ".join(header_parts))
        
        # Separator
        separator_parts = []
        for field in fields:
            separator_parts.append("-" * widths[field])
        lines.append("-+-".join(separator_parts))
        
        # Data rows
        for record in records:
            row_parts = []
            for field in fields:
                value_str = self._format_value(record.get(field))
                if self.config.truncate_long_fields:
                    value_str = self._truncate_text(value_str)
                row_parts.append(f"{value_str:{widths[field]}}")
            lines.append(" | ".join(row_parts))
        
        return "\n".join(lines)
    
    def format_key_value(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        """Format data as key-value pairs."""
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * len(title))
        
        # Calculate key width
        key_width = max(len(str(k)) for k in data.keys()) if data else 0
        
        for key, value in data.items():
            if key.startswith('_'):
                continue
            
            formatted_value = self._format_value(value)
            if isinstance(value, (list, dict)):
                formatted_value = str(value)  # Could be improved
            
            lines.append(f"{key:{key_width}} : {formatted_value}")
        
        return "\n".join(lines)


class EmployeeFormatter(BaseFormatter):
    """Specialized formatter for employee data."""
    
    def format_basic_info(self, employee: Dict[str, Any]) -> str:
        """Format basic employee information."""
        lines = [
            f"\n{'='*60}",
            f"Employee: {employee.get('name', '')} {employee.get('firstname', '')}",
            f"ID: {employee.get('id', '')} | Number: {employee.get('number', '')}",
        ]
        
        if employee.get('position'):
            lines.append(f"Position: {employee.get('position', '')}")
        
        if employee.get('function'):
            lines.append(f"Function: {employee.get('function', '')}")
        
        if employee.get('email'):
            lines.append(f"Email: {employee.get('email', '')}")
        
        if employee.get('phone'):
            lines.append(f"Phone: {employee.get('phone', '')}")
        
        if employee.get('empstart'):
            lines.append(f"Employment Start: {self._format_value(employee.get('empstart'))}")
        
        return "\n".join(lines)
    
    def format_full_profile(self, profile: Dict[str, Any]) -> str:
        """Format full employee profile with related data."""
        lines = []
        
        # Basic info
        lines.append(self.format_basic_info(profile))
        
        # Related data
        for table_name, data in profile.items():
            if table_name.endswith("_related") and data:
                clean_name = table_name.replace("_related", "").replace("5", "")
                lines.append(f"\n{clean_name.title()}:")
                lines.append("-" * (len(clean_name) + 1))
                
                if isinstance(data, list):
                    # Show first few items
                    for i, item in enumerate(data[:5]):
                        if isinstance(item, dict):
                            summary = self._summarize_record(item)
                            lines.append(f"  {i+1}. {summary}")
                        else:
                            lines.append(f"  {i+1}. {item}")
                    
                    if len(data) > 5:
                        lines.append(f"  ... and {len(data) - 5} more")
                else:
                    if isinstance(data, dict):
                        summary = self._summarize_record(data)
                        lines.append(f"  {summary}")
                    else:
                        lines.append(f"  {data}")
        
        return "\n".join(lines)
    
    def format_schedule_table(self, schedule: List[Dict[str, Any]]) -> str:
        """Format employee schedule as a table."""
        if not schedule:
            return "No schedule entries found."
        
        # Prepare data for table formatting
        table_data = []
        for entry in schedule:
            shift_info = entry.get('5SHIFT_related', {})
            workplace_info = entry.get('5WOPL_related', {})
            
            table_data.append({
                'date': entry.get('date'),
                'shift': shift_info.get('name', 'Unknown'),
                'short': shift_info.get('shortname', ''),
                'start': shift_info.get('start_time', ''),
                'end': shift_info.get('end_time', ''),
                'workplace': workplace_info.get('name', 'Unknown'),
                'hours': shift_info.get('hours', '')
            })
        
        formatter = TableFormatter(self.config)
        return formatter.format(table_data, 
                              ['date', 'shift', 'start', 'end', 'workplace', 'hours'])
    
    def format_schedule_calendar(self, schedule: List[Dict[str, Any]], 
                                start_date: date, end_date: date) -> str:
        """Format schedule as a calendar view."""
        # Group schedule by date
        schedule_by_date = {}
        for entry in schedule:
            entry_date = entry.get('date')
            if isinstance(entry_date, str):
                entry_date = datetime.strptime(entry_date, '%Y-%m-%d').date()
            
            if entry_date:
                schedule_by_date[entry_date] = entry
        
        lines = [f"\nCalendar view: {start_date} to {end_date}"]
        lines.append("=" * 50)
        
        current_date = start_date
        current_month = None
        
        while current_date <= end_date:
            # Month header
            if current_date.month != current_month:
                current_month = current_date.month
                month_name = calendar.month_name[current_month]
                lines.append(f"\n{month_name} {current_date.year}")
                lines.append("-" * 20)
            
            # Day entry
            day_str = current_date.strftime("%a %d")
            if current_date in schedule_by_date:
                entry = schedule_by_date[current_date]
                shift_info = entry.get('5SHIFT_related', {})
                shift_name = shift_info.get('shortname') or shift_info.get('name', 'Shift')
                lines.append(f"{day_str}: {shift_name}")
            else:
                lines.append(f"{day_str}: -")
            
            # Next day
            from datetime import timedelta
            current_date += timedelta(days=1)
        
        return "\n".join(lines)
    
    def _summarize_record(self, record: Dict[str, Any]) -> str:
        """Create a one-line summary of a record."""
        # Try common summary fields
        if 'name' in record:
            summary = record['name']
            if 'date' in record:
                summary += f" ({self._format_value(record['date'])})"
            return summary
        elif 'date' in record and 'shift_id' in record:
            return f"Shift on {self._format_value(record['date'])}"
        elif 'leave_type_id' in record and 'date' in record:
            return f"Leave on {self._format_value(record['date'])}"
        else:
            # Generic summary with first few fields
            parts = []
            for key, value in list(record.items())[:3]:
                if not key.startswith('_') and value is not None:
                    parts.append(f"{key}={self._format_value(value)}")
            return ", ".join(parts) if parts else "Record"


class JSONFormatter(BaseFormatter):
    """Formats data as JSON."""
    
    def format(self, data: Any, indent: int = 2) -> str:
        """Format data as JSON string."""
        try:
            return json.dumps(data, indent=indent, default=self._json_serializer, 
                            ensure_ascii=False)
        except Exception as e:
            raise OutputFormatError("json", f"Failed to serialize data: {e}")
    
    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for special types."""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class YAMLFormatter(BaseFormatter):
    """Formats data as YAML."""
    
    def format(self, data: Any) -> str:
        """Format data as YAML string."""
        try:
            import yaml
            return yaml.dump(data, default_flow_style=False, 
                           default=self._yaml_serializer, allow_unicode=True)
        except ImportError:
            raise OutputFormatError("yaml", "PyYAML not installed")
        except Exception as e:
            raise OutputFormatError("yaml", f"Failed to serialize data: {e}")
    
    def _yaml_serializer(self, obj: Any) -> str:
        """Custom YAML serializer for special types."""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class CSVFormatter(BaseFormatter):
    """Formats data as CSV."""
    
    def format(self, records: List[Dict[str, Any]], 
               fields: Optional[List[str]] = None) -> str:
        """Format records as CSV."""
        if not records:
            return ""
        
        import csv
        import io
        
        output = io.StringIO()
        
        # Determine fields
        if not fields:
            fields = [k for k in records[0].keys() 
                     if not k.startswith('_') and not k.endswith('_related')]
        
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        
        for record in records:
            # Convert values to strings
            row = {}
            for field in fields:
                value = record.get(field)
                row[field] = self._format_value(value)
            writer.writerow(row)
        
        return output.getvalue()


def get_formatter(format_type: str, config: Optional[FormatConfig] = None):
    """Get formatter instance for the specified format type."""
    formatters = {
        'table': TableFormatter,
        'json': JSONFormatter,
        'yaml': YAMLFormatter,
        'csv': CSVFormatter,
        'employee': EmployeeFormatter
    }
    
    if format_type not in formatters:
        raise OutputFormatError(format_type, f"Unknown format type. Available: {list(formatters.keys())}")
    
    return formatters[format_type](config)