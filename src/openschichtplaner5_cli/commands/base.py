# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/base.py
"""
Base command class and CLI context for OpenSchichtplaner5.
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core.config import CLIConfig
from ..core.exceptions import CommandError
from ..utils.progress import ProgressIndicator


@dataclass
class CLIContext:
    """Context object passed to all commands."""
    config: CLIConfig
    dbf_path: str
    query_engine: Optional[Any] = None
    report_generator: Optional[Any] = None
    data_exporter: Optional[Any] = None
    validator: Optional[Any] = None
    discovery: Optional[Any] = None
    
    def initialize_components(self):
        """Lazy initialization of heavy components."""
        if self.query_engine is None:
            from ..utils.progress import progress_context
            
            with progress_context("Initializing data engine"):
                try:
                    # Import here to avoid circular imports
                    from libopenschichtplaner5.query_engine import QueryEngine
                    from libopenschichtplaner5.reports import ReportGenerator
                    from libopenschichtplaner5.export import DataExporter
                    from libopenschichtplaner5.utils.validation import DataValidator
                    
                    self.query_engine = QueryEngine(self.dbf_path)
                    self.report_generator = ReportGenerator(self.query_engine)
                    self.data_exporter = DataExporter()
                    self.validator = DataValidator()
                    
                except ImportError as e:
                    raise CommandError("initialization", 
                                     f"Required library components not available: {e}")
                except Exception as e:
                    raise CommandError("initialization", 
                                     f"Failed to initialize components: {e}")
    
    def ensure_components(self):
        """Ensure all components are initialized."""
        if self.query_engine is None:
            self.initialize_components()


class BaseCommand(ABC):
    """Abstract base class for all CLI commands."""
    
    def __init__(self):
        self.name = self.__class__.__name__.lower().replace('command', '')
    
    @abstractmethod
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command-specific arguments to the parser."""
        pass
    
    @abstractmethod
    def execute(self, args: Namespace, context: CLIContext) -> int:
        """
        Execute the command.
        
        Args:
            args: Parsed command line arguments
            context: CLI context with configuration and components
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass
    
    def validate_args(self, args: Namespace) -> list:
        """
        Validate command arguments.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        return []
    
    @property
    def description(self) -> str:
        """Get command description."""
        return self.__doc__ or f"{self.name.title()} command"
    
    @property
    def help_text(self) -> str:
        """Get command help text."""
        return self.description
    
    def _print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"❌ Error: {message}")
    
    def _print_warning(self, message: str) -> None:
        """Print a warning message.""" 
        print(f"⚠️  Warning: {message}")
    
    def _print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"✅ {message}")
    
    def _print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"ℹ️  {message}")


class SubcommandBase(BaseCommand):
    """Base class for commands that have subcommands."""
    
    def __init__(self):
        super().__init__()
        self.subcommands: Dict[str, BaseCommand] = {}
    
    def add_subcommand(self, name: str, command: BaseCommand) -> None:
        """Add a subcommand."""
        self.subcommands[name] = command
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add subcommand arguments."""
        if not self.subcommands:
            return
        
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help=f"{self.name.title()} subcommands",
            metavar='SUBCOMMAND'
        )
        
        for subcmd_name, subcmd in self.subcommands.items():
            subcmd_parser = subparsers.add_parser(
                subcmd_name,
                help=subcmd.help_text,
                description=subcmd.description
            )
            subcmd.add_arguments(subcmd_parser)
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        """Execute the appropriate subcommand."""
        if not hasattr(args, 'subcommand') or not args.subcommand:
            self._print_error(f"No subcommand specified for {self.name}")
            self._print_available_subcommands()
            return 1
        
        if args.subcommand not in self.subcommands:
            self._print_error(f"Unknown subcommand: {args.subcommand}")
            self._print_available_subcommands()
            return 1
        
        subcmd = self.subcommands[args.subcommand]
        
        # Validate arguments
        validation_errors = subcmd.validate_args(args)
        if validation_errors:
            self._print_error("Argument validation failed:")
            for error in validation_errors:
                print(f"  - {error}")
            return 1
        
        return subcmd.execute(args, context)
    
    def _print_available_subcommands(self) -> None:
        """Print available subcommands."""
        if self.subcommands:
            print(f"\nAvailable {self.name} subcommands:")
            for name, cmd in self.subcommands.items():
                print(f"  {name:<15} {cmd.help_text}")


class SimpleCommand(BaseCommand):
    """Base class for simple commands without subcommands."""
    
    def validate_args(self, args: Namespace) -> list:
        """Default validation - can be overridden."""
        return []