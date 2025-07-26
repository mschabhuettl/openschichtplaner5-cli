# openschichtplaner5-cli/src/openschichtplaner5_cli/core/exceptions.py
"""
CLI-specific exceptions for OpenSchichtplaner5.
"""


class CLIError(Exception):
    """Base exception for CLI-related errors."""
    
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class ConfigError(CLIError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, config_path: str = None):
        super().__init__(f"Configuration error: {message}")
        self.config_path = config_path


class CommandError(CLIError):
    """Command execution errors."""
    
    def __init__(self, command: str, message: str):
        super().__init__(f"Command '{command}' failed: {message}")
        self.command = command


class LibraryNotFoundError(CLIError):
    """Raised when libopenschichtplaner5 cannot be found."""
    
    def __init__(self, attempted_paths: list = None):
        message = "libopenschichtplaner5 not found"
        if attempted_paths:
            message += f". Searched paths: {', '.join(attempted_paths)}"
        super().__init__(message)
        self.attempted_paths = attempted_paths or []


class DataValidationError(CLIError):
    """Data validation errors."""
    
    def __init__(self, table: str, errors: list):
        super().__init__(f"Validation failed for table {table}: {len(errors)} errors")
        self.table = table
        self.errors = errors


class OutputFormatError(CLIError):
    """Output formatting errors."""
    
    def __init__(self, format_name: str, message: str):
        super().__init__(f"Output format '{format_name}' error: {message}")
        self.format_name = format_name