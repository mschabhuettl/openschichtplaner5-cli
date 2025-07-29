# src/openschichtplaner5_cli/batch_operations.py
"""
Batch operations for the CLI.
Allows executing multiple commands from files or scripts.
"""

import logging
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

from libopenschichtplaner5.query_engine import QueryEngine
from libopenschichtplaner5.export import DataExporter
from libopenschichtplaner5.performance import monitor_performance, performance_monitor

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class BatchCommand:
    """Single command in a batch."""
    line_number: int
    command: str
    args: List[str]
    options: Dict[str, Any]
    variables: Dict[str, str] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}

    def expand_variables(self, context: Dict[str, Any]) -> "BatchCommand":
        """Expand variables in command."""
        expanded_command = self.command
        expanded_args = []

        # Expand command
        for var, value in context.items():
            expanded_command = expanded_command.replace(f"${{{var}}}", str(value))

        # Expand args
        for arg in self.args:
            expanded_arg = arg
            for var, value in context.items():
                expanded_arg = expanded_arg.replace(f"${{{var}}}", str(value))
            expanded_args.append(expanded_arg)

        return BatchCommand(
            line_number=self.line_number,
            command=expanded_command,
            args=expanded_args,
            options=self.options,
            variables=self.variables
        )


@dataclass
class BatchResult:
    """Result of a batch command execution."""
    command: BatchCommand
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "line": self.command.line_number,
            "command": f"{self.command.command} {' '.join(self.command.args)}",
            "success": self.success,
            "duration": round(self.duration, 3),
            "error": self.error
        }


