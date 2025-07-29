# src/openschichtplaner5_cli/enhanced_cli.py
"""
Enhanced CLI - now redirects to v2 implementation.
This file maintains backward compatibility.
"""

# Import the new v2 implementation
from .enhanced_cli_v2 import main, EnhancedCLIv2

# For backward compatibility, also export the original interface
from .enhanced_cli_v2 import (
    ConfigManager,
    RichFormatter,
    InteractiveShell,
)

# Legacy compatibility - in case anything imports these directly
CLIFormatter = RichFormatter
EnhancedCLI = EnhancedCLIv2

# The main function is already imported from v2

if __name__ == "__main__":
    main()