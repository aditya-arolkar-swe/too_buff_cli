"""CLI commands implementation."""

import click
from datetime import datetime, time, timedelta
import subprocess
import sys
import re

from toobuff.config import (
    load_config,
    save_config,
    load_data,
    save_data,
    get_data_path,
    get_data_dir,
    get_config_dir,
    get_config_path,
)


def style_heading(text: str) -> str:
    """Style a heading with cyan color."""
    return click.style(text, fg="cyan", bold=True)


def style_number(text: str) -> str:
    """Extract and bold all numbers in text."""
    # Pattern to match numbers (integers, floats, percentages, times)
    pattern = r'\d+\.?\d*'
    
    def replace_number(match):
        num = match.group(0)
        return click.style(num, bold=True, fg="yellow")
    
    return re.sub(pattern, replace_number, text)


def style_success(text: str) -> str:
    """Style success messages in green."""
    return click.style(text, fg="green", bold=True)


def style_error(text: str) -> str:
    """Style error messages in red."""
    return click.style(text, fg="red", bold=True)


def style_label(text: str) -> str:
    """Style labels in a subtle color."""
    return click.style(text, fg="bright_blue")


def parse_time(time_str: str) -> time:
    """Parse a time string in HH:MM format."""
    try:
        hour, minute = map(int, time_str.split(":"))
        return time(hour, minute)
    except ValueError:
        raise click.BadParameter("Time must be in HH:MM format (e.g., 06:30)")


def parse_weights(weights_str: str) -> list:
    """Parse weights string into list of {weight, reps} dicts.
    
    Supports formats:
    - "170x5" (assumed lbs)
    - "90kgx5" (converts kg to lbs)
    - "135x5, 185x5, 225x3" (multiple sets)
    
    Always returns weight in lbs.
    """
    if not weights_str or not weights_str.strip():
        return []
    
    KG_TO_LBS = 2.20462
    sets = []
    
    # Split by comma to handle multiple sets
    for set_str in weights_str.split(","):
        set_str = set_str.strip()
        if not set_str:
            continue
        
        # Normalize to lowercase for parsing
        set_str_lower = set_str.lower()
        
        # Check if it's in kg format
        if "kg" in set_str_lower:
            # Remove "kg" and parse (case-insensitive)
            set_str_clean = set_str_lower.replace("kg", "").strip()
            try:
                # Split on 'x' (case-insensitive by normalizing to lowercase)
                parts = set_str_clean.split("x")
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                weight_str, reps_str = parts
                weight_kg = float(weight_str.strip())
                weight_lbs = weight_kg * KG_TO_LBS
                reps = int(reps_str.strip())
                sets.append({"weight": round(weight_lbs, 2), "reps": reps})
            except (ValueError, IndexError):
                raise click.BadParameter(f"Invalid weight format: {set_str}. Use 'weightxreps' or 'weightkgxreps' (e.g., '170x5' or '90kgx5')")
        else:
            # Assume lbs format - normalize to lowercase for splitting
            set_str_normalized = set_str.lower()
            try:
                # Split on 'x' (case-insensitive by normalizing to lowercase)
                parts = set_str_normalized.split("x")
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                weight_str, reps_str = parts
                weight_lbs = float(weight_str.strip())
                reps = int(reps_str.strip())
                sets.append({"weight": round(weight_lbs, 2), "reps": reps})
            except (ValueError, IndexError):
                raise click.BadParameter(f"Invalid weight format: {set_str}. Use 'weightxreps' or 'weightkgxreps' (e.g., '170x5' or '90kgx5')")
    
    return sets


def get_week_number(date: datetime) -> str:
    """Get the week identifier (YYYY-WW format)."""
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def get_week_start(date: datetime) -> datetime:
    """Get the Monday (start) of the week for a given date."""
    # isocalendar() returns (year, week, weekday) where Monday=1, Sunday=7
    _, _, weekday = date.isocalendar()
    days_since_monday = weekday - 1
    week_start = date - timedelta(days=days_since_monday)
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_week_end(date: datetime) -> datetime:
    """Get the Sunday (end) of the week for a given date."""
    week_start = get_week_start(date)
    week_end = week_start + timedelta(days=6)
    return week_end.replace(hour=23, minute=59, second=59, microsecond=999999)


