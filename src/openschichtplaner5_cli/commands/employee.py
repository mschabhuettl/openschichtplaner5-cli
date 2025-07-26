# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/employee.py
"""
Employee-related commands for OpenSchichtplaner5 CLI.
"""

from argparse import ArgumentParser, Namespace
from datetime import datetime, date
from typing import Optional

from .base import SubcommandBase, SimpleCommand, CLIContext
from ..output.formatters import EmployeeFormatter, TableFormatter
from ..utils.parsing import ArgumentValidator


class EmployeeProfileCommand(SimpleCommand):
    """Get detailed employee profile information."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'employee_id',
            type=int,
            help='Employee ID to retrieve profile for'
        )
        parser.add_argument(
            '--full', 
            action='store_true',
            help='Include all related data (shifts, absences, etc.)'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'yaml'],
            default=None,
            help='Output format (default: from config)'
        )
    
    def validate_args(self, args: Namespace) -> list:
        validator = ArgumentValidator()
        validator.validate_employee_id(args.employee_id)
        return validator.errors
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        try:
            context.ensure_components()
            
            # Use configured format if not specified
            output_format = args.format or context.config.default_output_format
            
            if args.full:
                # Get full profile with relationships
                profile = context.query_engine.get_employee_full_profile(args.employee_id)
                if not profile:
                    self._print_error(f"Employee with ID {args.employee_id} not found")
                    return 1
                
                if output_format == 'json':
                    import json
                    print(json.dumps(profile, indent=2, default=str))
                elif output_format == 'yaml':
                    import yaml
                    print(yaml.dump(profile, default_flow_style=False))
                else:
                    # Table format
                    formatter = EmployeeFormatter()
                    print(formatter.format_full_profile(profile))
            else:
                # Get basic employee info
                result = (context.query_engine.query()
                         .select("5EMPL")
                         .where("id", "==", args.employee_id)
                         .execute())
                
                if not result.records:
                    self._print_error(f"Employee with ID {args.employee_id} not found")
                    return 1
                
                employee = result.to_dict()[0]
                
                if output_format == 'json':
                    import json
                    print(json.dumps(employee, indent=2, default=str))
                elif output_format == 'yaml':
                    import yaml
                    print(yaml.dump(employee, default_flow_style=False))
                else:
                    formatter = EmployeeFormatter()
                    print(formatter.format_basic_info(employee))
            
            return 0
            
        except Exception as e:
            self._print_error(f"Failed to retrieve employee profile: {e}")
            return 1


class EmployeeSearchCommand(SimpleCommand):
    """Search for employees by name or other criteria."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'search_term',
            help='Search term (name, position, etc.)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of results (default: 20)'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'list'],
            default='table',
            help='Output format (default: table)'
        )
    
    def validate_args(self, args: Namespace) -> list:
        validator = ArgumentValidator()
        if args.limit:
            validator.validate_limit(args.limit)
        return validator.errors
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        try:
            context.ensure_components()
            
            # Perform search
            results = context.query_engine.search_employees(args.search_term)
            
            if not results:
                self._print_info(f"No employees found matching '{args.search_term}'")
                return 0
            
            # Apply limit
            if args.limit and len(results) > args.limit:
                results = results[:args.limit]
                self._print_info(f"Showing first {args.limit} results")
            
            # Format output
            if args.format == 'json':
                import json
                print(json.dumps(results, indent=2, default=str))
            elif args.format == 'list':
                print(f"\nFound {len(results)} employees:")
                for emp in results:
                    print(f"  [{emp['id']}] {emp['name']} {emp['firstname']} "
                          f"({emp.get('position', 'N/A')})")
            else:
                # Table format
                formatter = TableFormatter()
                fields = ['id', 'name', 'firstname', 'position', 'email']
                print(f"\nFound {len(results)} employees:")
                print(formatter.format(results, fields))
            
            return 0
            
        except Exception as e:
            self._print_error(f"Search failed: {e}")
            return 1


class EmployeeScheduleCommand(SimpleCommand):
    """Get employee schedule for a date range."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'employee_id',
            type=int,
            help='Employee ID'
        )
        parser.add_argument(
            '--start',
            type=str,
            help='Start date (YYYY-MM-DD, default: current month start)'
        )
        parser.add_argument(
            '--end',
            type=str,
            help='End date (YYYY-MM-DD, default: current month end)'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'calendar'],
            default='table',
            help='Output format (default: table)'
        )
    
    def validate_args(self, args: Namespace) -> list:
        validator = ArgumentValidator()
        validator.validate_employee_id(args.employee_id)
        
        if args.start:
            validator.validate_date_string(args.start, "start date")
        if args.end:
            validator.validate_date_string(args.end, "end date")
        
        return validator.errors
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        try:
            context.ensure_components()
            
            # Parse dates
            if args.start:
                start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            else:
                # Default to start of current month
                today = date.today()
                start_date = today.replace(day=1)
            
            if args.end:
                end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
            else:
                # Default to end of current month
                if args.start:
                    # End of month for start date
                    import calendar
                    year, month = start_date.year, start_date.month
                    last_day = calendar.monthrange(year, month)[1]
                    end_date = start_date.replace(day=last_day)
                else:
                    # End of current month
                    today = date.today()
                    import calendar
                    last_day = calendar.monthrange(today.year, today.month)[1]
                    end_date = today.replace(day=last_day)
            
            # Get schedule
            schedule = context.query_engine.get_employee_schedule(
                args.employee_id, start_date, end_date
            )
            
            if not schedule:
                self._print_info(f"No schedule found for employee {args.employee_id} "
                               f"between {start_date} and {end_date}")
                return 0
            
            # Format output
            if args.format == 'json':
                import json
                print(json.dumps(schedule, indent=2, default=str))
            elif args.format == 'calendar':
                formatter = EmployeeFormatter()
                print(formatter.format_schedule_calendar(schedule, start_date, end_date))
            else:
                # Table format
                formatter = EmployeeFormatter()
                print(f"\nSchedule for employee {args.employee_id} ({start_date} to {end_date}):")
                print(formatter.format_schedule_table(schedule))
            
            return 0
            
        except Exception as e:
            self._print_error(f"Failed to retrieve schedule: {e}")
            return 1


class EmployeeCommand(SubcommandBase):
    """Employee management and queries."""
    
    def __init__(self):
        super().__init__()
        self.add_subcommand('profile', EmployeeProfileCommand())
        self.add_subcommand('search', EmployeeSearchCommand())
        self.add_subcommand('schedule', EmployeeScheduleCommand())