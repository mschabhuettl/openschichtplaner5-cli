# openschichtplaner5-cli/src/openschichtplaner5_cli/core/config.py
"""
Configuration management for OpenSchichtplaner5 CLI.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from .exceptions import ConfigError


@dataclass
class CLIConfig:
    """CLI configuration settings."""
    
    # Data source settings
    default_dbf_path: Optional[str] = None
    library_path: Optional[str] = None
    
    # Output settings
    default_output_format: str = "table"
    color_output: bool = True
    max_records_display: int = 100
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    
    # Performance settings
    query_timeout: int = 30
    cache_enabled: bool = True
    parallel_loading: bool = True
    
    # Interactive mode settings
    interactive_history_size: int = 1000
    auto_completion: bool = True
    
    # Report settings
    default_report_format: str = "json"
    report_output_dir: Optional[str] = None
    
    # Advanced settings
    debug_mode: bool = False
    verbose_logging: bool = False
    profiling_enabled: bool = False
    
    # Template paths
    template_dirs: list = field(default_factory=lambda: ["~/.openschichtplaner5/templates"])
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'CLIConfig':
        """Load configuration from YAML file."""
        try:
            if not config_path.exists():
                return cls()  # Return default config
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Expand user paths
            if 'default_dbf_path' in data and data['default_dbf_path']:
                data['default_dbf_path'] = str(Path(data['default_dbf_path']).expanduser())
            
            if 'library_path' in data and data['library_path']:
                data['library_path'] = str(Path(data['library_path']).expanduser())
            
            if 'report_output_dir' in data and data['report_output_dir']:
                data['report_output_dir'] = str(Path(data['report_output_dir']).expanduser())
            
            # Expand template directories
            if 'template_dirs' in data:
                data['template_dirs'] = [str(Path(d).expanduser()) for d in data['template_dirs']]
            
            return cls(**data)
            
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML syntax: {e}", str(config_path))
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}", str(config_path))
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(asdict(self), f, default_flow_style=False, sort_keys=True)
                
        except Exception as e:
            raise ConfigError(f"Failed to save config: {e}", str(config_path))
    
    def merge_with_args(self, **kwargs) -> 'CLIConfig':
        """Create new config by merging with command line arguments."""
        # Only merge non-None values
        updates = {k: v for k, v in kwargs.items() if v is not None}
        
        config_dict = asdict(self)
        config_dict.update(updates)
        
        return CLIConfig(**config_dict)
    
    @property
    def config_dir(self) -> Path:
        """Get the configuration directory."""
        return Path.home() / ".openschichtplaner5"
    
    @property
    def default_config_path(self) -> Path:
        """Get the default configuration file path."""
        return self.config_dir / "config.yaml"
    
    def validate(self) -> list:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check paths exist if specified
        if self.default_dbf_path:
            path = Path(self.default_dbf_path)
            if not path.exists():
                issues.append(f"Default DBF path does not exist: {path}")
        
        if self.library_path:
            path = Path(self.library_path)
            if not path.exists():
                issues.append(f"Library path does not exist: {path}")
        
        if self.report_output_dir:
            path = Path(self.report_output_dir)
            if not path.parent.exists():
                issues.append(f"Report output directory parent does not exist: {path.parent}")
        
        # Check format values
        valid_formats = ["table", "json", "csv", "yaml"]
        if self.default_output_format not in valid_formats:
            issues.append(f"Invalid output format: {self.default_output_format}")
        
        valid_report_formats = ["json", "html", "markdown", "pdf"]
        if self.default_report_format not in valid_report_formats:
            issues.append(f"Invalid report format: {self.default_report_format}")
        
        # Check numeric ranges
        if self.max_records_display < 1:
            issues.append("max_records_display must be at least 1")
        
        if self.query_timeout < 1:
            issues.append("query_timeout must be at least 1 second")
        
        if self.interactive_history_size < 0:
            issues.append("interactive_history_size cannot be negative")
        
        return issues


def load_config() -> CLIConfig:
    """Load configuration from default locations."""
    config = CLIConfig()
    
    # Try to load from default location
    default_path = config.default_config_path
    if default_path.exists():
        config = CLIConfig.load_from_file(default_path)
    
    # Override with environment variables
    env_overrides = {}
    
    if 'OPENSCHICHTPLANER5_DBF_PATH' in os.environ:
        env_overrides['default_dbf_path'] = os.environ['OPENSCHICHTPLANER5_DBF_PATH']
    
    if 'OPENSCHICHTPLANER5_DEBUG' in os.environ:
        env_overrides['debug_mode'] = os.environ['OPENSCHICHTPLANER5_DEBUG'].lower() in ('1', 'true', 'yes')
    
    if 'OPENSCHICHTPLANER5_NO_COLOR' in os.environ:
        env_overrides['color_output'] = False
    
    if env_overrides:
        config = config.merge_with_args(**env_overrides)
    
    return config


def create_default_config_file() -> Path:
    """Create a default configuration file."""
    config = CLIConfig()
    config_path = config.default_config_path
    
    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add comments to the YAML file
    yaml_content = """# OpenSchichtplaner5 CLI Configuration
# See https://github.com/mschabhuettl/libopenschichtplaner5 for documentation

# Data source settings
default_dbf_path: null  # Path to directory containing DBF files
library_path: null      # Path to libopenschichtplaner5 if not installed

# Output settings  
default_output_format: table  # table, json, csv, yaml
color_output: true
max_records_display: 100
date_format: "%Y-%m-%d"
time_format: "%H:%M:%S"

# Performance settings
query_timeout: 30
cache_enabled: true
parallel_loading: true

# Interactive mode
interactive_history_size: 1000
auto_completion: true

# Reports
default_report_format: json  # json, html, markdown, pdf
report_output_dir: null      # Default: current directory

# Advanced
debug_mode: false
verbose_logging: false
profiling_enabled: false

# Template directories
template_dirs:
  - ~/.openschichtplaner5/templates
"""
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    return config_path