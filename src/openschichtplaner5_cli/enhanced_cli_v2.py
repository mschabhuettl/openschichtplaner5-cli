# src/openschichtplaner5_cli/enhanced_cli_v2.py
"""
Enhanced CLI v2 with Rich UI, interactive mode, and configuration support.
"""

import argparse
import json
import yaml
import os
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
import sys
import readline  # For command history
from functools import wraps
import time

# Rich imports for better UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.syntax import Syntax
from rich.tree import Tree
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.theme import Theme

# Import library components with improved versions
try:
    # Use improved versions if available
    from libopenschichtplaner5.registry_improved import enhanced_registry as registry
    from libopenschichtplaner5.relationships_improved import improved_relationship_manager
except ImportError:
    # Fallback to original
    from libopenschichtplaner5.registry import load_table, TABLE_NAMES
    from libopenschichtplaner5.relationships import relationship_manager as improved_relationship_manager

from libopenschichtplaner5.query_engine import QueryEngine, FilterOperator
from libopenschichtplaner5.reports import ReportGenerator
from libopenschichtplaner5.export import DataExporter, ReportExporter, ExportFormat
from libopenschichtplaner5.utils.validation import DataValidator
from libopenschichtplaner5.exceptions import DataNotFoundError, SchichtplanerError

# Custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "bold magenta",
    "muted": "dim white",
})

console = Console(theme=custom_theme)


class ConfigManager:
    """Manages CLI configuration."""

    DEFAULT_CONFIG = {
        "defaults": {
            "output_format": "table",
            "verbose": False,
            "page_size": 20,
            "theme": "default"
        },
        "aliases": {},
        "shortcuts": {},
        "history_size": 1000
    }

    def __init__(self):
        self.config_dir = Path.home() / ".openschichtplaner5"
        self.config_file = self.config_dir / "config.yaml"
        self.history_file = self.config_dir / "history.txt"
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f) or self.DEFAULT_CONFIG
            except Exception as e:
                console.print(f"[warning]Failed to load config: {e}[/warning]")
        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save configuration to file."""
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set configuration value."""
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_config()


class RichFormatter:
    """Formats data using Rich components."""

    @staticmethod
    def create_employee_panel(employee: Dict[str, Any]) -> Panel:
        """Create a rich panel for employee data."""
        content = f"""[bold]{employee.get('name', '')} {employee.get('firstname', '')}[/bold]

[info]ID:[/info] {employee.get('id', '')} | [info]Number:[/info] {employee.get('number', 'N/A')}
[info]Position:[/info] {employee.get('position', 'N/A')} | [info]Function:[/info] {employee.get('function', 'N/A')}
[info]Email:[/info] {employee.get('email', 'N/A')}
[info]Phone:[/info] {employee.get('phone', 'N/A')}
[info]Employment:[/info] {employee.get('empstart', 'N/A')} - {employee.get('empend', 'Present')}"""

        return Panel(content, title="Employee Profile", border_style="cyan")

    @staticmethod
    def create_data_table(records: List[Dict[str, Any]],
                          fields: Optional[List[str]] = None,
                          title: str = "Data") -> Table:
        """Create a rich table from records."""
        if not records:
            return Table(title=title, caption="No records found")

        # Determine fields
        if not fields:
            fields = [k for k in records[0].keys()
                      if not k.endswith('_related') and not k.startswith('_')]

        # Create table
        table = Table(title=title, box=box.ROUNDED)

        # Add columns
        for field in fields:
            table.add_column(field.replace('_', ' ').title(), style="cyan")

        # Add rows
        for record in records:
            row = []
            for field in fields:
                value = record.get(field, '')
                if isinstance(value, (date, datetime)):
                    value = value.strftime('%Y-%m-%d')
                row.append(str(value))
            table.add_row(*row)

        return table

    @staticmethod
    def create_tree(data: Dict[str, Any], title: str = "Data") -> Tree:
        """Create a tree visualization."""
        tree = Tree(title)

        def add_branch(parent: Tree, key: str, value: Any):
            if isinstance(value, dict):
                branch = parent.add(f"[bold cyan]{key}[/bold cyan]")
                for k, v in value.items():
                    add_branch(branch, k, v)
            elif isinstance(value, list):
                branch = parent.add(f"[bold cyan]{key}[/bold cyan] ({len(value)} items)")
                for i, item in enumerate(value[:5]):  # Limit to 5 items
                    if isinstance(item, dict):
                        item_branch = branch.add(f"[{i}]")
                        for k, v in item.items():
                            add_branch(item_branch, k, v)
                    else:
                        branch.add(str(item))
                if len(value) > 5:
                    branch.add("...")
            else:
                parent.add(f"{key}: {value}")

        for key, value in data.items():
            add_branch(tree, key, value)

        return tree


