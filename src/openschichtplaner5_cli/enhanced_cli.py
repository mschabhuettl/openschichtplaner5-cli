# openschichtplaner5-cli/src/openschichtplaner5_cli/enhanced_cli.py
"""
Enhanced CLI with advanced query capabilities for Schichtplaner5 data.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import sys

from libopenschichtplaner5.query_engine import QueryEngine, FilterOperator
from libopenschichtplaner5.relationships import relationship_manager
from libopenschichtplaner5.registry import TABLE_NAMES
from libopenschichtplaner5.reports import ReportGenerator
from libopenschichtplaner5.export import DataExporter, ReportExporter, ExportFormat
from libopenschichtplaner5.utils.validation import DataValidator


class CLIFormatter:
    """Formats query results for console output."""
    
    @staticmethod
    def format_employee(employee: Dict[str, Any]) -> str:
        """Format employee data for display."""
        lines = [
            f"\n{'='*60}",
            f"Employee: {employee.get('name', '')} {employee.get('firstname', '')}",
            f"ID: {employee.get('id', '')} | Number: {employee.get('number', '')}",
            f"Position: {employee.get('position', '')} | Function: {employee.get('function', '')}",
            f"Email: {employee.get('email', '')} | Phone: {employee.get('phone', '')}",
        ]
        
        if employee.get('empstart'):
            lines.append(f"Employment Start: {employee.get('empstart')}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_schedule_entry(entry: Dict[str, Any]) -> str:
        """Format a schedule entry."""
        shift_info = entry.get('5SHIFT_related', {})
        workplace_info = entry.get('5WOPL_related', {})
        
        return (f"{entry.get('date', 'N/A')} | "
                f"{shift_info.get('name', 'Unknown Shift')} "
                f"({shift_info.get('shortname', '')}) | "
                f"Location: {workplace_info.get('name', 'Unknown')}")
    
    @staticmethod
    def format_table(records: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> str:
        """Format records as a table."""
        if not records:
            return "No records found."
        
        # Determine fields to display
        if not fields:
            fields = [k for k in records[0].keys() if not k.endswith('_related')]
        
        # Calculate column widths
        widths = {}
        for field in fields:
            widths[field] = max(
                len(field),
                max(len(str(r.get(field, ''))) for r in records)
            )
        
        # Create header
        header = " | ".join(f"{field:{widths[field]}}" for field in fields)
        separator = "-+-".join("-" * widths[field] for field in fields)
        
        # Create rows
        rows = []
        for record in records:
            row = " | ".join(f"{str(record.get(field, '')):{widths[field]}}" for field in fields)
            rows.append(row)
        
        return f"\n{header}\n{separator}\n" + "\n".join(rows)


class EnhancedCLI:
    """Enhanced command-line interface for Schichtplaner5."""
    
    def __init__(self):
        self.parser = self._create_parser()
        self.engine: Optional[QueryEngine] = None
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description="OpenSchichtplaner5 Enhanced CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_examples()
        )
        
        parser.add_argument(
            "--dir", 
            required=True, 
            type=Path,
            help="Directory containing DBF files"
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Employee commands
        emp_parser = subparsers.add_parser("employee", help="Employee queries")
        emp_sub = emp_parser.add_subparsers(dest="subcommand")
        
        # Employee profile
        emp_profile = emp_sub.add_parser("profile", help="Get employee profile")
        emp_profile.add_argument("--id", type=int, required=True, help="Employee ID")
        emp_profile.add_argument("--full", action="store_true", help="Include all related data")
        
        # Employee search
        emp_search = emp_sub.add_parser("search", help="Search employees")
        emp_search.add_argument("term", help="Search term")
        
        # Employee schedule
        emp_schedule = emp_sub.add_parser("schedule", help="Get employee schedule")
        emp_schedule.add_argument("--id", type=int, required=True, help="Employee ID")
        emp_schedule.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
        emp_schedule.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
        
        # Group commands
        group_parser = subparsers.add_parser("group", help="Group queries")
        group_sub = group_parser.add_subparsers(dest="subcommand")
        
        # Group members
        group_members = group_sub.add_parser("members", help="List group members")
        group_members.add_argument("--id", type=int, required=True, help="Group ID")
        
        # List groups
        group_list = group_sub.add_parser("list", help="List all groups")
        
        # Query builder
        query_parser = subparsers.add_parser("query", help="Custom query builder")
        query_parser.add_argument("table", choices=TABLE_NAMES, help="Table to query")
        query_parser.add_argument("--where", nargs=3, action="append", 
                                metavar=("FIELD", "OP", "VALUE"),
                                help="Filter condition (can be used multiple times)")
        query_parser.add_argument("--join", action="append", choices=TABLE_NAMES,
                                help="Join with table (can be used multiple times)")
        query_parser.add_argument("--limit", type=int, help="Limit results")
        query_parser.add_argument("--order", nargs=2, metavar=("FIELD", "ASC/DESC"),
                                help="Order by field")
        query_parser.add_argument("--format", choices=["table", "json", "csv"], 
                                default="table", help="Output format")
        
        # Relationships info
        rel_parser = subparsers.add_parser("relationships", help="Show table relationships")
        rel_parser.add_argument("--table", help="Show relationships for specific table")
        rel_parser.add_argument("--graph", action="store_true", 
                              help="Show full relationship graph")
        
        # Report commands
        report_parser = subparsers.add_parser("report", help="Generate reports")
        report_sub = report_parser.add_subparsers(dest="subcommand")
        
        # Absence report
        absence_report = report_sub.add_parser("absence", help="Employee absence report")
        absence_report.add_argument("--employee-id", type=int, required=True, help="Employee ID")
        absence_report.add_argument("--year", type=int, help="Year (default: current)")
        absence_report.add_argument("--format", choices=["json", "html", "markdown"], 
                                  default="json", help="Output format")
        absence_report.add_argument("--output", type=Path, help="Output file")
        
        # Staffing report
        staffing_report = report_sub.add_parser("staffing", help="Group staffing report")
        staffing_report.add_argument("--group-id", type=int, required=True, help="Group ID")
        staffing_report.add_argument("--date", type=str, help="Date (YYYY-MM-DD, default: today)")
        staffing_report.add_argument("--format", choices=["json", "html", "markdown"], 
                                   default="json", help="Output format")
        
        # Shift distribution report
        shift_report = report_sub.add_parser("shifts", help="Shift distribution report")
        shift_report.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
        shift_report.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
        shift_report.add_argument("--group-id", type=int, help="Filter by group ID")
        shift_report.add_argument("--format", choices=["json", "html", "markdown"], 
                                default="json", help="Output format")
        
        # Overtime report
        overtime_report = report_sub.add_parser("overtime", help="Overtime analysis report")
        overtime_report.add_argument("--month", type=int, help="Month (1-12)")
        overtime_report.add_argument("--year", type=int, help="Year")
        overtime_report.add_argument("--employee-id", type=int, help="Filter by employee ID")
        overtime_report.add_argument("--format", choices=["json", "html", "markdown"], 
                                   default="json", help="Output format")
        
        # Validate command
        validate_parser = subparsers.add_parser("validate", help="Validate data integrity")
        validate_parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
        
        return parser
    
    def _get_examples(self) -> str:
        """Get usage examples."""
        return """
