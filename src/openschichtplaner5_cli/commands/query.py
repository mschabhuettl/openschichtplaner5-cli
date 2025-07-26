# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/query.py
"""
Advanced query command with filtering support.
"""

from argparse import ArgumentParser, Namespace
from typing import List

from .base import SimpleCommand, CLIContext
from ..output.formatters import get_formatter, FormatConfig
from ..utils.parsing import FilterParser, ArgumentValidator


class QueryCommand(SimpleCommand):
    """Execute advanced queries with filtering and joins."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--table',
            required=True,
            help='Table to query (e.g., 5EMPL, 5SHIFT)'
        )
        
        parser.add_argument(
            '--filter',
            action='append',
            help='Filter condition (e.g., "name=Schmidt", "age>=25"). Can be used multiple times.'
        )
        
        parser.add_argument(
            '--join',
            action='append',
            help='Join with table. Can be used multiple times.'
        )
        
        parser.add_argument(
            '--order',
            help='Order by field (e.g., "name", "id desc")'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of results'
        )
        
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'yaml', 'csv'],
            help='Output format (default: from config)'
        )
        
        parser.add_argument(
            '--fields',
            help='Comma-separated list of fields to display'
        )
        
        parser.add_argument(
            '--explain',
            action='store_true',
            help='Show query execution plan instead of results'
        )
    
    def validate_args(self, args: Namespace) -> List[str]:
        validator = ArgumentValidator()
        errors = []
        
        # Validate limit
        if args.limit is not None:
            if not validator.validate_limit(args.limit):
                errors.extend(validator.errors)
        
        # Validate filters
        if args.filter:
            filter_parser = FilterParser()
            for filter_expr in args.filter:
                try:
                    filter_parser.parse_filter(filter_expr)
                except Exception as e:
                    errors.append(f"Invalid filter '{filter_expr}': {e}")
        
        # Validate order clause
        if args.order:
            order_parts = args.order.split()
            if len(order_parts) > 2:
                errors.append("Order clause format: 'field' or 'field desc'")
            elif len(order_parts) == 2 and order_parts[1].lower() not in ['asc', 'desc']:
                errors.append("Order direction must be 'asc' or 'desc'")
        
        return errors
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        try:
            context.ensure_components()
            
            # Check if table exists
            from libopenschichtplaner5.registry import TABLE_NAMES
            if args.table not in TABLE_NAMES:
                self._print_error(f"Unknown table: {args.table}")
                self._print_info(f"Available tables: {', '.join(TABLE_NAMES)}")
                return 1
            
            # Build query
            query = context.query_engine.query().select(args.table)
            
            # Apply filters
            if args.filter:
                filter_parser = FilterParser()
                for filter_expr in args.filter:
                    condition = filter_parser.parse_filter(filter_expr)
                    query = query.where(condition.field, condition.operator, condition.value)
            
            # Apply joins
            if args.join:
                for join_table in args.join:
                    if join_table not in TABLE_NAMES:
                        self._print_warning(f"Unknown join table: {join_table}")
                        continue
                    query = query.join(join_table)
            
            # Apply ordering
            if args.order:
                order_parts = args.order.split()
                field = order_parts[0]
                ascending = True
                if len(order_parts) > 1:
                    ascending = order_parts[1].lower() != 'desc'
                query = query.order_by(field, ascending)
            
            # Apply limit
            if args.limit:
                query = query.limit(args.limit)
            
            # Show explain plan if requested
            if args.explain:
                # This would need to be implemented in the query engine
                self._print_info("Query plan explanation not yet implemented")
                return 0
            
            # Execute query
            from ..utils.progress import progress_context
            with progress_context("Executing query"):
                result = query.execute()
            
            if not result.records:
                self._print_info("No records found")
                return 0
            
            # Prepare output format
            output_format = args.format or context.config.default_output_format
            
            # Convert to dict for formatting
            data = result.to_dict()
            
            # Filter fields if specified
            if args.fields:
                specified_fields = [f.strip() for f in args.fields.split(',')]
                data = [{k: record.get(k) for k in specified_fields} for record in data]
            
            # Format and output
            format_config = FormatConfig(
                color_output=context.config.color_output,
                date_format=context.config.date_format,
                time_format=context.config.time_format
            )
            
            formatter = get_formatter(output_format, format_config)
            
            if output_format in ['json', 'yaml']:
                output = formatter.format(data)
            else:
                # Table or CSV format
                fields = None
                if args.fields:
                    fields = [f.strip() for f in args.fields.split(',')]
                
                if hasattr(formatter, 'format'):
                    if output_format == 'table':
                        output = formatter.format(data, fields, 
                                                f"Query results ({len(data)} records)")
                    else:
                        output = formatter.format(data, fields)
                else:
                    output = str(data)
            
            print(output)
            
            # Show execution stats
            if context.config.verbose_logging:
                print(f"\n📊 Query executed in {result.execution_time:.3f}s, "
                      f"returned {result.count} records")
            
            return 0
            
        except Exception as e:
            self._print_error(f"Query failed: {e}")
            if context.config.debug_mode:
                import traceback
                traceback.print_exc()
            return 1