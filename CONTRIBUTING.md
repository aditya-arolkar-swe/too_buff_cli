# Contributing

## Installation Script Details

The quick install script (`install.sh`) performs the following:
- Checks for Python 3.8+
- Installs using `pipx` (if available) or `pip`
- Makes `toobuff` available globally

## Alternative: Install from PyPI

If you prefer to install manually:

```bash
# Using pipx (recommended)
pipx install toobuff

# Or using pip
pip install toobuff
```

## Development Setup

This project uses [Poetry](https://python-poetry.org/) for dependency management:

```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies and the CLI
poetry install

# Run commands using Poetry (no activation needed)
poetry run toobuff init

# Or activate the Poetry shell (spawns a new shell with env activated)
poetry shell
toobuff init

# Note: Poetry cannot modify your current shell's environment directly.
# Use `poetry shell` to get an activated shell, or `poetry run <command>` 
# to run commands without activation.
```

## Data Storage Details

All data is stored locally following platform conventions:
- **Config file**: Stored in platform-specific config directory
  - Linux: `~/.config/toobuff/config.json`
  - macOS: `~/Library/Application Support/toobuff/config.json`
  - Windows: `%APPDATA%\toobuff\config.json`
- **Data file**: Stored in platform-specific data directory
  - Linux: `~/.local/share/toobuff/data.json`
  - macOS: `~/Library/Application Support/toobuff/data.json`
  - Windows: `%APPDATA%\toobuff\data.json`

The tool uses the `platformdirs` library to automatically handle platform-specific paths, following XDG Base Directory specifications and OS conventions.

