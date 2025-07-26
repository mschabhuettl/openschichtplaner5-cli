# openschichtplaner5-cli/src/openschichtplaner5_cli/core/cli_app.py
"""
Main CLI application for OpenSchichtplaner5.
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Dict, List, Optional

from .config import CLIConfig, load_config
from .exceptions import CLIError, ConfigError, LibraryNotFoundError
from ..commands import (
    BaseCommand, CLIContext, EmployeeCommand, GroupCommand, 
    QueryCommand, ReportCommand, ValidateCommand, ConfigCommand, InfoCommand
)
from ..utils.discovery import setup_library
from ..utils.parsing import ArgumentValidator
from ..utils.progress import progress_context


class CLIApplication:
    """Main CLI application coordinator."""
    
    def __init__(self):
        self.config: Optional[CLIConfig] = None
        self.context: Optional[CLIContext] = None
        self.commands: Dict[str, BaseCommand] = {}
        self._setup_commands()
    
    def _setup_commands(self):
        """Initialize all available commands."""
        self.commands = {
            'employee': EmployeeCommand(),
            'group': GroupCommand(),
            'query': QueryCommand(), 
            'report': ReportCommand(),
            'validate': ValidateCommand(),
            'config': ConfigCommand(),
            'info': InfoCommand()
        }
    
    def create_parser(self) -> ArgumentParser:
        """Create the main argument parser."""
        from argparse import RawDescriptionHelpFormatter
        
        parser = ArgumentParser(
            prog='openschichtplaner5-cli',
            description='Command-line interface for OpenSchichtplaner5 data',
            formatter_class=RawDescriptionHelpFormatter,
            epilog=self._get_examples_text()
        )
        
        # Global options
        parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s 2.0.0'
        )
        
        parser.add_argument(
            '--config',
            type=Path,
            help='Path to configuration file'
        )
        
        parser.add_argument(
            '--dir',
            type=Path,
            dest='dbf_path',
            help='Directory containing DBF files (required unless set in config)'
        )
        
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'yaml', 'csv'],
            help='Override default output format'
        )
        
        parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode'
        )
        
        # Commands
        subparsers = parser.add_subparsers(
            dest='command',
            title='Available commands',
            metavar='COMMAND',
            help='Use COMMAND --help for command-specific help'
        )
        
        # Add each command
        for cmd_name, cmd_instance in self.commands.items():
            cmd_parser = subparsers.add_parser(
                cmd_name,
                help=cmd_instance.help_text,
                description=cmd_instance.description
            )
            cmd_instance.add_arguments(cmd_parser)
        
        return parser
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI application.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        try:
            # Load configuration
            self._load_configuration(parsed_args)
            
            # Handle special commands that don't need data access
            if parsed_args.command == 'config':
                return self._handle_config_command(parsed_args, parser)
            
            # Setup library and validate DBF path
            self._setup_library_and_path(parsed_args)
            
            # Create CLI context
            self._create_context(parsed_args)
            
            # Handle commands
            if not parsed_args.command:
                parser.print_help()
                return 0
            
            # Execute command
            return self._execute_command(parsed_args)
            
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
            return 130  # Standard exit code for Ctrl+C
        except CLIError as e:
            print(f"❌ {e}")
            if parsed_args.debug if hasattr(parsed_args, 'debug') else False:
                import traceback
                traceback.print_exc()
            return e.exit_code
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if parsed_args.debug if hasattr(parsed_args, 'debug') else False:
                import traceback
                traceback.print_exc()
            return 1
    
    def _load_configuration(self, args: Namespace):
        """Load configuration from file and command line."""
        try:
            if args.config:
                self.config = CLIConfig.load_from_file(args.config)
            else:
                self.config = load_config()
            
            # Override with command line arguments
            overrides = {}
            if args.format:
                overrides['default_output_format'] = args.format
            if args.no_color:
                overrides['color_output'] = False
            if hasattr(args, 'verbose') and args.verbose:
                overrides['verbose_logging'] = True
            if hasattr(args, 'debug') and args.debug:
                overrides['debug_mode'] = True
            
            if overrides:
                self.config = self.config.merge_with_args(**overrides)
                
        except ConfigError as e:
            raise CLIError(str(e), 1)
    
    def _setup_library_and_path(self, args: Namespace):
        """Setup library discovery and validate DBF path."""
        # Setup library
        try:
            with progress_context("Setting up library"):
                setup_library(self.config.library_path)
        except LibraryNotFoundError as e:
            raise CLIError(str(e), 1)
        
        # Determine DBF path
        dbf_path = args.dbf_path or self.config.default_dbf_path
        if not dbf_path:
            raise CLIError(
                "DBF directory required. Use --dir or set default_dbf_path in config.", 1
            )
        
        # Validate DBF path
        validator = ArgumentValidator()
        validated_path = validator.validate_dbf_path(str(dbf_path))
        if validator.has_errors():
            raise CLIError(validator.get_error_summary(), 1)
        
        if validator.has_warnings() and self.config.verbose_logging:
            print(f"⚠️  {validator.get_warning_summary()}")
        
        self.dbf_path = validated_path
    
    def _create_context(self, args: Namespace):
        """Create CLI context."""
        self.context = CLIContext(
            config=self.config,
            dbf_path=self.dbf_path
        )
    
    def _execute_command(self, args: Namespace) -> int:
        """Execute the specified command."""
        if args.command not in self.commands:
            print(f"❌ Unknown command: {args.command}")
            self._print_available_commands()
            return 1
        
        command = self.commands[args.command]
        
        # Validate command arguments
        validation_errors = command.validate_args(args)
        if validation_errors:
            print("❌ Argument validation failed:")
            for error in validation_errors:
                print(f"  - {error}")
            return 1
        
        # Execute command
        return command.execute(args, self.context)
    
    def _handle_config_command(self, args: Namespace, parser: ArgumentParser) -> int:
        """Handle config command without full initialization."""
        # Create minimal context for config command
        minimal_context = CLIContext(
            config=self.config,
            dbf_path=""  # Not needed for config commands
        )
        
        command = self.commands['config']
        validation_errors = command.validate_args(args)
        if validation_errors:
            print("❌ Argument validation failed:")
            for error in validation_errors:
                print(f"  - {error}")
            return 1
        
        return command.execute(args, minimal_context)
    
    def _print_available_commands(self):
        """Print list of available commands."""
        print("\nAvailable commands:")
        for cmd_name, cmd_instance in self.commands.items():
            print(f"  {cmd_name:<12} {cmd_instance.help_text}")
        print("\nUse 'COMMAND --help' for command-specific help.")
    
    def _get_examples_text(self) -> str:
        """Get examples text for help."""
        return """
Examples:
  # Get employee profile
  openschichtplaner5-cli --dir /path/to/dbf employee profile 52

  # Search employees  
  openschichtplaner5-cli --dir /path/to/dbf employee search "Schmidt"

  # Get employee schedule for current month
  openschichtplaner5-cli --dir /path/to/dbf employee schedule 52

  # Custom query with filters
  openschichtplaner5-cli --dir /path/to/dbf query --table 5EMPL --filter "position=Developer" --limit 10

  # Generate absence report
  openschichtplaner5-cli --dir /path/to/dbf report absence --employee 52 --year 2024

  # Show configuration
  openschichtplaner5-cli config show

  # Create default config file
  openschichtplaner5-cli config create

Configuration:
  Configuration file: ~/.openschichtplaner5/config.yaml
  Environment variables: OPENSCHICHTPLANER5_DBF_PATH, OPENSCHICHTPLANER5_DEBUG

For more information, visit: https://github.com/mschabhuettl/libopenschichtplaner5
"""


def main():
    """Main entry point for the CLI application."""
    app = CLIApplication()
    exit_code = app.run()
    sys.exit(exit_code)