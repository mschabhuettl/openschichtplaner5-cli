# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/info.py
"""
System information and diagnostics commands.
"""

from argparse import ArgumentParser, Namespace

from .base import SimpleCommand, CLIContext
from ..utils.discovery import LibraryDiscovery


class InfoCommand(SimpleCommand):
    """Show system and library information."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--library',
            action='store_true',
            help='Show detailed library information'
        )
        parser.add_argument(
            '--tables',
            action='store_true',
            help='List available tables'
        )
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        print("OpenSchichtplaner5 CLI Information")
        print("=" * 50)
        
        # Basic info
        print(f"CLI Version:     2.0.0")
        print(f"DBF Path:        {context.dbf_path}")
        print(f"Config File:     {context.config.default_config_path}")
        print(f"Config Exists:   {'Yes' if context.config.default_config_path.exists() else 'No'}")
        
        if args.library:
            print("\nLibrary Information:")
            print("-" * 30)
            
            try:
                discovery = LibraryDiscovery()
                discovery.discover_and_setup()
                
                info = discovery.get_library_info()
                if 'error' in info:
                    print(f"❌ {info['error']}")
                else:
                    print(f"Version:         {info.get('version', 'unknown')}")
                    print(f"Location:        {info.get('location', 'unknown')}")
                    print(f"Available Tables: {info.get('available_tables', 0)}")
                    
                    components = info.get('components', {})
                    print("\nComponents:")
                    for comp, available in components.items():
                        status = "✅" if available else "❌"
                        print(f"  {comp:<15}: {status}")
                
                # Validation
                issues = discovery.validate_library()
                if issues:
                    print(f"\n⚠️  Library Issues:")
                    for issue in issues:
                        print(f"  - {issue}")
                else:
                    print(f"\n✅ Library validation passed")
                    
            except Exception as e:
                print(f"❌ Failed to get library info: {e}")
        
        if args.tables:
            print("\nAvailable Tables:")
            print("-" * 30)
            
            try:
                from libopenschichtplaner5.registry import TABLE_NAMES
                for table in sorted(TABLE_NAMES):
                    print(f"  {table}")
            except Exception as e:
                print(f"❌ Failed to get table list: {e}")
        
        return 0