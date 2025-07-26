#!/usr/bin/env python3
"""
Basic CLI tests for OpenSchichtplaner5 CLI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch
from argparse import ArgumentParser

from openschichtplaner5_cli.core.cli_app import CLIApplication
from openschichtplaner5_cli.core.config import CLIConfig
from openschichtplaner5_cli.commands.config import ConfigShowCommand


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_cli_app_creation(self):
        """Test that CLI application can be created."""
        app = CLIApplication()
        assert app is not None
        assert len(app.commands) > 0
        assert 'config' in app.commands
        assert 'employee' in app.commands
    
    def test_parser_creation(self):
        """Test argument parser creation."""
        app = CLIApplication()
        parser = app.create_parser()
        assert isinstance(parser, ArgumentParser)
        assert parser.prog == 'openschichtplaner5-cli'
    
    def test_config_creation(self):
        """Test configuration creation."""
        config = CLIConfig()
        assert config.default_output_format == 'table'
        assert config.color_output is True
        assert config.max_records_display == 100
    
    def test_config_command(self):
        """Test config command execution."""
        cmd = ConfigShowCommand()
        parser = ArgumentParser()
        cmd.add_arguments(parser)
        
        # Mock context
        mock_config = CLIConfig()
        mock_context = Mock()
        mock_context.config = mock_config
        
        # Mock args
        mock_args = Mock()
        mock_args.path = False
        
        # Execute command
        result = cmd.execute(mock_args, mock_context)
        assert result == 0
    
    def test_help_command(self):
        """Test that help can be displayed."""
        app = CLIApplication()
        
        # Test with help argument
        try:
            app.run(['--help'])
            assert False, "Help should exit"
        except SystemExit as e:
            # Help should exit with code 0
            assert e.code == 0


if __name__ == '__main__':
    # Run basic tests
    test_instance = TestCLIBasics()
    
    print("🧪 Running basic CLI tests...")
    
    try:
        test_instance.test_cli_app_creation()
        print("✅ CLI app creation test passed")
        
        test_instance.test_parser_creation()
        print("✅ Parser creation test passed")
        
        test_instance.test_config_creation()
        print("✅ Config creation test passed")
        
        test_instance.test_config_command()
        print("✅ Config command test passed")
        
        print("\n🎉 All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()