class BatchParser:
    """Parse batch command files."""

    # Command patterns
    PATTERNS = {
        "comment": re.compile(r'^\s*#.*$'),
        "variable": re.compile(r'^\s*SET\s+(\w+)\s*=\s*(.+)$', re.IGNORECASE),
        "for_loop": re.compile(r'^\s*FOR\s+(\w+)\s+IN\s+(.+)\s*:$', re.IGNORECASE),
        "if_statement": re.compile(r'^\s*IF\s+(.+)\s*:$', re.IGNORECASE),
        "command": re.compile(r'^\s*(\w+)\s*(.*)$')
    }

    def parse_file(self, filepath: Path) -> List[BatchCommand]:
        """Parse a batch file."""
        commands = []
        context = {}

        with open(filepath, 'r') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            line_number = i + 1

            # Skip empty lines and comments
            if not line or self.PATTERNS["comment"].match(line):
                i += 1
                continue

            # Variable assignment
            var_match = self.PATTERNS["variable"].match(line)
            if var_match:
                var_name = var_match.group(1)
                var_value = var_match.group(2).strip()
                context[var_name] = self._evaluate_value(var_value, context)
                i += 1
                continue

            # FOR loop
            for_match = self.PATTERNS["for_loop"].match(line)
            if for_match:
                var_name = for_match.group(1)
                items_expr = for_match.group(2).strip()

                # Parse loop body
                loop_commands = []
                i += 1
                indent_level = self._get_indent_level(lines[i]) if i < len(lines) else 0

                while i < len(lines):
                    if self._get_indent_level(lines[i]) < indent_level:
                        break
                    loop_commands.append(lines[i])
                    i += 1

                # Execute loop
                items = self._parse_list(items_expr, context)
                for item in items:
                    loop_context = context.copy()
                    loop_context[var_name] = item

                    # Parse commands in loop body
                    for cmd_line in loop_commands:
                        cmd = self._parse_command_line(cmd_line.strip(), line_number, loop_context)
                        if cmd:
                            commands.append(cmd)
                continue

            # Regular command
            cmd = self._parse_command_line(line, line_number, context)
            if cmd:
                commands.append(cmd)
            i += 1

        return commands

    def _parse_command_line(self, line: str, line_number: int, context: Dict[str, Any]) -> Optional[BatchCommand]:
        """Parse a single command line."""
        if not line or line.startswith('#'):
            return None

        # Expand variables
        for var, value in context.items():
            line = line.replace(f"${{{var}}}", str(value))

        # Parse command and arguments
        parts = line.split()
        if not parts:
            return None

        command = parts[0]
        args = []
        options = {}

        i = 1
        while i < len(parts):
            if parts[i].startswith('--'):
                # Option with value
                opt_name = parts[i][2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith('-'):
                    options[opt_name] = parts[i + 1]
                    i += 2
                else:
                    options[opt_name] = True
                    i += 1
            elif parts[i].startswith('-'):
                # Short option
                opt_name = parts[i][1:]
                options[opt_name] = True
                i += 1
            else:
                # Regular argument
                args.append(parts[i])
                i += 1

        return BatchCommand(
            line_number=line_number,
            command=command,
            args=args,
            options=options,
            variables=context.copy()
        )

    def _evaluate_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate a value expression."""
        # Remove quotes
        if (expr.startswith('"') and expr.endswith('"')) or \
                (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # Check for numbers
        if expr.isdigit():
            return int(expr)

        try:
            return float(expr)
        except ValueError:
            pass

        # Check for boolean
        if expr.lower() in ['true', 'false']:
            return expr.lower() == 'true'

        # Variable reference
        if expr.startswith('$'):
            var_name = expr[1:].strip('{}')
            return context.get(var_name, expr)

        return expr

    def _parse_list(self, expr: str, context: Dict[str, Any]) -> List[Any]:
        """Parse a list expression."""
        # Range expression: 1..10
        if '..' in expr:
            parts = expr.split('..')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return list(range(int(parts[0]), int(parts[1]) + 1))

        # Comma-separated list
        if ',' in expr:
            return [self._evaluate_value(item.strip(), context) for item in expr.split(',')]

        # Single value
        return [self._evaluate_value(expr, context)]

    def _get_indent_level(self, line: str) -> int:
        """Get indentation level of a line."""
        return len(line) - len(line.lstrip())


class BatchExecutor:
    """Execute batch commands."""

    def __init__(self, engine: QueryEngine):
        self.engine = engine
        self.exporter = DataExporter()
        self.context = {}  # Shared context for variables
        self.results = []

    @monitor_performance("batch_execution")
    def execute_batch(self, commands: List[BatchCommand],
                      dry_run: bool = False,
                      stop_on_error: bool = True) -> List[BatchResult]:
        """Execute a batch of commands."""
        self.results = []

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
        ) as progress:

            task = progress.add_task(
                f"Executing {len(commands)} commands...",
                total=len(commands)
            )

            for i, command in enumerate(commands):
                progress.update(task, description=f"[{i + 1}/{len(commands)}] {command.command}")

                if dry_run:
                    console.print(f"[dim]Would execute: {command.command} {' '.join(command.args)}[/dim]")
                    progress.advance(task)
                    continue

                # Execute command
                result = self._execute_command(command)
                self.results.append(result)

                # Show result
                if result.success:
                    console.print(f"[green]✓[/green] Line {command.line_number}: {command.command}")
                else:
                    console.print(f"[red]✗[/red] Line {command.line_number}: {result.error}")
                    if stop_on_error:
                        break

                progress.advance(task)

        return self.results

    def _execute_command(self, command: BatchCommand) -> BatchResult:
        """Execute a single command."""
        import time
        start_time = time.time()

        try:
            # Expand variables in command
            expanded = command.expand_variables(self.context)

            # Route to appropriate handler
            if expanded.command.upper() == "QUERY":
                output = self._execute_query(expanded)
            elif expanded.command.upper() == "EXPORT":
                output = self._execute_export(expanded)
            elif expanded.command.upper() == "SET":
                output = self._execute_set(expanded)
            elif expanded.command.upper() == "PRINT":
                output = self._execute_print(expanded)
            else:
                raise ValueError(f"Unknown command: {expanded.command}")

            duration = time.time() - start_time
            return BatchResult(command, True, output, duration=duration)

        except Exception as e:
            duration = time.time() - start_time
            return BatchResult(command, False, error=str(e), duration=duration)

    def _execute_query(self, command: BatchCommand) -> Any:
        """Execute a query command."""
        if not command.args:
            raise ValueError("Query requires table name")

        table = command.args[0]
        query = self.engine.query().select(table)

        # Apply filters from options
        for key, value in command.options.items():
            if key.startswith("where_"):
                field = key[6:]  # Remove 'where_' prefix
                query = query.where(field, "=", value)

        # Limit
        if "limit" in command.options:
            query = query.limit(int(command.options["limit"]))

        result = query.execute()

        # Store in context if variable name provided
        if "var" in command.options:
            self.context[command.options["var"]] = result.to_dict()

        return result.count

    def _execute_export(self, command: BatchCommand) -> Any:
        """Execute an export command."""
        if len(command.args) < 3:
            raise ValueError("Export requires: table format filename")

        table, format, filename = command.args[0], command.args[1], command.args[2]

        # Get data
        data = [r.__dict__ for r in self.engine.loaded_tables.get(table, [])]

        # Export
        self.exporter.export(data, format, Path(filename))
        return f"Exported {len(data)} records to {filename}"

    def _execute_set(self, command: BatchCommand) -> Any:
        """Execute a set variable command."""
        if len(command.args) < 2:
            raise ValueError("SET requires: variable value")

        var_name = command.args[0]
        value = " ".join(command.args[1:])

        # Evaluate value
        if value.isdigit():
            value = int(value)
        elif value.lower() in ['true', 'false']:
            value = value.lower() == 'true'

        self.context[var_name] = value
        return f"Set {var_name} = {value}"

    def _execute_print(self, command: BatchCommand) -> Any:
        """Execute a print command."""
        message = " ".join(command.args)

        # Expand variables
        for var, value in self.context.items():
            message = message.replace(f"${{{var}}}", str(value))

        console.print(message)
        return message

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        total_duration = sum(r.duration for r in self.results)

        return {
            "total_commands": len(self.results),
            "successful": successful,
            "failed": failed,
            "total_duration": round(total_duration, 3),
            "avg_duration": round(total_duration / len(self.results), 3) if self.results else 0
        }

    def export_results(self, filepath: Path):
        """Export batch results."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
            "context": self.context
        }

        if filepath.suffix == '.json':
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        elif filepath.suffix == '.yaml':
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)


