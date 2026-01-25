"""Configuration and data file management."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from platformdirs import user_config_path, user_data_path


def get_config_dir() -> Path:
    """Get the directory where config files are stored.
    
    Follows platform conventions:
    - Linux: ~/.config/toobuff/
    - macOS: ~/Library/Application Support/toobuff/
    - Windows: %APPDATA%/toobuff/
    """
    config_dir = user_config_path("toobuff")
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the directory where data files are stored.
    
    Follows platform conventions:
    - Linux: ~/.local/share/toobuff/
    - macOS: ~/Library/Application Support/toobuff/
    - Windows: %APPDATA%/toobuff/
    """
    data_dir = user_data_path("toobuff")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_config_dir() / "config.json"


def get_data_path() -> Path:
    """Get the path to the data file."""
    return get_data_dir() / "data.json"


def load_config() -> Optional[Dict[str, Any]]:
    """Load the configuration file."""
    config_path = get_config_path()
    if not config_path.exists():
        return None
    with open(config_path, "r") as f:
        return json.load(f)


def save_config(config: Dict[str, Any]) -> None:
    """Save the configuration file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def load_data() -> Dict[str, Any]:
    """Load the data file."""
    data_path = get_data_path()
    if not data_path.exists():
        return {"checkins": [], "weeks": {}}
    with open(data_path, "r") as f:
        return json.load(f)


def save_data(data: Dict[str, Any]) -> None:
    """Save the data file."""
    data_path = get_data_path()
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)

