# Too Buff CLI

A command-line tool for tracking your fitness goals and daily check-ins, inspired by the "How to Make Friends When You're Too Buff" weekly planner.

## Installation

### Option 1: Using Poetry (Recommended)

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

### Option 2: Using pipx (For end users)

`pipx` is great for installing CLI applications without Poetry:

```bash
# Install pipx if you don't have it
brew install pipx

# Install toobuff
pipx install .

# Or install from a built wheel
poetry build
pipx install dist/toobuff-*.whl
```

### Option 3: Using a Virtual Environment (Alternative)

If you prefer traditional venv:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -e .
```

After installation, the `toobuff` command will be available in your PATH.

## Usage

### Initialize your goals

```bash
toobuff init
```

This will prompt you to set up:
- Workouts per week
- Wake up time goal
- Weekly cardio time goal
- Weekly average protein goal
- Weekly average calorie goal
- Weekly average steps goal

### Record daily check-ins

```bash
toobuff checkin
```

This interactive command will ask you about:
- Wake up time
- Sleep duration
- Workout details (week, day, primary lift, weights)
- Cardio (medium, duration, zone)
- Optional: protein, calories, steps

### View data file location

```bash
toobuff datafile
```

Prints the location of your data file and opens it in Finder (macOS).

### View data summary

```bash
toobuff data
```

Shows a summary of your recorded data including:
- Days recorded
- Average sleep time
- Average workouts per week
- Average wake time
- Wake up time adherence
- Weekly summaries

## Data Storage

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

## License

MIT