# Example batch files

EXAMPLE_BATCH_SIMPLE = """
# Simple batch example
SET OUTPUT_DIR = "./exports"

# Export all employees
EXPORT 5EMPL csv ${OUTPUT_DIR}/employees.csv

# Query and export active employees  
QUERY 5EMPL --where_empend = null --var active_employees
PRINT Found ${active_employees} active employees
"""

EXAMPLE_BATCH_LOOP = """
# Loop example - export each group separately
SET OUTPUT_DIR = "./exports/groups"

# Get all groups
QUERY 5GROUP --var groups

# Export each group's members
FOR group_id IN 1,2,3,4,5:
    QUERY 5GRASG --where_group_id = ${group_id} --var members
    EXPORT 5GRASG csv ${OUTPUT_DIR}/group_${group_id}.csv
    PRINT Exported group ${group_id}
"""

EXAMPLE_BATCH_ANALYSIS = """
# Analysis batch - generate reports for each department
SET YEAR = 2024
SET OUTPUT_DIR = "./reports"

# For each major department
FOR dept IN IT,Sales,Support,Admin:
    # Find employees in department
    QUERY 5EMPL --where_position = ${dept} --var dept_employees

    # Export absence report
    QUERY 5ABSEN --where_year = ${YEAR} --var absences
    EXPORT 5ABSEN excel ${OUTPUT_DIR}/${dept}_absences_${YEAR}.xlsx

    # Print summary
    PRINT Department ${dept}: ${dept_employees} employees, ${absences} absences in ${YEAR}
"""