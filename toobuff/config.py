"""Configuration and data file management."""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
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
    """Get the path to the latest timestamped config file.
    
    Returns the most recent config_{timestamp}.json file, or None if none exist.
    """
    config_files = list_config_files()
    if config_files:
        return config_files[-1][1]  # Return the latest (last in sorted list)
    return None


def get_data_path() -> Path:
    """Get the path to the data file."""
    return get_data_dir() / "data.json"


def get_timestamped_config_path(timestamp: datetime) -> Path:
    """Get the path to a timestamped config file.

    Args:
        timestamp: The datetime to use for the filename

    Returns:
        Path to config file with timestamp suffix
    """
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    return get_config_dir() / f"config_{timestamp_str}.json"


def list_config_files() -> List[tuple]:
    """List all timestamped config files sorted by timestamp.

    Returns:
        List of (datetime, path) tuples sorted oldest to newest
    """
    config_dir = get_config_dir()
    config_files = []

    # Pattern to match config_{timestamp}.json files
    pattern = re.compile(r"config_(\d{8}_\d{6})\.json$")

    for file_path in config_dir.glob("config_*.json"):
        match = pattern.match(file_path.name)
        if match:
            timestamp_str = match.group(1)
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                config_files.append((timestamp, file_path))
            except ValueError:
                continue

    # Sort by timestamp (oldest first)
    config_files.sort(key=lambda x: x[0])
    return config_files


def load_config() -> Optional[Dict[str, Any]]:
    """Load the latest configuration file (most recent timestamped config)."""
    config_path = get_config_path()
    if config_path is None or not config_path.exists():
        return None
    with open(config_path, "r") as f:
        return json.load(f)


def get_config_path_for_date(target_date: datetime) -> Optional[Path]:
    """Get the path to the config that was active on a specific date.

    Args:
        target_date: The date to find the config for

    Returns:
        Path to the config file that was active on that date, or None if no configs exist
    """
    config_files = list_config_files()

    if not config_files:
        return None

    # Convert target_date to naive datetime for comparison if it's timezone-aware
    if target_date.tzinfo is not None:
        target_date_naive = target_date.replace(tzinfo=None)
    else:
        target_date_naive = target_date

    applicable_path = None

    for timestamp, path in config_files:
        if timestamp <= target_date_naive:
            applicable_path = path
        else:
            break

    if applicable_path is None:
        # No config existed before target_date, use the earliest available
        applicable_path = config_files[0][1]

    return applicable_path


def load_config_for_date(target_date: datetime) -> Optional[Dict[str, Any]]:
    """Load the config that was active on a specific date.

    Finds the most recent timestamped config file that was created
    on or before the target date.

    Args:
        target_date: The date to find the config for

    Returns:
        The config dict that was active on that date, or None if no configs exist
    """
    config_path = get_config_path_for_date(target_date)

    if config_path is None or not config_path.exists():
        return None

    with open(config_path, "r") as f:
        return json.load(f)


def save_config(config: Dict[str, Any], create_timestamped: bool = True) -> None:
    """Save the configuration file as a timestamped config.

    Args:
        config: The configuration dictionary to save
        create_timestamped: Kept for backwards compatibility, always saves timestamped
    """
    now = datetime.now()

    # Add timestamp to config if not present
    if "created_at" not in config:
        config["created_at"] = now.isoformat()

    # Always update the updated_at timestamp
    config["updated_at"] = now.isoformat()

    # Store effective_from for historical lookups
    config["effective_from"] = now.isoformat()

    # Save as timestamped config (only storage method now)
    timestamped_path = get_timestamped_config_path(now)
    with open(timestamped_path, "w") as f:
        json.dump(config, f, indent=2)


def load_data() -> Dict[str, Any]:
    """Load the data file."""
    data_path = get_data_path()
    if not data_path.exists():
        return {"checkins": []}
    data = json.load(open(data_path, "r"))
    # Remove "weeks" if it exists (legacy data structure)
    if "weeks" in data:
        del data["weeks"]
    return data


def save_data(data: Dict[str, Any]) -> None:
    """Save the data file."""
    data_path = get_data_path()
    # Remove "weeks" if it exists (legacy data structure, calculated at runtime)
    data_to_save = {k: v for k, v in data.items() if k != "weeks"}
    with open(data_path, "w") as f:
        json.dump(data_to_save, f, indent=2)