def format_week_header(year: int, week: int, week_start: datetime, week_end: datetime) -> str:
    """Format week header as 'YYYY Week W: Mon DDth -> Sun DDth'."""
    start_month = week_start.strftime("%b")
    start_day = week_start.day
    start_suffix = "th" if 10 <= start_day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(start_day % 10, "th")
    
    end_month = week_end.strftime("%b")
    end_day = week_end.day
    end_suffix = "th" if 10 <= end_day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(end_day % 10, "th")
    
    return f"{year} Week {week}: {start_month} {start_day}{start_suffix} -> {end_month} {end_day}{end_suffix}"


def calculate_weekly_summaries(checkins: list, config: dict) -> dict:
    """Calculate weekly summaries from checkins at runtime."""
    weeks = {}
    
    for checkin in checkins:
        checkin_date = datetime.fromisoformat(checkin["timestamp"])
        week_id = get_week_number(checkin_date)
        
        if week_id not in weeks:
            weeks[week_id] = {
                "year": checkin_date.year,
                "week": checkin_date.isocalendar()[1],
                "week_start": get_week_start(checkin_date),
                "week_end": get_week_end(checkin_date),
                "protein_total": 0.0,
                "protein_days": 0,
                "sleep_total": 0.0,
                "sleep_days": 0,
                "calories_total": 0,
                "calories_days": 0,
                "cardio_total_minutes": 0,
                "steps_total": 0,
                "steps_days": 0,
                "wake_up_adherence": 0,
                "wake_up_total": 0
            }
        
        week_data = weeks[week_id]
        
        # Update sleep
        if checkin.get("sleep_hours"):
            week_data["sleep_total"] += checkin["sleep_hours"]
            week_data["sleep_days"] += 1
        
        # Update cardio
        if checkin.get("cardio") and checkin["cardio"].get("duration_minutes"):
            week_data["cardio_total_minutes"] += checkin["cardio"]["duration_minutes"]
        
        # Update wake up time adherence
        if checkin.get("wake_up_time") and config.get("wake_up_time_goal"):
            try:
                wake_time = parse_time(checkin["wake_up_time"])
                goal_time = parse_time(config["wake_up_time_goal"])
                wake_diff = abs((wake_time.hour * 60 + wake_time.minute) - 
                               (goal_time.hour * 60 + goal_time.minute))
                if wake_diff <= 30:
                    week_data["wake_up_adherence"] += 1
                week_data["wake_up_total"] += 1
            except:
                pass
        
        # Update protein
        if checkin.get("protein"):
            week_data["protein_total"] += checkin["protein"]
            week_data["protein_days"] += 1
        
        # Update calories
        if checkin.get("calories"):
            week_data["calories_total"] += checkin["calories"]
            week_data["calories_days"] += 1
        
        # Update steps
        if checkin.get("steps"):
            week_data["steps_total"] += checkin["steps"]
            week_data["steps_days"] += 1
    
    return weeks


@click.command()
def init_command():
    """Set up your weekly goals and records them in a config file."""
    click.echo(f"{style_heading('Welcome to Too Buff!')} Let's set up your weekly goals.\n")
    
    # Check if config already exists
    existing_config = load_config()
    if existing_config:
        if not click.confirm("Configuration already exists. Do you want to overwrite it?"):
            click.echo(style_error("Cancelled."))
            return
    
    config = {}
    
    # Workouts per week
    config["workouts_per_week"] = click.prompt(
        "How many times do you want to workout per week?",
        type=int,
        default=4
    )
    
    # Wake up time goal
    wake_time_str = click.prompt(
        "What is your wake up time goal? (HH:MM format, e.g., 06:30)",
        default="06:30"
    )
    config["wake_up_time_goal"] = parse_time(wake_time_str).strftime("%H:%M")
    
    # Weekly cardio time goal (in minutes)
    config["weekly_cardio_time_goal"] = click.prompt(
        "What is your weekly cardio time goal? (in minutes)",
        type=int,
        default=150
    )
    
    # Weekly average protein goal (in grams)
    config["weekly_protein_goal"] = click.prompt(
        "What is your weekly average protein goal? (in grams)",
        type=float,
        default=150.0
    )
    
    # Weekly average calorie goal
    config["weekly_calorie_goal"] = click.prompt(
        "What is your weekly average calorie goal?",
        type=int,
        default=2500
    )
    
    # Weekly average steps goal
    config["weekly_steps_goal"] = click.prompt(
        "What is your weekly average steps goal?",
        type=int,
        default=10000
    )
    
    save_config(config)
    click.echo(f"\n{style_success('✓ Configuration saved successfully!')}")
    config_path = get_config_dir() / 'config.json'
    click.echo(click.style(f"Config file location: ", fg="bright_blue") + str(config_path))


