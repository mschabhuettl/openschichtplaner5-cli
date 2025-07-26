#!/usr/bin/env python3
"""
Setup script for OpenSchichtplaner5 CLI.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "Command-line interface for OpenSchichtplaner5"

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith("#")
        ]
else:
    requirements = ["PyYAML>=6.0"]

setup(
    name="openschichtplaner5-cli",
    version="2.0.0",
    description="Command-line interface for OpenSchichtplaner5 shift planning data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="OpenSchichtplaner5 Team",
    author_email="info@openschichtplaner5.org",
    url="https://github.com/mschabhuettl/libopenschichtplaner5",
    project_urls={
        "Bug Reports": "https://github.com/mschabhuettl/libopenschichtplaner5/issues",
        "Source": "https://github.com/mschabhuettl/libopenschichtplaner5",
        "Documentation": "https://github.com/mschabhuettl/libopenschichtplaner5/wiki"
    },
    
    # Package information
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0", 
            "black>=22.0.0",
            "mypy>=1.0.0",
            "flake8>=5.0.0"
        ],
        "rich": [
            "rich>=13.0.0",
            "colorama>=0.4.6"
        ]
    },
    
    # Entry points
    entry_points={
        "console_scripts": [
            "openschichtplaner5-cli=openschichtplaner5_cli.core.cli_app:main",
            "os5-cli=openschichtplaner5_cli.core.cli_app:main",  # Short alias
        ]
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Utilities",
        "Environment :: Console"
    ],
    
    # Additional metadata
    keywords="shift planning, workforce management, DBF, command line",
    include_package_data=True,
    zip_safe=False,
)