# OpenSchichtplaner5 CLI 2.0

🚀 **Komplett überarbeitete CLI** für OpenSchichtplaner5 Datenanalyse und -verwaltung.

## ✨ Features

### 🏗️ **Modulare Architektur**
- **Command Pattern**: Saubere Trennung von Commands
- **Plugin-System**: Erweiterbare Befehls-Module  
- **Smart Library Discovery**: Automatische Pfad-Erkennung
- **Konfigurationssystem**: YAML-basierte Konfiguration

### 🔍 **Erweiterte Query-Engine**
- **Intelligente Filter**: `--filter "name=Schmidt"`, `--filter "age>=25"`
- **Mehrfach-Filter**: Kombinierbare Bedingungen
- **Smart Type Detection**: Automatische Typ-Konvertierung
- **Join-Support**: Tabellen-übergreifende Abfragen

### 📊 **Flexible Ausgabe-Formate**
- **Table**: Formatierte ASCII-Tabellen
- **JSON**: Strukturierte Datenausgabe  
- **YAML**: Human-readable Format
- **CSV**: Excel-kompatible Daten

### 💻 **Benutzerfreundlichkeit**
- **Progress Indicators**: Spinner und Progress-Bars
- **Intelligent Defaults**: Sinnvolle Standard-Einstellungen
- **Error Handling**: Detaillierte Fehlermeldungen
- **Auto-Completion**: Bash/Zsh Support (geplant)

## 🚀 Quick Start

### Installation
```bash
# Installation der CLI
pip install -e .

# Abhängigkeiten installieren  
pip install -r requirements.txt
```

### Erstmalige Konfiguration
```bash
# Standard-Konfiguration erstellen
openschichtplaner5-cli config create

# Konfiguration anzeigen
openschichtplaner5-cli config show

# DBF-Pfad in Config setzen (optional)
echo "default_dbf_path: /path/to/your/dbf/files" >> ~/.openschichtplaner5/config.yaml
```

## 📖 Beispiel-Commands

### Employee-Verwaltung
```bash
# Mitarbeiter-Profil anzeigen
openschichtplaner5-cli --dir /path/to/dbf employee profile 52

# Mitarbeiter suchen
openschichtplaner5-cli employee search "Schmidt"

# Dienstplan für aktuellen Monat
openschichtplaner5-cli employee schedule 52 --format calendar
```

### Erweiterte Queries  
```bash
# Entwickler mit Filterung
openschichtplaner5-cli query --table 5EMPL --filter "position=Developer" --limit 10

# Mehrfach-Filter mit JSON-Output
openschichtplaner5-cli query --table 5EMPL \
  --filter "active=true" \
  --filter "start_date>=2023-01-01" \
  --format json

# Tabellen-Join mit bestimmten Feldern
openschichtplaner5-cli query --table 5EMPL \
  --join 5GRASG \
  --fields "id,name,group_id" \
  --order "name"
```

### System-Information
```bash
# Bibliothek-Info und Diagnose
openschichtplaner5-cli info --library --tables

# Verfügbare Tabellen auflisten
openschichtplaner5-cli info --tables
```

## 🏗️ Architektur-Übersicht

### Neue modulare Struktur:
```
src/openschichtplaner5_cli/
├── core/                    # Kern-Komponenten
│   ├── cli_app.py          # Haupt-Anwendung  
│   ├── config.py           # Konfiguration
│   └── exceptions.py       # CLI-spezifische Exceptions
├── commands/               # Command-Module
│   ├── employee.py         # Mitarbeiter-Befehle
│   ├── query.py           # Erweiterte Queries
│   ├── config.py          # Konfigurations-Befehle
│   └── ...
├── output/                 # Ausgabe-Formatierung
│   ├── formatters.py      # Format-Handler
│   └── tables.py          # Tabellen-Formatierung
└── utils/                  # Hilfsfunktionen
    ├── discovery.py       # Library-Discovery
    ├── parsing.py         # Argument-Parsing
    └── progress.py        # Progress-Anzeigen
```

### ✅ Verbesserungen gegenüber v1:

| Aspekt | v1 (Alt) | v2 (Neu) |
|--------|----------|----------|
| **Architektur** | Monolithisch (613 Zeilen) | Modularer Command Pattern |
| **Konfiguration** | Hardcoded Pfade | YAML + Environment Variables |
| **Fehlerbehandlung** | Inkonsistent | Strukturierte Exceptions |
| **Filter-Syntax** | `--where field op value` | `--filter "field=value"` |
| **Library-Discovery** | Fragiles Path-Handling | Smart Discovery mit Fallbacks |
| **Ausgabe** | Gemischte Print-Statements | Spezialisierte Formatter |
| **Testing** | Keine Struktur | Testbare Command-Module |
| **Erweiterbarkeit** | Schwierig | Plugin-System |

## 🔧 Konfiguration

### Standard-Pfad: `~/.openschichtplaner5/config.yaml`

```yaml
# Datenquellen
default_dbf_path: /path/to/dbf/files
library_path: null

# Ausgabe-Einstellungen  
default_output_format: table
color_output: true
max_records_display: 100

# Performance
query_timeout: 30
cache_enabled: true

# Debug
debug_mode: false
verbose_logging: false
```

### Environment Variables
```bash
export OPENSCHICHTPLANER5_DBF_PATH=/path/to/dbf
export OPENSCHICHTPLANER5_DEBUG=1
export OPENSCHICHTPLANER5_NO_COLOR=1
```

## 🧪 Entwicklung & Testing

```bash
# Entwicklungs-Setup
pip install -e ".[dev]"

# Tests ausführen (geplant)
pytest tests/

# Code-Formatierung
black src/

# Type-Checking  
mypy src/
```

## 🚧 Roadmap

### Phase 1 ✅ (Implementiert)
- [x] Modulare Architektur mit Command Pattern
- [x] Konfigurationssystem mit YAML
- [x] Smart Library Discovery
- [x] Erweiterte Filter-Parser
- [x] Flexible Output-Formatter

### Phase 2 🚧 (In Entwicklung)  
- [ ] Vollständige Command-Implementierungen
- [ ] Report-Generation System
- [ ] Data Validation Framework
- [ ] Unit Test Suite

### Phase 3 📋 (Geplant)
- [ ] Interactive Mode (REPL)
- [ ] Template-System für Reports
- [ ] Plugin-API für Custom Commands
- [ ] Bash/Zsh Auto-Completion
- [ ] Performance Profiling Tools

## 📄 Lizenz

MIT License - siehe LICENSE Datei für Details.
