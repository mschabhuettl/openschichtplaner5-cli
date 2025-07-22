# openschichtplaner5-cli/src/openschichtplaner5_cli/__main__.py
"""
Main entry point for the OpenSchichtplaner5 CLI.
"""
import sys
from pathlib import Path

# WICHTIG: Library-Pfad hinzufügen!
lib_path = Path(__file__).parent.parent.parent.parent / "libopenschichtplaner5" / "src"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))
else:
    # Fallback für installierte Version
    try:
        import libopenschichtplaner5
    except ImportError:
        print("ERROR: libopenschichtplaner5 not found!")
        print("Please ensure the library is installed or run from the project root.")
        sys.exit(1)

from .enhanced_cli import main

if __name__ == "__main__":
    main()