@click.command()
def checkin_command():
    """Start interactive mode to record your daily check-in values."""
    config = load_config()
    if not config:
        click.echo(style_error("Error: Configuration not found. Please run 'toobuff init' first."))
        sys.exit(1)
    
    data = load_data()
    
    click.echo(f"{style_heading('Daily Check-in')}\n")
    
    checkin = {
        "timestamp": datetime.now().isoformat(),
    }
    
    # Wake up time
    wake_time_str = click.prompt(
        "What time did you wake up? (HH:MM format, e.g., 06:30)",
        default=datetime.now().strftime("%H:%M")
    )
    checkin["wake_up_time"] = parse_time(wake_time_str).strftime("%H:%M")
    
    # Sleep duration (in hours)
    sleep_hours = click.prompt(
        "How many hours of sleep did you get last night?",
        type=float,
        default=8.0
    )
    checkin["sleep_hours"] = sleep_hours
    
    # Workout information
    did_workout = click.confirm("Did you work out today?", default=True)
    if did_workout:
        workout_week = click.prompt(
            "What week are you in for your powerlifting block?",
            type=int,
            default=1
        )
        workout_day = click.prompt(
            "What day of the week are you in? (1-7)",
            type=int,
            default=1
        )
        
        primary_lift = click.prompt(
            "What was your primary lift? (squat/bench/deadlift)",
            type=click.Choice(["squat", "bench", "deadlift"], case_sensitive=False),
            default="squat"
        ).lower()
        
        weights_str = click.prompt(
            "What weights did you use? (e.g., '135x5, 185x5, 225x3' or '90kgx5')",
            default=""
        )
        
        weights_sets = parse_weights(weights_str) if weights_str else []
        
        checkin["workout"] = {
            "week": workout_week,
            "day": workout_day,
            "primary_lift": primary_lift,
            "weights": weights_sets
        }
    else:
        checkin["workout"] = None
    
    # Cardio
    did_cardio = click.confirm("Did you do cardio today?", default=False)
    if did_cardio:
        cardio_medium = click.prompt(
            "What medium did you use? (e.g., rowing, incline treadmill, bike)",
            default="rowing"
        )
        cardio_duration = click.prompt(
            "How long did you do cardio? (in minutes)",
            type=int,
            default=30
        )
        cardio_zone = click.prompt(
            "What zone? (1-5)",
            type=int,
            default=3
        )
        
        checkin["cardio"] = {
            "medium": cardio_medium,
            "duration_minutes": cardio_duration,
            "zone": cardio_zone
        }
    else:
        checkin["cardio"] = None
    
    # Ask for daily nutrition/steps if available
    if click.confirm("Do you want to record today's protein intake?", default=False):
        protein = click.prompt("Protein (grams)", type=float, default=0.0)
        checkin["protein"] = protein
    
    if click.confirm("Do you want to record today's calorie intake?", default=False):
        calories = click.prompt("Calories", type=int, default=0)
        checkin["calories"] = calories
    
    if click.confirm("Do you want to record today's steps?", default=False):
        steps = click.prompt("Steps", type=int, default=0)
        checkin["steps"] = steps
    
    # Add checkin to data
    if "checkins" not in data:
        data["checkins"] = []
    data["checkins"].append(checkin)
    
    save_data(data)
    click.echo(f"\n{style_success('✓ Check-in recorded successfully!')}")


