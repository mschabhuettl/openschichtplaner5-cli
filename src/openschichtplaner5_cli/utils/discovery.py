# openschichtplaner5-cli/src/openschichtplaner5_cli/utils/discovery.py
"""
Library discovery utilities for finding libopenschichtplaner5.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

from ..core.exceptions import LibraryNotFoundError


class LibraryDiscovery:
    """Smart discovery of libopenschichtplaner5 library."""
    
    def __init__(self, config_library_path: Optional[str] = None):
        self.config_library_path = config_library_path
        self.attempted_paths: List[str] = []
    
    def discover_and_setup(self) -> bool:
        """
        Discover and setup the library path.
        
        Returns:
            True if library was found and setup successfully
            
        Raises:
            LibraryNotFoundError: If library cannot be found
        """
        search_paths = self._get_search_paths()
        
        for path in search_paths:
            self.attempted_paths.append(str(path))
            
            if self._try_library_path(path):
                return True
        
        # Try direct import as fallback
        if self._try_direct_import():
            return True
        
        raise LibraryNotFoundError(self.attempted_paths)
    
    def _get_search_paths(self) -> List[Path]:
        """Get ordered list of paths to search for the library."""
        paths = []
        
        # 1. Explicit config path
        if self.config_library_path:
            paths.append(Path(self.config_library_path))
        
        # 2. Environment variable
        if 'LIBOPENSCHICHTPLANER5_PATH' in os.environ:
            paths.append(Path(os.environ['LIBOPENSCHICHTPLANER5_PATH']))
        
        # 3. Relative to CLI location (development setup)
        cli_dir = Path(__file__).parent.parent.parent.parent
        dev_paths = [
            cli_dir.parent / "libopenschichtplaner5" / "src",
            cli_dir / "libopenschichtplaner5" / "src",
            cli_dir / ".." / "libopenschichtplaner5" / "src"
        ]
        paths.extend(dev_paths)
        
        # 4. Common installation locations
        home = Path.home()
        common_paths = [
            home / ".local" / "lib" / "python" / "site-packages",
            home / "src" / "libopenschichtplaner5" / "src",
            home / "projects" / "libopenschichtplaner5" / "src",
            Path("/usr/local/lib/python3/site-packages"),
            Path("/opt/libopenschichtplaner5/src"),
        ]
        paths.extend(common_paths)
        
        # 5. Python path locations
        for path_str in sys.path:
            if path_str:
                path = Path(path_str)
                if path.exists():
                    paths.append(path)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in paths:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique_paths.append(resolved)
        
        return unique_paths
    
    def _try_library_path(self, path: Path) -> bool:
        """Try to add a path to sys.path and import the library."""
        if not path.exists():
            return False
        
        # Check if libopenschichtplaner5 exists in this path
        lib_path = path / "libopenschichtplaner5"
        if not lib_path.exists():
            return False
        
        # Add to sys.path if not already there
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
        
        # Try to import
        try:
            import libopenschichtplaner5
            # Test critical components
            from libopenschichtplaner5.registry import TABLE_NAMES
            from libopenschichtplaner5.query_engine import QueryEngine
            return True
        except ImportError:
            # Remove from sys.path if we added it
            if path_str in sys.path:
                sys.path.remove(path_str)
            return False
    
    def _try_direct_import(self) -> bool:
        """Try direct import without path manipulation."""
        try:
            import libopenschichtplaner5
            from libopenschichtplaner5.registry import TABLE_NAMES
            from libopenschichtplaner5.query_engine import QueryEngine
            return True
        except ImportError:
            return False
    
    def get_library_info(self) -> dict:
        """Get information about the discovered library."""
        try:
            import libopenschichtplaner5
            from libopenschichtplaner5.registry import TABLE_NAMES
            
            info = {
                "version": getattr(libopenschichtplaner5, '__version__', 'unknown'),
                "location": libopenschichtplaner5.__file__,
                "available_tables": len(TABLE_NAMES),
                "table_names": TABLE_NAMES
            }
            
            # Check for optional components
            optional_components = {}
            
            try:
                from libopenschichtplaner5.query_engine import QueryEngine
                optional_components["query_engine"] = True
            except ImportError:
                optional_components["query_engine"] = False
            
            try:
                from libopenschichtplaner5.relationships import relationship_manager
                optional_components["relationships"] = True
            except ImportError:
                optional_components["relationships"] = False
            
            try:
                from libopenschichtplaner5.reports import ReportGenerator
                optional_components["reports"] = True
            except ImportError:
                optional_components["reports"] = False
            
            try:
                from libopenschichtplaner5.export import DataExporter
                optional_components["export"] = True
            except ImportError:
                optional_components["export"] = False
            
            info["components"] = optional_components
            return info
            
        except ImportError:
            return {"error": "Library not available"}
    
    def validate_library(self) -> List[str]:
        """Validate the library installation and return any issues."""
        issues = []
        
        try:
            import libopenschichtplaner5
        except ImportError as e:
            issues.append(f"Cannot import libopenschichtplaner5: {e}")
            return issues
        
        # Check critical components
        critical_modules = [
            "libopenschichtplaner5.registry",
            "libopenschichtplaner5.query_engine", 
            "libopenschichtplaner5.models"
        ]
        
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError as e:
                issues.append(f"Cannot import {module}: {e}")
        
        # Check table definitions
        try:
            from libopenschichtplaner5.registry import TABLE_NAMES
            if not TABLE_NAMES:
                issues.append("No table definitions found in registry")
            elif len(TABLE_NAMES) < 10:
                issues.append(f"Only {len(TABLE_NAMES)} tables found, expected more")
        except Exception as e:
            issues.append(f"Cannot access table registry: {e}")
        
        # Test basic functionality
        try:
            from libopenschichtplaner5.query_engine import QueryEngine
            # This will fail if no DBF path is provided, but should not raise ImportError
        except ImportError as e:
            issues.append(f"QueryEngine not available: {e}")
        except Exception:
            # Other exceptions are expected when no data path is provided
            pass
        
        return issues


def setup_library(config_library_path: Optional[str] = None) -> LibraryDiscovery:
    """Setup and validate the library. Returns discovery instance for info."""
    discovery = LibraryDiscovery(config_library_path)
    discovery.discover_and_setup()
    return discovery