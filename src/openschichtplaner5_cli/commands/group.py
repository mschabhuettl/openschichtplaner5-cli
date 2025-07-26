# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/group.py
"""
Group-related commands (stub implementation).
"""

from argparse import ArgumentParser, Namespace

from .base import SubcommandBase, SimpleCommand, CLIContext


class GroupListCommand(SimpleCommand):
    """List all groups."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        pass
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        self._print_info("Group commands not yet implemented")
        return 0


class GroupCommand(SubcommandBase):
    """Group management and queries."""
    
    def __init__(self):
        super().__init__()
        self.add_subcommand('list', GroupListCommand())