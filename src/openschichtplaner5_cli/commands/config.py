# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/config.py
"""
Configuration management commands.
"""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from .base import SubcommandBase, SimpleCommand, CLIContext
from ..core.config import create_default_config_file


class ConfigShowCommand(SimpleCommand):
    """Show current configuration."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--path',
            action='store_true',
            help='Show config file path'
        )
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        if args.path:
            print(context.config.default_config_path)
            return 0
        
        print("Current Configuration:")
        print("=" * 50)
        
        config_dict = context.config.__dict__
        for key, value in config_dict.items():
            if not key.startswith('_'):
                print(f"{key:<25}: {value}")
        
        return 0


class ConfigCreateCommand(SimpleCommand):
    """Create default configuration file."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing config file'
        )
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        config_path = context.config.default_config_path
        
        if config_path.exists() and not args.force:
            self._print_error(f"Config file already exists: {config_path}")
            self._print_info("Use --force to overwrite")
            return 1
        
        try:
            created_path = create_default_config_file()
            self._print_success(f"Created config file: {created_path}")
            return 0
        except Exception as e:
            self._print_error(f"Failed to create config file: {e}")
            return 1


class ConfigCommand(SubcommandBase):
    """Configuration management."""
    
    def __init__(self):
        super().__init__()
        self.add_subcommand('show', ConfigShowCommand())
        self.add_subcommand('create', ConfigCreateCommand())