class InteractiveShell:
    """Interactive shell mode for the CLI."""

    def __init__(self, engine: QueryEngine, config: ConfigManager):
        self.engine = engine
        self.config = config
        self.report_generator = ReportGenerator(engine)
        self.exporter = DataExporter()
        self.validator = DataValidator()
        self.formatter = RichFormatter()
        self.history = []
        self.context = {}  # Store variables

        # Commands
        self.commands = {
            'help': self.cmd_help,
            'query': self.cmd_query,
            'show': self.cmd_show,
            'export': self.cmd_export,
            'report': self.cmd_report,
            'validate': self.cmd_validate,
            'config': self.cmd_config,
            'clear': self.cmd_clear,
            'exit': self.cmd_exit,
        }

    def run(self):
        """Run the interactive shell."""
        console.print(Panel.fit(
            "[bold]OpenSchichtplaner5 Interactive Shell[/bold]\n"
            "Type 'help' for commands, 'exit' to quit",
            border_style="green"
        ))

        while True:
            try:
                # Get input
                command = Prompt.ask("\n[bold green]>>>[/bold green]")

                if not command.strip():
                    continue

                # Add to history
                self.history.append(command)

                # Parse command
                parts = command.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                # Execute command
                if cmd in self.commands:
                    self.commands[cmd](args)
                else:
                    # Try to evaluate as Python expression
                    try:
                        result = eval(command, {"engine": self.engine, **self.context})
                        if result is not None:
                            console.print(result)
                    except:
                        console.print(f"[error]Unknown command: {cmd}[/error]")
                        console.print("Type 'help' for available commands")

            except KeyboardInterrupt:
                console.print("\n[warning]Use 'exit' to quit[/warning]")
            except Exception as e:
                console.print(f"[error]Error: {e}[/error]")

    def cmd_help(self, args: List[str]):
        """Show help."""
        help_text = """[bold]Available Commands:[/bold]

[info]query[/info] <table> [filters...]  - Query a table
[info]show[/info] <table|relationships>   - Show table info or relationships  
[info]export[/info] <table> <format> <file> - Export data
[info]report[/info] <type> [options...]    - Generate report
[info]validate[/info]                      - Validate data integrity
[info]config[/info] <get|set> <key> [val]  - Manage configuration
[info]clear[/info]                         - Clear screen
[info]exit[/info]                          - Exit shell

[bold]Examples:[/bold]
  query 5EMPL where name = "Schmidt"
  show 5EMPL
  export 5EMPL csv employees.csv
  report absence --employee-id 52 --year 2024"""

        console.print(Panel(help_text, title="Help", border_style="blue"))

    def cmd_query(self, args: List[str]):
        """Execute a query."""
        if not args:
            console.print("[error]Usage: query <table> [where field op value]...[/error]")
            return

        table = args[0]
        query = self.engine.query().select(table)

        # Parse where clauses
        i = 1
        while i < len(args):
            if args[i].lower() == "where" and i + 3 < len(args):
                field = args[i + 1]
                op = args[i + 2]
                value = args[i + 3]

                # Convert value type
                if value.isdigit():
                    value = int(value)
                elif value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'

                query = query.where(field, op, value)
                i += 4
            else:
                i += 1

        # Execute with progress
        with console.status("Executing query..."):
            result = query.execute()

        # Display results
        if result.records:
            table = self.formatter.create_data_table(
                result.to_dict()[:20],  # Limit display
                title=f"Query Results ({result.count} records)"
            )
            console.print(table)

            if result.count > 20:
                console.print(f"[muted]Showing first 20 of {result.count} records[/muted]")
        else:
            console.print("[warning]No records found[/warning]")

    def cmd_show(self, args: List[str]):
        """Show table info or relationships."""
        if not args:
            # Show all tables
            table = Table(title="Available Tables", box=box.ROUNDED)
            table.add_column("Table", style="cyan")
            table.add_column("Records", justify="right")
            table.add_column("Status", style="green")

            for name, data in self.engine.loaded_tables.items():
                table.add_row(name, str(len(data)), "✓ Loaded")

            console.print(table)
        elif args[0].lower() == "relationships":
            # Show relationships
            if len(args) > 1:
                # Specific table
                table_name = args[1]
                tree = Tree(f"Relationships for {table_name}")

                # Add outgoing
                outgoing = tree.add("Outgoing")
                for rel in improved_relationship_manager.resolver._schema_index.get(table_name, []):
                    outgoing.add(f"{rel.target_table} ({rel.relationship_type.value})")

                console.print(tree)
            else:
                # All relationships
                console.print("[info]Total relationships:[/info]",
                              len(improved_relationship_manager.resolver.schemas))
        else:
            # Show table info
            table_name = args[0]
            if table_name in self.engine.loaded_tables:
                records = self.engine.loaded_tables[table_name]
                console.print(f"[bold]Table: {table_name}[/bold]")
                console.print(f"Records: {len(records)}")

                if records:
                    # Show sample
                    sample_table = self.formatter.create_data_table(
                        [r.__dict__ for r in records[:5]],
                        title="Sample Records"
                    )
                    console.print(sample_table)
            else:
                console.print(f"[error]Table {table_name} not found[/error]")

    def cmd_export(self, args: List[str]):
        """Export data."""
        if len(args) < 3:
            console.print("[error]Usage: export <table> <format> <filename>[/error]")
            return

        table, format, filename = args[0], args[1], args[2]

        if table not in self.engine.loaded_tables:
            console.print(f"[error]Table {table} not found[/error]")
            return

        # Get data
        data = [r.__dict__ for r in self.engine.loaded_tables[table]]

        # Export with progress
        with console.status(f"Exporting to {filename}..."):
            try:
                self.exporter.export(data, format, Path(filename))
                console.print(f"[success]✓ Exported {len(data)} records to {filename}[/success]")
            except Exception as e:
                console.print(f"[error]Export failed: {e}[/error]")

    def cmd_report(self, args: List[str]):
        """Generate report."""
        if not args:
            console.print("[error]Available reports: absence, staffing, shifts, overtime[/error]")
            return

        report_type = args[0]

        # Parse options
        options = {}
        i = 1
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                key = args[i][2:].replace('-', '_')
                value = args[i + 1]
                if value.isdigit():
                    value = int(value)
                options[key] = value
                i += 2
            else:
                i += 1

        try:
            with console.status(f"Generating {report_type} report..."):
                if report_type == "absence":
                    report = self.report_generator.employee_absence_report(
                        options.get('employee_id'),
                        options.get('year', datetime.now().year)
                    )
                elif report_type == "staffing":
                    report = self.report_generator.group_staffing_report(
                        options.get('group_id'),
                        options.get('date')
                    )
                elif report_type == "shifts":
                    report = self.report_generator.shift_distribution_report(
                        options.get('start_date'),
                        options.get('end_date'),
                        options.get('group_id')
                    )
                elif report_type == "overtime":
                    report = self.report_generator.overtime_analysis_report(
                        options.get('employee_id'),
                        options.get('month'),
                        options.get('year')
                    )
                else:
                    console.print(f"[error]Unknown report type: {report_type}[/error]")
                    return

            # Display report
            tree = self.formatter.create_tree(report.data, title=report.title)
            console.print(tree)

        except Exception as e:
            console.print(f"[error]Report generation failed: {e}[/error]")

    def cmd_validate(self, args: List[str]):
        """Validate data."""
        with console.status("Validating data integrity..."):
            report = self.validator.validate_all_tables(self.engine.loaded_tables)

        # Show results
        if report.has_errors():
            console.print(f"[error]Found {len(report.errors)} errors[/error]")
            for error in report.errors[:10]:
                console.print(f"  - {error}")
        else:
            console.print("[success]✓ No errors found[/success]")

        if report.warnings:
            console.print(f"[warning]Found {len(report.warnings)} warnings[/warning]")

    def cmd_config(self, args: List[str]):
        """Manage configuration."""
        if not args:
            # Show all config
            syntax = Syntax(yaml.dump(self.config.config), "yaml", theme="monokai")
            console.print(Panel(syntax, title="Configuration"))
        elif args[0] == "get" and len(args) > 1:
            value = self.config.get(args[1])
            console.print(f"{args[1]}: {value}")
        elif args[0] == "set" and len(args) > 2:
            self.config.set(args[1], args[2])
            console.print(f"[success]✓ Set {args[1]} = {args[2]}[/success]")

    def cmd_clear(self, args: List[str]):
        """Clear screen."""
        console.clear()

    def cmd_exit(self, args: List[str]):
        """Exit shell."""
        if Confirm.ask("Exit shell?"):
            console.print("[info]Goodbye![/info]")
            sys.exit(0)