Examples:
  # Get employee profile
  python -m openschichtplaner5_cli --dir /path/to/dbf employee profile --id 52 --full
  
  # Search employees
  python -m openschichtplaner5_cli --dir /path/to/dbf employee search "Schmidt"
  
  # Get employee schedule
  python -m openschichtplaner5_cli --dir /path/to/dbf employee schedule --id 52 \\
    --start 2024-01-01 --end 2024-01-31
  
  # List group members
  python -m openschichtplaner5_cli --dir /path/to/dbf group members --id 5
  
  # Custom query with joins
  python -m openschichtplaner5_cli --dir /path/to/dbf query 5EMPL \\
    --where position = "Developer" --join 5NOTE --join 5GRASG --limit 10
  
  # Show relationships
  python -m openschichtplaner5_cli --dir /path/to/dbf relationships --table 5EMPL
"""
    
    def run(self, args: Optional[List[str]] = None):
        """Run the CLI."""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return
        
        # Initialize query engine and other components
        try:
            self.engine = QueryEngine(parsed_args.dir)
            self.report_generator = ReportGenerator(self.engine)
            self.data_exporter = DataExporter()
            self.report_exporter = ReportExporter()
            self.validator = DataValidator()
        except Exception as e:
            print(f"Error initializing components: {e}")
            return 1
        
        # Dispatch to appropriate handler
        if parsed_args.command == "employee":
            self._handle_employee_command(parsed_args)
        elif parsed_args.command == "group":
            self._handle_group_command(parsed_args)
        elif parsed_args.command == "query":
            self._handle_query_command(parsed_args)
        elif parsed_args.command == "relationships":
            self._handle_relationships_command(parsed_args)
        elif parsed_args.command == "info":
            self._handle_info_command(parsed_args)
        elif parsed_args.command == "report":
            self._handle_report_command(parsed_args)
        elif parsed_args.command == "validate":
            self._handle_validate_command(parsed_args)
        elif parsed_args.command == "export":
            self._handle_export_command(parsed_args)
        else:
            self.parser.print_help()
    
    def _handle_employee_command(self, args):
        """Handle employee-related commands."""
        if args.subcommand == "profile":
            if args.full:
                profile = self.engine.get_employee_full_profile(args.id)
                if profile:
                    print(CLIFormatter.format_employee(profile))
                    
                    # Show related data
                    for table, data in profile.items():
                        if table.endswith("_related"):
                            print(f"\n{table}:")
                            if isinstance(data, list):
                                for item in data[:5]:  # Limit to 5 items
                                    print(f"  - {item}")
                            else:
                                print(f"  {data}")
                else:
                    print(f"Employee with ID {args.id} not found.")
            else:
                result = (self.engine.query()
                         .select("5EMPL")
                         .where("id", "=", args.id)
                         .execute())
                if result.records:
                    print(CLIFormatter.format_employee(result.to_dict()[0]))
                else:
                    print(f"Employee with ID {args.id} not found.")
        
        elif args.subcommand == "search":
            results = self.engine.search_employees(args.term)
            if results:
                print(f"\nFound {len(results)} employees:")
                for emp in results:
                    print(f"- [{emp['id']}] {emp['name']} {emp['firstname']} "
                          f"({emp.get('position', 'N/A')})")
            else:
                print(f"No employees found matching '{args.term}'")
        
        elif args.subcommand == "schedule":
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else None
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None
            
            schedule = self.engine.get_employee_schedule(args.id, start_date, end_date)
            if schedule:
                print(f"\nSchedule for employee {args.id}:")
                for entry in schedule:
                    print(CLIFormatter.format_schedule_entry(entry))
            else:
                print(f"No schedule found for employee {args.id}")
    
    def _handle_group_command(self, args):
        """Handle group-related commands."""
        if args.subcommand == "members":
            members = self.engine.get_group_members(args.id)
            if members:
                print(f"\nGroup {args.id} has {len(members)} members:")
                print(CLIFormatter.format_table(members, ["id", "name", "firstname", "position"]))
            else:
                print(f"No members found for group {args.id}")
        
        elif args.subcommand == "list":
            result = self.engine.query().select("5GROUP").order_by("name").execute()
            if result.records:
                print("\nAvailable groups:")
                print(CLIFormatter.format_table(result.to_dict(), ["id", "name", "shortname"]))
            else:
                print("No groups found")
    
    def _handle_query_command(self, args):
        """Handle custom query command."""
        query = self.engine.query().select(args.table)
        
        # Apply filters
        if args.where:
            for field, op, value in args.where:
                # Try to convert value to appropriate type
                try:
                    if value.isdigit():
                        value = int(value)
                    elif value.replace(".", "").isdigit():
                        value = float(value)
                    elif value.lower() in ["true", "false"]:
                        value = value.lower() == "true"
                except:
                    pass  # Keep as string
                
                query = query.where(field, op, value)
        
        # Apply joins
        if args.join:
            for table in args.join:
                query = query.join(table)
        
        # Apply ordering
        if args.order:
            field, direction = args.order
            query = query.order_by(field, direction.upper() == "ASC")
        
        # Apply limit
        if args.limit:
            query = query.limit(args.limit)
        
        # Execute query
        result = query.execute()
        
        print(f"\nQuery returned {result.count} records (execution time: {result.execution_time:.3f}s)")
        
        # Format output
        if args.format == "json":
            print(json.dumps(result.to_dict(), indent=2, default=str))
        elif args.format == "csv":
            # Simple CSV output
            if result.records:
                data = result.to_dict()
                fields = [k for k in data[0].keys() if not k.endswith("_related")]
                print(",".join(fields))
                for record in data:
                    print(",".join(str(record.get(f, "")) for f in fields))
        else:  # table format
            print(CLIFormatter.format_table(result.to_dict()))
    
    def _handle_relationships_command(self, args):
        """Handle relationships command."""
        if args.graph:
            graph = relationship_manager.get_relationship_graph()
            print("\nRelationship Graph:")
            print(json.dumps(graph, indent=2))
        elif args.table:
            print(f"\nRelationships for {args.table}:")
            
            # Outgoing relationships
            outgoing = relationship_manager.get_relationships_from(args.table)
            if outgoing:
                print("\n  Outgoing (this table references):")
                for rel in outgoing:
                    print(f"    - {rel.source_field} -> {rel.target_table}.{rel.target_field} "
                          f"({rel.relationship_type.value})")
                    if rel.description:
                        print(f"      {rel.description}")
            
            # Incoming relationships
            incoming = relationship_manager.get_relationships_to(args.table)
            if incoming:
                print("\n  Incoming (referenced by):")
                for rel in incoming:
                    print(f"    - {rel.source_table}.{rel.source_field} -> {rel.target_field} "
                          f"({rel.relationship_type.value})")
                    if rel.description:
                        print(f"      {rel.description}")
        else:
            # Show summary
            all_tables = set()
            for rel in relationship_manager.relationships:
                all_tables.add(rel.source_table)
                all_tables.add(rel.target_table)
            
            print(f"\nTotal relationships defined: {len(relationship_manager.relationships)}")
            print(f"Tables with relationships: {len(all_tables)}")
            print("\nUse --table TABLE_NAME to see relationships for a specific table")
            print("Use --graph to see the full relationship graph")
    
    def _handle_info_command(self, args):
        """Handle table info command."""
        if args.table not in self.engine.loaded_tables:
            print(f"Table {args.table} not loaded")
            return
        
        records = self.engine.loaded_tables[args.table]
        print(f"\nTable: {args.table}")
        print(f"Records: {len(records)}")
        
        if records:
            # Show field information
            sample = records[0]
            print("\nFields:")
            for attr in dir(sample):
                if not attr.startswith("_") and not callable(getattr(sample, attr)):
                    value = getattr(sample, attr)
                    print(f"  - {attr}: {type(value).__name__}")
            
            # Show sample records
            if args.sample > 0:
                print(f"\nSample records (first {args.sample}):")
                sample_data = [self._record_to_dict(r) for r in records[:args.sample]]
                print(CLIFormatter.format_table(sample_data))
    
    def _handle_report_command(self, args):
        """Handle report generation commands."""
        if args.subcommand == "absence":
            year = args.year or datetime.now().year
            try:
                report = self.report_generator.employee_absence_report(args.employee_id, year)
                
                # Format output
                if args.format == "json":
                    output = json.dumps(report.to_dict(), indent=2, default=str)
                elif args.format == "html":
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.HTML)
                else:  # markdown
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.MARKDOWN)
                
                if args.output:
                    args.output.write_text(output, encoding='utf-8')
                    print(f"Report saved to: {args.output}")
                else:
                    print(output)
                    
            except Exception as e:
                print(f"Error generating absence report: {e}")
        
        elif args.subcommand == "staffing":
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
            try:
                report = self.report_generator.group_staffing_report(args.group_id, target_date)
                
                # Format output
                if args.format == "json":
                    output = json.dumps(report.to_dict(), indent=2, default=str)
                elif args.format == "html":
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.HTML)
                else:  # markdown
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.MARKDOWN)
                
                print(output)
                
            except Exception as e:
                print(f"Error generating staffing report: {e}")
        
        elif args.subcommand == "shifts":
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
            
            try:
                report = self.report_generator.shift_distribution_report(
                    start_date, end_date, args.group_id
                )
                
                # Format output
                if args.format == "json":
                    output = json.dumps(report.to_dict(), indent=2, default=str)
                elif args.format == "html":
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.HTML)
                else:  # markdown
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.MARKDOWN)
                
                print(output)
                
            except Exception as e:
                print(f"Error generating shift distribution report: {e}")
        
        elif args.subcommand == "overtime":
            try:
                report = self.report_generator.overtime_analysis_report(
                    args.employee_id, args.month, args.year
                )
                
                # Format output
                if args.format == "json":
                    output = json.dumps(report.to_dict(), indent=2, default=str)
                elif args.format == "html":
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.HTML)
                else:  # markdown
                    output = self.report_exporter.export_summary_report(report.to_dict(), ExportFormat.MARKDOWN)
                
                print(output)
                
            except Exception as e:
                print(f"Error generating overtime report: {e}")
    
    def _handle_validate_command(self, args):
        """Handle data validation command."""
        print("Running data validation...")
        validation_report = self.validator.validate_all_tables(self.engine.loaded_tables)
        
        print(f"\n{validation_report.summary()}")
        
        if validation_report.errors:
            print(f"\nShowing first 10 errors:")
            for error in validation_report.errors[:10]:
                print(f"  - {error}")
        
        if validation_report.warnings:
            print(f"\nShowing first 10 warnings:")
            for warning in validation_report.warnings[:10]:
                print(f"  - {warning}")
        
        if args.fix:
            print("\nNote: Automatic fixing is not yet implemented.")
    
    def _handle_export_command(self, args):
        """Handle data export command."""
        # Build query
        query = self.engine.query().select(args.table)
        
        # Apply filters
        if args.where:
            for field, op, value in args.where:
                # Try to convert value to appropriate type
                try:
                    if value.isdigit():
                        value = int(value)
                    elif value.replace(".", "").isdigit():
                        value = float(value)
                except:
                    pass  # Keep as string
                
                query = query.where(field, op, value)
        
        # Apply limit
        if args.limit:
            query = query.limit(args.limit)
        
        # Execute query
        result = query.execute()
        
        if not result.records:
            print("No data to export")
            return
        
        # Export data
        try:
            data = result.to_dict()
            self.data_exporter.export(data, args.format, args.output)
            print(f"Successfully exported {len(data)} records to: {args.output}")
        except Exception as e:
            print(f"Error exporting data: {e}")
    
    def _record_to_dict(self, record: Any) -> Dict[str, Any]:
        """Convert a record to dictionary."""
        result = {}
        for attr in dir(record):
            if not attr.startswith("_") and not callable(getattr(record, attr)):
                result[attr] = getattr(record, attr)
        return result


def main():
    """Main entry point for the enhanced CLI."""
    cli = EnhancedCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
