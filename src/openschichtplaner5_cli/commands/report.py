# openschichtplaner5-cli/src/openschichtplaner5_cli/commands/report.py
"""
Report generation commands (stub implementation).
"""

from argparse import ArgumentParser, Namespace

from .base import SubcommandBase, SimpleCommand, CLIContext


class ReportAbsenceCommand(SimpleCommand):
    """Generate absence report."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument('--employee', type=int, help='Employee ID')
    
    def execute(self, args: Namespace, context: CLIContext) -> int:
        self._print_info("Report commands not yet implemented")
        return 0


class ReportCommand(SubcommandBase):
    """Report generation."""
    
    def __init__(self):
        super().__init__()
        self.add_subcommand('absence', ReportAbsenceCommand())