class EnhancedCLIv2:
    """Enhanced CLI v2 with Rich UI and interactive features."""

    def __init__(self):
        self.config = ConfigManager()
        self.parser = self._create_parser()
        self.engine: Optional[QueryEngine] = None

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="OpenSchichtplaner5 CLI v2",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument(
            "--dir",
            type=Path,
            help="Directory containing DBF files (or use config default)"
        )

        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )

        subparsers = parser.add_subparsers(dest="command", help="Commands")

        # Interactive mode
        subparsers.add_parser("shell", help="Start interactive shell")

        # Query command
        query_parser = subparsers.add_parser("query", help="Query data")
        query_parser.add_argument("table", help="Table to query")
        query_parser.add_argument("--where", nargs=3, action="append",
                                  metavar=("FIELD", "OP", "VALUE"))
        query_parser.add_argument("--limit", type=int, help="Limit results")
        query_parser.add_argument("--format", choices=["table", "json", "tree"],
                                  default="table")

        # Employee commands
        emp_parser = subparsers.add_parser("employee", help="Employee operations")
        emp_sub = emp_parser.add_subparsers(dest="subcommand")

        emp_profile = emp_sub.add_parser("profile")
        emp_profile.add_argument("--id", type=int, required=True)

        emp_search = emp_sub.add_parser("search")
        emp_search.add_argument("term")

        # Stats command
        stats_parser = subparsers.add_parser("stats", help="Show database statistics")

        # Config command
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_parser.add_argument("action", choices=["show", "set", "edit"])
        config_parser.add_argument("key", nargs="?")
        config_parser.add_argument("value", nargs="?")

        # Validate command
        subparsers.add_parser("validate", help="Validate data integrity")

        # Watch command
        watch_parser = subparsers.add_parser("watch", help="Watch query results")
        watch_parser.add_argument("query", help="Query to watch")
        watch_parser.add_argument("--interval", type=int, default=5,
                                  help="Update interval in seconds")

        return parser

    def run(self, args: Optional[List[str]] = None):
        """Run the CLI."""
        parsed_args = self.parser.parse_args(args)

        # Get DBF directory
        dbf_dir = parsed_args.dir or self.config.get("defaults.dbf_dir")
        if not dbf_dir:
            console.print("[error]No DBF directory specified. Use --dir or set in config[/error]")
            return 1

        dbf_dir = Path(dbf_dir)
        if not dbf_dir.exists():
            console.print(f"[error]DBF directory not found: {dbf_dir}[/error]")
            return 1

        # Initialize engine with progress
        try:
            with console.status("Loading database...") as status:
                self.engine = QueryEngine(dbf_dir, verbose=parsed_args.verbose)

            console.print(f"[success]✓ Loaded {len(self.engine.loaded_tables)} tables[/success]")
        except Exception as e:
            console.print(f"[error]Failed to load database: {e}[/error]")
            return 1

        # Dispatch command
        if not parsed_args.command:
            self.parser.print_help()
        elif parsed_args.command == "shell":
            shell = InteractiveShell(self.engine, self.config)
            shell.run()
        elif parsed_args.command == "query":
            self._handle_query(parsed_args)
        elif parsed_args.command == "employee":
            self._handle_employee(parsed_args)
        elif parsed_args.command == "stats":
            self._handle_stats()
        elif parsed_args.command == "config":
            self._handle_config(parsed_args)
        elif parsed_args.command == "validate":
            self._handle_validate()
        elif parsed_args.command == "watch":
            self._handle_watch(parsed_args)

    def _handle_query(self, args):
        """Handle query command."""
        query = self.engine.query().select(args.table)

        if args.where:
            for field, op, value in args.where:
                # Type conversion
                if value.isdigit():
                    value = int(value)
                query = query.where(field, op, value)

        if args.limit:
            query = query.limit(args.limit)

        result = query.execute()

        if args.format == "json":
            console.print_json(data=result.to_dict())
        elif args.format == "tree":
            tree = RichFormatter.create_tree(
                {"records": result.to_dict()[:10]},
                title=f"Query Results ({result.count} total)"
            )
            console.print(tree)
        else:
            table = RichFormatter.create_data_table(
                result.to_dict()[:20],
                title=f"Query Results ({result.count} records)"
            )
            console.print(table)

    def _handle_employee(self, args):
        """Handle employee commands."""
        if args.subcommand == "profile":
            try:
                profile = self.engine.get_employee_full_profile(args.id)
                panel = RichFormatter.create_employee_panel(profile)
                console.print(panel)

                # Show related data
                for key, value in profile.items():
                    if key.endswith('_related') and value:
                        console.print(f"\n[bold]{key}:[/bold]")
                        if isinstance(value, list):
                            for item in value[:5]:
                                console.print(f"  • {item}")
                        else:
                            console.print(f"  {value}")

            except DataNotFoundError as e:
                console.print(f"[error]{e}[/error]")

        elif args.subcommand == "search":
            results = self.engine.search_employees(args.term)
            if results:
                table = RichFormatter.create_data_table(
                    results,
                    fields=["id", "name", "firstname", "position"],
                    title=f"Search Results ({len(results)} found)"
                )
                console.print(table)
            else:
                console.print(f"[warning]No employees found matching '{args.term}'[/warning]")

    def _handle_stats(self):
        """Show database statistics."""
        stats = {
            "Tables": len(self.engine.loaded_tables),
            "Total Records": sum(len(t) for t in self.engine.loaded_tables.values()),
        }

        # Table breakdown
        table = Table(title="Database Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")

        for key, value in stats.items():
            table.add_row(key, str(value))

        table.add_section()

        # Per-table stats
        for name, records in self.engine.loaded_tables.items():
            table.add_row(f"  {name}", str(len(records)))

        console.print(table)

    def _handle_config(self, args):
        """Handle configuration commands."""
        if args.action == "show":
            if args.key:
                value = self.config.get(args.key)
                console.print(f"{args.key}: {value}")
            else:
                syntax = Syntax(yaml.dump(self.config.config), "yaml", theme="monokai")
                console.print(Panel(syntax, title="Configuration"))
        elif args.action == "set" and args.key and args.value:
            self.config.set(args.key, args.value)
            console.print(f"[success]✓ Set {args.key} = {args.value}[/success]")
        elif args.action == "edit":
            # Open in editor
            import subprocess
            editor = os.environ.get('EDITOR', 'nano')
            subprocess.call([editor, str(self.config.config_file)])
            self.config.config = self.config.load_config()
            console.print("[success]✓ Configuration reloaded[/success]")

    def _handle_validate(self):
        """Handle data validation."""
        validator = DataValidator()

        with console.status("Validating data integrity..."):
            report = validator.validate_all_tables(self.engine.loaded_tables)

        # Create summary panel
        summary = f"""[bold]Validation Summary[/bold]

Errors: [error]{len(report.errors)}[/error]
Warnings: [warning]{len(report.warnings)}[/warning]

[bold]Statistics:[/bold]"""

        for key, count in sorted(report.statistics.items()):
            summary += f"\n  {key}: {count}"

        console.print(Panel(summary, border_style="blue"))

        # Show sample errors
        if report.errors:
            console.print("\n[bold]Sample Errors:[/bold]")
            for error in report.errors[:5]:
                console.print(f"  • {error}")

    def _handle_watch(self, args):
        """Watch query results with auto-refresh."""
        # Parse the query
        parts = args.query.split()
        if len(parts) < 2:
            console.print("[error]Invalid query format[/error]")
            return

        table_name = parts[1]

        def get_data():
            """Execute query and return formatted table."""
            query = self.engine.query().select(table_name).limit(10)
            result = query.execute()

            if result.records:
                return RichFormatter.create_data_table(
                    result.to_dict(),
                    title=f"Watching: {args.query} (Updated: {datetime.now().strftime('%H:%M:%S')})"
                )
            else:
                return Panel("No data", title="Watch")

        # Live update
        try:
            with Live(get_data(), refresh_per_second=1) as live:
                while True:
                    time.sleep(args.interval)
                    live.update(get_data())
        except KeyboardInterrupt:
            console.print("\n[info]Watch stopped[/info]")


def main():
    """Main entry point."""
    cli = EnhancedCLIv2()
    try:
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[warning]Operation cancelled[/warning]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()