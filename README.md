# openschichtplaner5-cli

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Rich](https://img.shields.io/badge/Rich-CLI-orange.svg)](https://rich.readthedocs.io/)

Interactive command-line interface for OpenSchichtplaner5 - explore and analyze Schichtplaner5 data from the terminal.

## 🎯 Overview

The CLI provides a powerful, interactive terminal interface for exploring Schichtplaner5 data, running queries, generating reports, and exporting data in various formats.

## 🚀 Quick Start

```bash
# Interactive shell mode
python -m openschichtplaner5_cli --dir /path/to/dbf/files --interactive

# Quick data overview
python -m openschichtplaner5_cli --dir /path/to/dbf/files --summary

# Export data
python -m openschichtplaner5_cli --dir /path/to/dbf/files --export csv --output data.csv
```

## ✨ Features

- **Interactive Shell**: Rich terminal interface with command history
- **Data Exploration**: Browse employees, shifts, absences, and more
- **Query Builder**: Fluent query interface with filtering and sorting
- **Multiple Export Formats**: CSV, JSON, Excel, HTML, Markdown
- **Analytics**: Built-in reporting and analytics functions
- **Configuration**: YAML-based configuration with user profiles

## 🖥️ Interactive Commands

```bash
# List all employees
> employees

# Filter employees by department
> employees.filter(department="Human Resources")

# Get shift schedule for date range
> schedule.range("2025-01-01", "2025-01-31")

# Export filtered data
> employees.filter(active=True).export("active_employees.csv")
```

## 📄 License

This CLI is part of the OpenSchichtplaner5 project and is licensed under the MIT License.