@click.command()
def datafile_command():
    """Print the location of your data file and open it in Finder."""
    data_path = get_data_path()
    data_dir = get_data_dir()
    
    click.echo(style_label(f"Data file location: ") + str(data_path))
    click.echo(style_label(f"Data directory: ") + str(data_dir))
    
    # Open in Finder (macOS)
    if sys.platform == "darwin":
        if data_path.exists():
            subprocess.run(["open", "-R", str(data_path)])
        else:
            # If file doesn't exist, open the directory instead
            subprocess.run(["open", str(data_dir)])
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", str(data_dir)])
    elif sys.platform == "win32":
        if data_path.exists():
            subprocess.run(["explorer", "/select,", str(data_path)])
        else:
            # If file doesn't exist, open the directory instead
            subprocess.run(["explorer", str(data_dir)])
    else:
        click.echo("Please open the directory manually.")


@click.command()
@click.option('-v', '--verbose', is_flag=True, help='Show data file location and directory paths.')
def data_command(verbose):
    """Print a summary of the data you've recorded so far."""
    config = load_config()
    if not config:
        click.echo(style_error("Error: Configuration not found. Please run 'toobuff init' first."))
        sys.exit(1)
    
    data = load_data()
    
    if not data.get("checkins"):
        click.echo(style_error("No check-ins recorded yet. Use 'toobuff checkin' to record your first check-in."))
        if verbose:
            data_path = get_data_path()
            data_dir = get_data_dir()
            
            # Use ANSI hyperlink escape codes to make paths clickable even with spaces
            file_url = f"file://{data_path}"
            dir_url = f"file://{data_dir}"
            
            click.echo(f"\n{style_label('Data file location: ')}\033]8;;{file_url}\033\\{data_path}\033]8;;\033\\")
            click.echo(f"{style_label('Data directory: ')}\033]8;;{dir_url}\033\\{data_dir}\033]8;;\033\\")
        return
    
    checkins = data["checkins"]
    
    # Calculate weekly summaries at runtime
    weeks = calculate_weekly_summaries(checkins, config)
    
    click.echo(f"\n{style_heading('=== Data Summary ===')}\n")
    
    # Days recorded
    click.echo(style_number(f"Days recorded: {len(checkins)}"))
    
    # Average sleep time
    sleep_total = sum(c.get("sleep_hours", 0) for c in checkins)
    sleep_count = sum(1 for c in checkins if c.get("sleep_hours"))
    if sleep_count > 0:
        avg_sleep = sleep_total / sleep_count
        click.echo(style_number(f"Average sleep time: {avg_sleep:.2f} hours"))
    else:
        click.echo("Average sleep time: N/A")
    
    # Average workouts per week
    workouts = [c for c in checkins if c.get("workout")]
    if weeks:
        total_weeks = len(weeks)
        if total_weeks > 0:
            avg_workouts = len(workouts) / total_weeks
            click.echo(style_number(f"Average workouts per week: {avg_workouts:.2f}"))
        else:
            click.echo("Average workouts per week: N/A")
    else:
        click.echo("Average workouts per week: N/A")
    
    # Average wake time
    wake_times = []
    for c in checkins:
        if c.get("wake_up_time"):
            try:
                wake_time = parse_time(c["wake_up_time"])
                wake_times.append(wake_time.hour * 60 + wake_time.minute)
            except:
                pass
    
    if wake_times:
        avg_wake_minutes = sum(wake_times) / len(wake_times)
        avg_hour = int(avg_wake_minutes // 60)
        avg_min = int(avg_wake_minutes % 60)
        click.echo(style_number(f"Average wake time: {avg_hour:02d}:{avg_min:02d}"))
    else:
        click.echo("Average wake time: N/A")
    
    # Days adhered to wake up time
    if weeks:
        total_adherence = 0
        total_days = 0
        for week_data in weeks.values():
            total_adherence += week_data.get("wake_up_adherence", 0)
            total_days += week_data.get("wake_up_total", 0)
        
        if total_days > 0:
            adherence_rate = (total_adherence / total_days) * 100
            click.echo(style_number(f"Wake up time adherence: {total_adherence}/{total_days} days ({adherence_rate:.1f}%)"))
        else:
            click.echo("Wake up time adherence: N/A")
    else:
        click.echo("Wake up time adherence: N/A")
    
    # Weekly summaries
    if weeks:
        click.echo(f"\n{style_heading('=== Weekly Summaries ===')}")
        for week_id in sorted(weeks.keys()):
            week_data = weeks[week_id]
            year = week_data["year"]
            week = week_data["week"]
            week_start = week_data["week_start"]
            week_end = week_data["week_end"]
            
            week_header = format_week_header(year, week, week_start, week_end)
            click.echo(f"\n{style_heading(week_header)}")
            
            if week_data.get("sleep_days", 0) > 0:
                avg_sleep = week_data["sleep_total"] / week_data["sleep_days"]
                click.echo(style_number(f"  Average sleep: {avg_sleep:.2f} hours"))
            
            if week_data.get("protein_days", 0) > 0:
                avg_protein = week_data["protein_total"] / week_data["protein_days"]
                click.echo(style_number(f"  Average protein: {avg_protein:.1f} g"))
            
            if week_data.get("calories_days", 0) > 0:
                avg_calories = week_data["calories_total"] / week_data["calories_days"]
                click.echo(style_number(f"  Average calories: {avg_calories:.0f}"))
            
            cardio_total = week_data.get("cardio_total_minutes", 0)
            click.echo(style_number(f"  Total cardio: {cardio_total} minutes"))
            
            if week_data.get("steps_days", 0) > 0:
                avg_steps = week_data["steps_total"] / week_data["steps_days"]
                click.echo(style_number(f"  Average steps: {avg_steps:.0f}"))
            
            wake_adherence = week_data.get("wake_up_adherence", 0)
            wake_total = week_data.get("wake_up_total", 0)
            if wake_total > 0:
                adherence_pct = (wake_adherence / wake_total) * 100
                click.echo(style_number(f"  Wake up adherence: {wake_adherence}/{wake_total} ({adherence_pct:.1f}%)"))
    
    if verbose:
        data_path = get_data_path()
        data_dir = get_data_dir()
        
        # Use ANSI hyperlink escape codes to make paths clickable even with spaces
        # Format: \033]8;;<URL>\033\\<text>\033]8;;\033\\
        file_url = f"file://{data_path}"
        dir_url = f"file://{data_dir}"
        
        click.echo(f"\n{style_label('Data file location: ')}\033]8;;{file_url}\033\\{data_path}\033]8;;\033\\")
        click.echo(f"{style_label('Data directory: ')}\033]8;;{dir_url}\033\\{data_dir}\033]8;;\033\\")


@click.command()
@click.option('-v', '--verbose', is_flag=True, help='Show config file location and directory paths.')
def goals_command(verbose):
    """Print your weekly goals."""
    config = load_config()
    if not config:
        click.echo(style_error("Error: Configuration not found. Please run 'toobuff init' first."))
        sys.exit(1)
    
    click.echo(f"\n{style_heading('=== Your Weekly Goals ===')}\n")
    
    # Display all goals
    workouts = config.get('workouts_per_week', 'N/A')
    wake_time = config.get('wake_up_time_goal', 'N/A')
    cardio = config.get('weekly_cardio_time_goal', 'N/A')
    protein = config.get('weekly_protein_goal', 'N/A')
    calories = config.get('weekly_calorie_goal', 'N/A')
    steps = config.get('weekly_steps_goal', 'N/A')
    
    click.echo(style_number(f"Workouts per week: {workouts}"))
    click.echo(style_number(f"Wake up time: {wake_time}"))
    click.echo(style_number(f"Weekly cardio time: {cardio} minutes"))
    click.echo(style_number(f"Weekly average protein: {protein} g"))
    click.echo(style_number(f"Weekly average calories: {calories}"))
    click.echo(style_number(f"Weekly average steps: {steps}"))
    
    if verbose:
        config_path = get_config_path()
        config_dir = get_config_dir()
        
        # Use ANSI hyperlink escape codes to make paths clickable even with spaces
        # Format: \033]8;;<URL>\033\\<text>\033]8;;\033\\
        file_url = f"file://{config_path}"
        dir_url = f"file://{config_dir}"
        
        click.echo(f"\n{style_label('Config file location: ')}\033]8;;{file_url}\033\\{config_path}\033]8;;\033\\")
        click.echo(f"{style_label('Config directory: ')}\033]8;;{dir_url}\033\\{config_dir}\033]8;;\033\\")

