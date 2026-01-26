"""CLI commands implementation."""

import click
from datetime import datetime, time, timedelta, timezone
import subprocess
import sys
import re
import pytz

from toobuff.config import (
    load_config,
    load_config_for_date,
    get_config_path_for_date,
    save_config,
    load_data,
    save_data,
    get_data_path,
    get_data_dir,
    get_config_dir,
    get_config_path,
)


def style_heading(text: str) -> str:
    """Style a heading with blue (USA theme)."""
    return click.style(text, fg="blue", bold=True)


def style_number(text: str) -> str:
    """Extract and bold all numbers in text."""
    # Pattern to match numbers (integers, floats, percentages, times)
    pattern = r"\d+\.?\d*"

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
    """Style labels in brown/black (USA theme - for details/links)."""
    # Using black since brown isn't a standard terminal color
    return click.style(text, fg="black")


def style_brown(text: str) -> str:
    """Style text in brown color."""
    # Use ANSI color code for brown (RGB: 139, 69, 19 or use 256-color mode)
    # Using bright_black as a brown approximation, or 256-color brown
    return f"\033[38;5;130m{text}\033[0m"


def style_question(text: str) -> str:
    """Style questions/prompts with magenta (very different from blue)."""
    return click.style(text, fg="magenta")


def style_question_purple(text: str) -> str:
    """Style questions/prompts with purple (for goals update)."""
    return click.style(text, fg="bright_magenta")


def style_response(text: str) -> str:
    """Style user responses in bold white (USA theme)."""
    return click.style(str(text), fg="white", bold=True)


def style_timestamp(text: str) -> str:
    """Style timestamp/recording line with red (USA theme)."""
    return click.style(text, fg="red")


def format_label_value(label: str, value: str, label_width: int = None) -> str:
    """Format a label-value pair with consistent alignment.

    Args:
        label: The label text (may include indentation like "  Label")
        value: The value to display
        label_width: Fixed width for the full label including indent. Colon will be placed at the end. If None, uses default widths.

    Returns:
        Formatted string with aligned label (colon in same column) and left-aligned value.
    """
    if label_width is None:
        # Default widths for different contexts
        label_width = 30  # Default for main summary

    # Extract indentation if present
    stripped_label = label.lstrip()
    indent = label[: len(label) - len(stripped_label)]

    # Pad label to width so colon is always in the same column
    padded_label = (indent + stripped_label).ljust(label_width)

    return style_number(f"{padded_label}: {value}")


def parse_time(time_str: str) -> time:
    """Parse a time string in HH:MM format."""
    try:
        hour, minute = map(int, time_str.split(":"))
        return time(hour, minute)
    except ValueError:
        raise click.BadParameter("Time must be in HH:MM format (e.g., 06:30)")


def parse_backfill_date(date_str: str) -> datetime:
    """Parse a backfill date string.

    Supports formats:
    - DD (assumes current month/year)
    - MM-DD (assumes current year)
    - YYYY-MM-DD (full date)

    Args:
        date_str: The date string to parse

    Returns:
        datetime object set to 5pm (17:00) of the specified date (naive, will be localized to ET)
    """
    et_tz = pytz.timezone("US/Eastern")
    now = datetime.now(et_tz)
    date_str = date_str.strip()

    try:
        # Try YYYY-MM-DD format
        if len(date_str.split("-")) == 3:
            year, month, day = map(int, date_str.split("-"))
            target_date = datetime(year, month, day, 17, 0, 0)
        # Try MM-DD format
        elif len(date_str.split("-")) == 2:
            month, day = map(int, date_str.split("-"))
            target_date = datetime(now.year, month, day, 17, 0, 0)
        # Try DD format
        else:
            day = int(date_str)
            target_date = datetime(now.year, now.month, day, 17, 0, 0)

        return target_date
    except (ValueError, TypeError) as e:
        raise click.BadParameter(
            f"Invalid date format: {date_str}. Use DD, MM-DD, or YYYY-MM-DD (e.g., '15', '01-15', or '2026-01-15')"
        )


def parse_block_day(block_str: str) -> tuple:
    """Parse a block day string like 'week 2 day 1' or 'w2d1'.

    Args:
        block_str: String in format 'week X day Y', 'wXdY', or 'X Y'

    Returns:
        Tuple of (week, day) as integers

    Raises:
        click.BadParameter if format is invalid
    """
    block_str = block_str.lower().strip()

    # Try "week X day Y" format
    week_day_match = re.match(r"week\s*(\d+)\s*day\s*(\d+)", block_str)
    if week_day_match:
        return int(week_day_match.group(1)), int(week_day_match.group(2))

    # Try "wXdY" format
    short_match = re.match(r"w(\d+)\s*d(\d+)", block_str)
    if short_match:
        return int(short_match.group(1)), int(short_match.group(2))

    # Try "X Y" format (just two numbers)
    numbers_match = re.match(r"(\d+)\s+(\d+)", block_str)
    if numbers_match:
        return int(numbers_match.group(1)), int(numbers_match.group(2))

    raise click.BadParameter(
        f"Invalid format: {block_str}. Use 'week X day Y', 'wXdY', or 'X Y' (e.g., 'week 2 day 1', 'w2d1', or '2 1')"
    )


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
                raise click.BadParameter(
                    f"Invalid weight format: {set_str}. Use 'weightxreps' or 'weightkgxreps' (e.g., '170x5' or '90kgx5')"
                )
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
                raise click.BadParameter(
                    f"Invalid weight format: {set_str}. Use 'weightxreps' or 'weightkgxreps' (e.g., '170x5' or '90kgx5')"
                )

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


def format_week_header(
    year: int, week: int, week_start: datetime, week_end: datetime
) -> str:
    """Format week header as 'YYYY Week W: Mon DDth -> Sun DDth'."""
    start_month = week_start.strftime("%b")
    start_day = week_start.day
    start_suffix = (
        "th"
        if 10 <= start_day % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(start_day % 10, "th")
    )

    end_month = week_end.strftime("%b")
    end_day = week_end.day
    end_suffix = (
        "th"
        if 10 <= end_day % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(end_day % 10, "th")
    )

    return f"{year} Week {week}: {start_month} {start_day}{start_suffix} -> {end_month} {end_day}{end_suffix}"


def calculate_wake_up_adherence(wake_up_times: list, wake_up_time_goal: str) -> tuple:
    """Calculate wake up time adherence against a goal.

    Args:
        wake_up_times: List of wake up time strings (HH:MM format)
        wake_up_time_goal: Goal wake up time string (HH:MM format)

    Returns:
        Tuple of (adherence_count, total_count)
    """
    wake_total = len(wake_up_times)
    wake_adherence = 0

    if wake_total > 0 and wake_up_time_goal:
        try:
            goal_time = parse_time(wake_up_time_goal)
            goal_minutes = goal_time.hour * 60 + goal_time.minute

            for wake_time_str in wake_up_times:
                try:
                    wake_time = parse_time(wake_time_str)
                    wake_minutes = wake_time.hour * 60 + wake_time.minute
                    if abs(wake_minutes - goal_minutes) <= 30:
                        wake_adherence += 1
                except:
                    pass
        except:
            pass

    return wake_adherence, wake_total


def calculate_weekly_summaries(checkins: list) -> dict:
    """Calculate weekly summaries from checkins at runtime.

    Note: wake_up_adherence is NOT calculated here - it's calculated separately
    using historical configs for each week.
    """
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
                "wake_up_times": [],  # Store actual wake up times (adherence calculated later)
                "workout_count": 0,
            }

        week_data = weeks[week_id]

        # Update sleep
        if checkin.get("sleep_hours"):
            week_data["sleep_total"] += checkin["sleep_hours"]
            week_data["sleep_days"] += 1

        # Update cardio
        if checkin.get("cardio") and checkin["cardio"].get("duration_minutes"):
            week_data["cardio_total_minutes"] += checkin["cardio"]["duration_minutes"]

        # Store wake up times (adherence calculated later with historical config)
        if checkin.get("wake_up_time"):
            week_data["wake_up_times"].append(checkin["wake_up_time"])

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

        # Update workout count
        if checkin.get("workout"):
            week_data["workout_count"] += 1

    return weeks


def check_goals_for_week(week_data: dict, week_checkins: list, config: dict) -> dict:
    """Check if goals are met for a week.

    Uses the provided config (should be historical config for that week)
    to determine goal values and calculate adherence.

    Returns a dict with goal names as keys and dicts containing:
    - 'met': True/False/None
    - 'goal': goal value
    - 'actual': actual value (if applicable)
    """
    goals_info = {}

    # Workouts per week
    workouts_goal = config.get("workouts_per_week", 0)
    workouts_actual = week_data.get("workout_count", 0)
    goals_info["workouts"] = {
        "met": workouts_actual >= workouts_goal if workouts_goal > 0 else None,
        "goal": workouts_goal,
        "actual": workouts_actual,
    }

    # Weekly cardio time goal
    cardio_goal = config.get("weekly_cardio_time_goal", 0)
    cardio_actual = week_data.get("cardio_total_minutes", 0)
    goals_info["cardio"] = {
        "met": cardio_actual >= cardio_goal if cardio_goal > 0 else None,
        "goal": cardio_goal,
        "actual": cardio_actual,
    }

    # Weekly average protein goal (with 2g tolerance)
    protein_goal = config.get("weekly_protein_goal", 0)
    if week_data.get("protein_days", 0) > 0:
        protein_actual = week_data["protein_total"] / week_data["protein_days"]
        # Check if within 2g tolerance (actual >= goal - 2)
        protein_met = (
            protein_actual >= (protein_goal - 2.0) if protein_goal > 0 else None
        )
        goals_info["protein"] = {
            "met": protein_met,
            "goal": protein_goal,
            "actual": protein_actual,
        }
    else:
        goals_info["protein"] = {"met": None, "goal": protein_goal, "actual": None}

    # Weekly average calorie goal (with 5% tolerance)
    calories_goal = config.get("weekly_calorie_goal", 0)
    if week_data.get("calories_days", 0) > 0:
        calories_actual = week_data["calories_total"] / week_data["calories_days"]
        # Check if within 5% tolerance (actual >= goal * 0.95)
        calories_met = (
            calories_actual >= (calories_goal * 0.95) if calories_goal > 0 else None
        )
        goals_info["calories"] = {
            "met": calories_met,
            "goal": calories_goal,
            "actual": calories_actual,
        }
    else:
        goals_info["calories"] = {"met": None, "goal": calories_goal, "actual": None}

    # Weekly average steps goal
    steps_goal = config.get("weekly_steps_goal", 0)
    if week_data.get("steps_days", 0) > 0:
        steps_actual = week_data["steps_total"] / week_data["steps_days"]
        goals_info["steps"] = {
            "met": steps_actual >= steps_goal if steps_goal > 0 else None,
            "goal": steps_goal,
            "actual": steps_actual,
        }
    else:
        goals_info["steps"] = {"met": None, "goal": steps_goal, "actual": None}

    # Daily sleep goal (average sleep per day)
    sleep_goal = config.get("daily_sleep_goal", 0)
    if week_data.get("sleep_days", 0) > 0:
        sleep_actual = week_data["sleep_total"] / week_data["sleep_days"]
        goals_info["sleep"] = {
            "met": sleep_actual >= sleep_goal if sleep_goal > 0 else None,
            "goal": sleep_goal,
            "actual": sleep_actual,
        }
    else:
        goals_info["sleep"] = {"met": None, "goal": sleep_goal, "actual": None}

    # Wake up time adherence (80% threshold) - calculate using historical config
    wake_up_times = week_data.get("wake_up_times", [])
    wake_up_time_goal = config.get("wake_up_time_goal", None)

    # Calculate adherence using the helper function
    wake_adherence, wake_total = calculate_wake_up_adherence(
        wake_up_times, wake_up_time_goal
    )

    # Store adherence in week_data for display_weekly_metrics
    week_data["wake_up_adherence"] = wake_adherence
    week_data["wake_up_total"] = wake_total

    if wake_total > 0:
        adherence_rate = (wake_adherence / wake_total) * 100
        goals_info["wake_up"] = {
            "met": adherence_rate >= 80.0,
            "goal": wake_up_time_goal,
            "actual": wake_up_times,
            "adherence": f"{wake_adherence}/{wake_total}",
        }
    else:
        goals_info["wake_up"] = {
            "met": None,
            "goal": wake_up_time_goal,
            "actual": [],
            "adherence": "0/0",
        }

    return goals_info


def format_goal_text(goal_key: str, goal_info: dict, config: dict) -> str:
    """Format goal text (without emoji) for a metric line.

    Returns formatted string like "195.0 g" (without emoji).
    """
    if goal_info is None or goal_info.get("met") is None:
        return ""

    goal_value = goal_info.get("goal")

    # Format goal value based on metric type with abbreviations
    if goal_key == "sleep":
        goal_text = f"{goal_value:.1f} hrs"
    elif goal_key == "protein":
        goal_text = f"{goal_value:.1f} g"
    elif goal_key == "calories":
        goal_text = f"{int(goal_value)}"
    elif goal_key == "cardio":
        goal_text = f"{int(goal_value)} min"
    elif goal_key == "steps":
        goal_text = f"{int(goal_value)}"
    elif goal_key == "wake_up":
        # For wake up, goal_value is a time string like "05:30"
        goal_text = str(goal_value) if goal_value else "N/A"
    elif goal_key == "workouts":
        goal_text = f"{int(goal_value)} workouts"
    else:
        goal_text = str(goal_value)

    return goal_text


def format_goal_suffix(
    goal_key: str, goal_info: dict, config: dict, max_goal_width: int = 0
) -> str:
    """Format goal suffix for a metric line with aligned emoji.

    Returns formatted string like "195.0 g ✅" in green, with emoji aligned.
    """
    if goal_info is None or goal_info.get("met") is None:
        return ""

    goal_text = format_goal_text(goal_key, goal_info, config)
    if not goal_text:
        return ""

    met = goal_info.get("met")
    emoji = "✅" if met else "❌"

    # Pad goal text to max width for emoji alignment
    if max_goal_width > 0:
        goal_text_padded = goal_text.ljust(max_goal_width)
    else:
        goal_text_padded = goal_text

    goal_display = f"{goal_text_padded} {emoji}"
    return click.style(goal_display, fg="green")


def format_value_bold(value: str) -> str:
    """Format a value string in bold and yellow."""
    return click.style(value, bold=True, fg="yellow")


def pad_line_with_bold_value(
    label_part: str, bold_value: str, target_width: int
) -> str:
    """Pad a line while preserving bold formatting on the value.

    Args:
        label_part: The label part (e.g., "  Label: ")
        bold_value: The value part with bold formatting
        target_width: Target width for the entire line

    Returns:
        Padded line with bold value preserved
    """
    # Calculate the width of the unstyled parts
    unstyled_label = click.unstyle(label_part)
    unstyled_value = click.unstyle(bold_value)
    current_width = len(unstyled_label) + len(unstyled_value)

    # Calculate padding needed
    padding_needed = max(0, target_width - current_width)

    # Return the line with padding and bold value
    return f"{label_part}{bold_value}{' ' * padding_needed}"


def format_clickable_path(path: str, color: str = None, open_in_finder: bool = False) -> str:
    """Format a file path as a clickable ANSI hyperlink.

    Args:
        path: The file path to make clickable
        color: Optional color name or ANSI code (e.g., 'brown' for 130)
        open_in_finder: If True, use file:// to open in Finder; otherwise use cursor:// to open in Cursor

    Returns:
        ANSI-formatted clickable path string
    """
    if open_in_finder:
        file_url = f"file://{path}"
    else:
        file_url = f"cursor://file{path}"

    if color == "brown":
        # Use 256-color brown
        return f"\033[38;5;130m\033]8;;{file_url}\033\\{path}\033]8;;\033\\\033[0m"
    elif color:
        # Use click.style for standard colors
        return (
            f"\033]8;;{file_url}\033\\{click.style(str(path), fg=color)}\033]8;;\033\\"
        )
    else:
        return f"\033]8;;{file_url}\033\\{path}\033]8;;\033\\"


def format_metric_line(
    label: str,
    value: str,
    label_width: int,
    goal_info: dict = None,
    goal_key: str = None,
    config: dict = None,
    goal_column: int = 0,
    max_goal_width: int = 0,
    indent: int = 2,
) -> str:
    """Format a metric line with optional goal suffix.

    Args:
        label: The label text (without indent)
        value: The value to display (will be bolded)
        label_width: Width for the label column (including indent)
        goal_info: Goal info dict with 'met', 'goal', 'actual' keys
        goal_key: Key for goal formatting (e.g., 'sleep', 'protein')
        config: Config dict for goal formatting
        goal_column: Column position for goal alignment
        max_goal_width: Max width for goal text alignment
        indent: Number of spaces to indent (default 2)

    Returns:
        Formatted line string
    """
    indent_str = " " * indent
    padded_label = f"{indent_str}{label}".ljust(label_width)
    label_with_colon = f"{padded_label}: "
    bold_value = format_value_bold(value)

    if goal_info and goal_info.get("met") is not None and goal_key and config:
        goal_suffix = format_goal_suffix(goal_key, goal_info, config, max_goal_width)
        padded_line = pad_line_with_bold_value(
            label_with_colon, bold_value, goal_column
        )
        return f"{padded_line}{goal_suffix}"
    else:
        return f"{label_with_colon}{bold_value}"


def echo_metric_line(
    label: str,
    value: str,
    label_width: int,
    goal_info: dict = None,
    goal_key: str = None,
    config: dict = None,
    goal_column: int = 0,
    max_goal_width: int = 0,
    indent: int = 2,
) -> None:
    """Echo a formatted metric line with optional goal suffix.

    Args:
        label: The label text (without indent)
        value: The value to display (will be bolded)
        label_width: Width for the label column (including indent)
        goal_info: Goal info dict with 'met', 'goal', 'actual' keys
        goal_key: Key for goal formatting (e.g., 'sleep', 'protein')
        config: Config dict for goal formatting
        goal_column: Column position for goal alignment
        max_goal_width: Max width for goal text alignment
        indent: Number of spaces to indent (default 2)
    """
    line = format_metric_line(
        label,
        value,
        label_width,
        goal_info,
        goal_key,
        config,
        goal_column,
        max_goal_width,
        indent,
    )
    click.echo(line)


def prompt_with_echo(
    prompt_text: str,
    type_converter=None,
    default=None,
    choices=None,
    style_func=None,
    suffix: str = "",
) -> any:
    """Prompt user for input and echo their response.

    Args:
        prompt_text: The question to ask (will be styled)
        type_converter: Type for click.prompt (e.g., int, float)
        default: Default value
        choices: List of valid choices
        style_func: Function to style the prompt (default: style_question)
        suffix: Suffix to add after echoed response

    Returns:
        The user's input value
    """
    if style_func is None:
        style_func = style_question

    styled_prompt = style_func(prompt_text)

    if choices:
        value = click.prompt(
            styled_prompt,
            type=click.Choice(choices, case_sensitive=False),
            default=default,
            prompt_suffix="\n",
        )
    elif type_converter:
        value = click.prompt(
            styled_prompt, type=type_converter, default=default, prompt_suffix="\n"
        )
    else:
        value = click.prompt(styled_prompt, default=default, prompt_suffix="\n")

    # Echo the response
    response_text = str(value) + suffix
    click.echo(f"  {style_response(response_text)}\n")

    return value


def aligned_prompt(
    label: str,
    label_width: int,
    type_converter=None,
    default=None,
    show_default: bool = True,
    style_func=None,
) -> any:
    """Prompt with aligned colon and bold answer display.

    After user enters value, rewrites the line with bold formatting.

    Args:
        label: The label text (without colon)
        label_width: Fixed width for label (colon will be at this position)
        type_converter: Type for click.prompt (e.g., int, float)
        default: Default value
        show_default: Whether to show default in prompt
        style_func: Function to style the label (default: style_question)

    Returns:
        The user's input value
    """
    if style_func is None:
        style_func = style_question

    # Pad label to fixed width
    padded_label = label.ljust(label_width)

    # Build the prompt - click adds ": " after the text
    styled_label = style_func(padded_label)

    if type_converter:
        value = click.prompt(
            styled_label,
            type=type_converter,
            default=default,
            show_default=show_default,
        )
    else:
        value = click.prompt(styled_label, default=default, show_default=show_default)

    # Move cursor up one line and clear it, then reprint with bold value
    # \033[A = move up, \033[K = clear to end of line
    click.echo(
        f"\033[A\033[K{style_func(padded_label)}: {click.style(str(value), bold=True, fg='yellow')}"
    )

    return value


def calculate_max_label_width(labels: list, extra: int = 1) -> int:
    """Calculate the maximum width needed for a list of labels.

    Args:
        labels: List of label strings
        extra: Extra padding to add (default 1 for colon)

    Returns:
        Maximum width for labels
    """
    return max(len(label) for label in labels) + extra


def build_sample_metric_line(
    label: str, value: str, label_width: int, indent: int = 2
) -> str:
    """Build a sample metric line for width calculation (no styling).

    Args:
        label: The label text
        value: The value text
        label_width: Width for the label column
        indent: Number of spaces to indent

    Returns:
        Plain text line for width measurement
    """
    indent_str = " " * indent
    padded_label = f"{indent_str}{label}".ljust(label_width)
    return f"{padded_label}: {value}"


def display_weekly_metrics(week_data: dict, goals_info: dict, config: dict, config_path: str = None, verbose: bool = False) -> None:
    """Display all metrics for a week with aligned goals.

    Args:
        week_data: Week data dict with totals and counts
        goals_info: Goals info dict from check_goals_for_week
        config: Config dict for goal formatting
        config_path: Path to the config file used for this week's goals
        verbose: Whether to show additional info like config path
    """
    weekly_labels = [
        "Sessions recorded",
        "Workouts hit",
        "Average sleep",
        "Average protein",
        "Average calories",
        "Total cardio",
        "Average steps",
        "Wake up times",
        "Wake up adherence",
    ]
    max_weekly_label_width = max(len(label) for label in weekly_labels)
    weekly_label_width = 2 + max_weekly_label_width + 1

    # Build sample lines for width calculation
    session_count = week_data.get("session_count", 0)
    workouts_count = week_data.get("workout_count", 0)

    sample_lines = [
        build_sample_metric_line(
            "Sessions recorded", f"{session_count}/7", weekly_label_width
        ),
        build_sample_metric_line(
            "Workouts hit", str(workouts_count), weekly_label_width
        ),
    ]

    if week_data.get("sleep_days", 0) > 0:
        avg_sleep = week_data["sleep_total"] / week_data["sleep_days"]
        sample_lines.append(
            build_sample_metric_line(
                "Average sleep", f"{avg_sleep:.1f} hrs", weekly_label_width
            )
        )

    if week_data.get("protein_days", 0) > 0:
        avg_protein = week_data["protein_total"] / week_data["protein_days"]
        sample_lines.append(
            build_sample_metric_line(
                "Average protein", f"{avg_protein:.1f} g", weekly_label_width
            )
        )

    if week_data.get("calories_days", 0) > 0:
        avg_calories = week_data["calories_total"] / week_data["calories_days"]
        sample_lines.append(
            build_sample_metric_line(
                "Average calories", f"{avg_calories:.0f}", weekly_label_width
            )
        )

    cardio_total = week_data.get("cardio_total_minutes", 0)
    sample_lines.append(
        build_sample_metric_line(
            "Total cardio", f"{cardio_total} min", weekly_label_width
        )
    )

    if week_data.get("steps_days", 0) > 0:
        avg_steps = week_data["steps_total"] / week_data["steps_days"]
        sample_lines.append(
            build_sample_metric_line(
                "Average steps", f"{avg_steps:.0f}", weekly_label_width
            )
        )

    wake_up_times = week_data.get("wake_up_times", [])
    wake_total = week_data.get("wake_up_total", 0)
    if wake_total > 0:
        wake_times_str = ", ".join(wake_up_times)
        sample_lines.append(
            build_sample_metric_line(
                "Wake up times", wake_times_str, weekly_label_width
            )
        )
        wake_adherence = week_data.get("wake_up_adherence", 0)
        sample_lines.append(
            build_sample_metric_line(
                "Wake up adherence",
                f"{wake_adherence}/{wake_total}",
                weekly_label_width,
            )
        )

    max_line_width = max(len(line) for line in sample_lines) if sample_lines else 0
    goal_column = max_line_width + 3

    # Calculate max goal text width for emoji alignment
    goal_texts = []
    for key in [
        "workouts",
        "sleep",
        "protein",
        "calories",
        "cardio",
        "steps",
        "wake_up",
    ]:
        info = goals_info.get(key, {})
        if info.get("met") is not None:
            goal_texts.append(format_goal_text(key, info, config))
    max_goal_width = max(len(text) for text in goal_texts) if goal_texts else 0

    # Display metrics
    echo_metric_line("Sessions recorded", f"{session_count}/7", weekly_label_width)

    echo_metric_line(
        "Workouts hit",
        str(workouts_count),
        weekly_label_width,
        goals_info.get("workouts"),
        "workouts",
        config,
        goal_column,
        max_goal_width,
    )

    if week_data.get("sleep_days", 0) > 0:
        avg_sleep = week_data["sleep_total"] / week_data["sleep_days"]
        echo_metric_line(
            "Average sleep",
            f"{avg_sleep:.1f} hrs",
            weekly_label_width,
            goals_info.get("sleep"),
            "sleep",
            config,
            goal_column,
            max_goal_width,
        )

    if week_data.get("protein_days", 0) > 0:
        avg_protein = week_data["protein_total"] / week_data["protein_days"]
        echo_metric_line(
            "Average protein",
            f"{avg_protein:.1f} g",
            weekly_label_width,
            goals_info.get("protein"),
            "protein",
            config,
            goal_column,
            max_goal_width,
        )

    if week_data.get("calories_days", 0) > 0:
        avg_calories = week_data["calories_total"] / week_data["calories_days"]
        echo_metric_line(
            "Average calories",
            f"{avg_calories:.0f}",
            weekly_label_width,
            goals_info.get("calories"),
            "calories",
            config,
            goal_column,
            max_goal_width,
        )

    echo_metric_line(
        "Total cardio",
        f"{cardio_total} min",
        weekly_label_width,
        goals_info.get("cardio"),
        "cardio",
        config,
        goal_column,
        max_goal_width,
    )

    if week_data.get("steps_days", 0) > 0:
        avg_steps = week_data["steps_total"] / week_data["steps_days"]
        echo_metric_line(
            "Average steps",
            f"{avg_steps:.0f}",
            weekly_label_width,
            goals_info.get("steps"),
            "steps",
            config,
            goal_column,
            max_goal_width,
        )

    if wake_total > 0:
        wake_times_str = ", ".join(wake_up_times)
        echo_metric_line("Wake up times", wake_times_str, weekly_label_width)

        wake_adherence = week_data.get("wake_up_adherence", 0)
        echo_metric_line(
            "Wake up adherence",
            f"{wake_adherence}/{wake_total}",
            weekly_label_width,
            goals_info.get("wake_up"),
            "wake_up",
            config,
            goal_column,
            max_goal_width,
        )
    else:
        echo_metric_line("Wake up times", "No data", weekly_label_width)

    # Show config file path for this week's goals (verbose only)
    if verbose and config_path:
        clickable_config = format_clickable_path(str(config_path), "brown")
        click.echo(f"  {style_brown('Goals Config:')} {clickable_config}")


def display_file_locations(data_path, data_dir) -> None:
    """Display clickable file location links.

    Args:
        data_path: Path to data file
        data_dir: Path to data directory
    """
    click.echo(f"\n{style_heading('=== File Locations ===')}\n")

    file_labels = ["Check in data", "Folder"]
    max_width = calculate_max_label_width(file_labels)

    # Check in data opens in Cursor, Folder opens in Finder
    padded_label = "Check-In Log:".ljust(max_width)
    clickable_path = format_clickable_path(str(data_path), "brown")
    click.echo(f"{style_brown(padded_label)} {clickable_path}")

    padded_label = "Data Folder:".ljust(max_width)
    clickable_path = format_clickable_path(str(data_dir), "brown", open_in_finder=True)
    click.echo(f"{style_brown(padded_label)} {clickable_path}")


@click.command()
@click.option("-v", "--verbose", is_flag=True, help="Show config file locations.")
@click.pass_context
def init_command(ctx, verbose):
    """Set up your weekly goals"""
    # Check if config already exists
    existing_config = load_config()
    if existing_config:
        click.echo(f"{style_heading('Beware! Users of this CLI get Too Buff!')}")
        click.echo(f"\n{style_success('You are already set up! Go on and get too buff 💪🏽')}")

        # Display current goals by invoking goals_command
        ctx.invoke(goals_command, verbose=verbose, update=False)
        return

    click.echo(
        f"{style_heading('Beware! Users of this CLI get Too Buff!')} \n Let's set up your weekly goals...\n"
    )

    config = {}

    # Label width for aligned prompts
    LABEL_WIDTH = 22

    # Workouts per week
    config["workouts_per_week"] = aligned_prompt(
        "Workouts per week", LABEL_WIDTH, type_converter=int, default=4, style_func=style_question_purple
    )

    # Wake up time goal
    wake_time_str = aligned_prompt(
        "Wake up time (HH:MM)", LABEL_WIDTH, default="06:30", style_func=style_question_purple
    )
    config["wake_up_time_goal"] = parse_time(wake_time_str).strftime("%H:%M")

    # Daily sleep goal (in hours)
    config["daily_sleep_goal"] = aligned_prompt(
        "Sleep goal (hours)", LABEL_WIDTH, type_converter=float, default=8.0, style_func=style_question_purple
    )

    # Weekly cardio time goal (in minutes)
    config["weekly_cardio_time_goal"] = aligned_prompt(
        "Cardio goal (minutes)", LABEL_WIDTH, type_converter=int, default=150, style_func=style_question_purple
    )

    # Weekly average protein goal (in grams)
    config["weekly_protein_goal"] = aligned_prompt(
        "Protein goal (grams)", LABEL_WIDTH, type_converter=float, default=150.0, style_func=style_question_purple
    )

    # Weekly average calorie goal
    config["weekly_calorie_goal"] = aligned_prompt(
        "Calorie goal", LABEL_WIDTH, type_converter=int, default=2500, style_func=style_question_purple
    )

    # Weekly average steps goal
    config["weekly_steps_goal"] = aligned_prompt(
        "Steps goal", LABEL_WIDTH, type_converter=int, default=10000, style_func=style_question_purple
    )

    save_config(config, create_timestamped=True)
    click.echo(f"\n{style_success('✓ Configuration saved successfully!')}")

    # Show the latest timestamped config file
    if verbose:
        latest_config_path = get_config_path_for_date(datetime.now())
        clickable_config = format_clickable_path(str(latest_config_path), "brown")
        click.echo(f"{style_brown('Goals Config:')} {clickable_config}")


@click.command()
@click.option("--backfill", is_flag=True, help="Add a check-in for a previous day.")
@click.option("--dry-run", is_flag=True, help="Preview check-in without saving to data file.")
def checkin_command(backfill, dry_run):
    """Start interactive mode to record your daily check-in values."""
    config = load_config()
    if not config:
        click.echo(
            style_error(
                "Error: Configuration not found. Please run 'toobuff init' first."
            )
        )
        sys.exit(1)

    data = load_data()

    # Get Eastern Time timezone
    et_tz = pytz.timezone("US/Eastern")

    # Label width for aligned prompts - must accommodate longest label "Did you do cardio today?"
    LABEL_WIDTH = 24

    # Handle backfill mode
    if backfill:
        date_str = aligned_prompt("Backfill date (Use DD, MM-DD, or YYYY-MM-DD)", LABEL_WIDTH, default="", show_default=False)
        if not date_str:
            click.echo(style_error("Date is required for backfill. Use DD, MM-DD, or YYYY-MM-DD format."))
            sys.exit(1)

        try:
            backfill_date = parse_backfill_date(date_str)
            # Make timezone-aware (5pm ET)
            checkin_timestamp = et_tz.localize(backfill_date)
            click.echo(f"\n{style_heading('Daily Check-in (Backfill)')}")
            timestamp_str = checkin_timestamp.strftime("%Y-%m-%d at %I:%M %p %Z")
            click.echo(
                f"  {style_timestamp('Recording check-in for:')} {style_timestamp(timestamp_str)}\n"
            )
        except click.BadParameter as e:
            click.echo(style_error(str(e)))
            sys.exit(1)
    else:
        # Get current time in ET
        checkin_timestamp = datetime.now(et_tz)
        click.echo(f"\n{style_heading('Daily Check-in')}")
        timestamp_str = checkin_timestamp.strftime("%Y-%m-%d at %I:%M %p %Z")
        click.echo(
            f"  {style_timestamp('Recording check-in for:')} {style_timestamp(timestamp_str)}\n"
        )

    checkin = {
        "timestamp": checkin_timestamp.isoformat(),
    }

    # Wake up time
    wake_time_str = aligned_prompt("Wake up time", LABEL_WIDTH, default="05:30")
    checkin["wake_up_time"] = parse_time(wake_time_str).strftime("%H:%M")

    # Sleep duration (in hours)
    sleep_hours = aligned_prompt(
        "Sleep (hours)", LABEL_WIDTH, type_converter=float, default=8.0
    )
    checkin["sleep_hours"] = sleep_hours

    # Workout information
    did_workout = click.confirm(
        style_question("Did you work out today?".ljust(LABEL_WIDTH)), default=True
    )
    # Rewrite line with bold answer
    answer = "Yes" if did_workout else "No"
    click.echo(
        f"\033[A\033[K{style_question('Did you work out today?'.ljust(LABEL_WIDTH))}: {click.style(answer, bold=True, fg='yellow')}"
    )

    if did_workout:
        # Combined week and day question
        while True:
            block_str = aligned_prompt("Block day", LABEL_WIDTH, default="w1d1")
            try:
                workout_week, workout_day = parse_block_day(block_str)
                break
            except click.BadParameter as e:
                click.echo(style_error(str(e)))

        primary_lifts = {}
        lift_options = ["squat", "bench", "deadlift"]

        click.echo(
            style_question("Enter lifts (squat/bench/deadlift). Press Enter when done.")
        )
        while True:
            lift = aligned_prompt("  Lift", LABEL_WIDTH, default="", show_default=False)
            lift = lift.lower().strip()

            # Empty input means done
            if not lift:
                if not primary_lifts:
                    click.echo("  Please add at least one lift.")
                    continue
                break

            if lift not in lift_options:
                click.echo(f"  Invalid lift. Choose from: {', '.join(lift_options)}")
                continue

            # Keep prompting until valid weight format is entered
            while True:
                weights_str = aligned_prompt(
                    f"  {lift.capitalize()} (e.g. 175x5)", LABEL_WIDTH, default="", show_default=False
                )

                if not weights_str:
                    click.echo("  No weight entered. Skipping this lift.")
                    break

                try:
                    weights_sets = parse_weights(weights_str)
                    if weights_sets:
                        primary_lifts[lift] = {
                            "weight": weights_sets[0]["weight"],
                            "reps": weights_sets[0]["reps"],
                        }
                        break
                    else:
                        click.echo("  Invalid format. Use WEIGHTxREPS (e.g., 175x5 or 80kgx5)")
                except click.BadParameter:
                    click.echo("  Invalid format. Use WEIGHTxREPS (e.g., 175x5 or 80kgx5)")

        checkin["workout"] = {
            "week": workout_week,
            "day": workout_day,
            "primary_lifts": primary_lifts,
        }
    else:
        checkin["workout"] = None

    # Cardio
    did_cardio = click.confirm(
        style_question("Did you do cardio today?".ljust(LABEL_WIDTH)), default=True
    )
    # Rewrite line with bold answer
    cardio_answer = "Yes" if did_cardio else "No"
    click.echo(
        f"\033[A\033[K{style_question('Did you do cardio today?'.ljust(LABEL_WIDTH))}: {click.style(cardio_answer, bold=True, fg='yellow')}"
    )

    if did_cardio:
        cardio_medium = aligned_prompt(
            "Cardio medium", LABEL_WIDTH, default="incline treadmill"
        )
        cardio_duration = aligned_prompt(
            "Cardio (minutes)", LABEL_WIDTH, type_converter=int, default=15
        )
        cardio_zone = aligned_prompt(
            "Cardio zone", LABEL_WIDTH, type_converter=int, default=3
        )

        checkin["cardio"] = {
            "medium": cardio_medium,
            "duration_minutes": cardio_duration,
            "zone": cardio_zone,
        }
    else:
        checkin["cardio"] = {}

    # Protein
    protein = aligned_prompt(
        "Protein (g)", LABEL_WIDTH, type_converter=float, default=0.0
    )
    checkin["protein"] = protein

    # Calories
    calories = aligned_prompt("Calories", LABEL_WIDTH, type_converter=int, default=0)
    checkin["calories"] = calories

    # Steps
    steps = aligned_prompt("Steps", LABEL_WIDTH, type_converter=int, default=0)
    checkin["steps"] = steps

    # Add checkin to data
    if dry_run:
        click.echo(f"\n{click.style('🔍 DRY RUN - Check-in NOT saved:', fg='cyan', bold=True)}")
        import json
        click.echo(click.style(json.dumps(checkin, indent=2, default=str), fg='cyan'))
    else:
        if "checkins" not in data:
            data["checkins"] = []
        data["checkins"].append(checkin)
        save_data(data)
        click.echo(f"\n{style_success('✓ Check-in recorded successfully!')}")


@click.command()
@click.option(
    "-v", "--verbose", is_flag=True, help="Show data file location and directory paths."
)
def data_command(verbose):
    """Print a summary of the data you've recorded so far."""
    config = load_config()
    if not config:
        click.echo(
            style_error(
                "Error: Configuration not found. Please run 'toobuff init' first."
            )
        )
        sys.exit(1)

    data = load_data()

    if not data.get("checkins"):
        click.echo(
            style_error(
                "No check-ins recorded yet. Use 'toobuff checkin' to record your first check-in."
            )
        )
        if verbose:
            display_file_locations(get_data_path(), get_config_path(), get_data_dir())
        return

    checkins = data["checkins"]

    # Calculate weekly summaries at runtime
    weeks = calculate_weekly_summaries(checkins)

    # Pre-calculate wake up adherence for each week using historical configs
    # This is needed for the overall summary before weekly details are displayed
    for week_id, week_data in weeks.items():
        week_config = load_config_for_date(week_data["week_start"])
        if week_config is None:
            week_config = config

        wake_up_times = week_data.get("wake_up_times", [])
        wake_up_time_goal = week_config.get("wake_up_time_goal", None)

        adherence, total = calculate_wake_up_adherence(wake_up_times, wake_up_time_goal)
        week_data["wake_up_adherence"] = adherence
        week_data["wake_up_total"] = total

    click.echo(f"\n{style_heading('=== Data Summary ===')}\n")

    # Find the longest label for alignment (including colon)
    summary_labels = [
        "Days recorded",
        "Average sleep time",
        "Sleep balance",
        "Average workouts per week",
        "Average wake time",
        "Wake up time adherence",
        "Workouts goal",
        "Cardio goal",
        "Protein goal",
        "Calories goal",
        "Steps goal",
        "Wake up goal",
    ]
    max_label_width = max(len(label) for label in summary_labels) + 1  # +1 for colon

    # Days recorded
    click.echo(format_label_value("Days recorded", str(len(checkins)), max_label_width))

    # Average sleep time
    sleep_total = sum(c.get("sleep_hours", 0) for c in checkins)
    sleep_count = sum(1 for c in checkins if c.get("sleep_hours"))
    if sleep_count > 0:
        avg_sleep = sleep_total / sleep_count
        click.echo(
            format_label_value(
                "Average sleep time", f"{avg_sleep:.1f} hours", max_label_width
            )
        )
    else:
        click.echo(format_label_value("Average sleep time", "N/A", max_label_width))

    # Sleep balance (sleep goal * days - actual sleep * days)
    sleep_goal = config.get("daily_sleep_goal", 0)
    if sleep_goal > 0 and sleep_count > 0:
        days_recorded = len(checkins)
        goal_sleep_total = sleep_goal * days_recorded
        actual_sleep_total = sleep_total
        sleep_balance = actual_sleep_total - goal_sleep_total

        # Format sleep balance: green if surplus (positive), red if deficit (negative)
        if sleep_balance >= 0:
            balance_str = f"+{sleep_balance:.1f} hrs"
            balance_display = click.style(balance_str, fg="green", bold=True)
        else:
            balance_str = f"{sleep_balance:.1f} hrs"
            balance_display = click.style(balance_str, fg="red", bold=True)

        # Format the label with proper width so colon aligns with other labels
        stripped_label = "Sleep balance"
        padded_label = stripped_label.ljust(max_label_width)
        click.echo(f"{padded_label}: {balance_display}")
    else:
        click.echo(format_label_value("Sleep balance", "N/A", max_label_width))

    # Average workouts per week
    workouts = [c for c in checkins if c.get("workout")]
    if weeks:
        total_weeks = len(weeks)
        if total_weeks > 0:
            avg_workouts = len(workouts) / total_weeks
            click.echo(
                format_label_value(
                    "Average workouts per week",
                    str(int(round(avg_workouts))),
                    max_label_width,
                )
            )
        else:
            click.echo(
                format_label_value("Average workouts per week", "N/A", max_label_width)
            )
    else:
        click.echo(
            format_label_value("Average workouts per week", "N/A", max_label_width)
        )

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
        click.echo(
            format_label_value(
                "Average wake time", f"{avg_hour:02d}:{avg_min:02d}", max_label_width
            )
        )
    else:
        click.echo(format_label_value("Average wake time", "N/A", max_label_width))

    # Days adhered to wake up time
    if weeks:
        total_adherence = 0
        total_days = 0
        for week_data in weeks.values():
            total_adherence += week_data.get("wake_up_adherence", 0)
            total_days += week_data.get("wake_up_total", 0)

        if total_days > 0:
            adherence_rate = (total_adherence / total_days) * 100
            click.echo(
                format_label_value(
                    "Wake up time adherence",
                    f"{total_adherence}/{total_days} days ({adherence_rate:.1f}%)",
                    max_label_width,
                )
            )
        else:
            click.echo(
                format_label_value("Wake up time adherence", "N/A", max_label_width)
            )
    else:
        click.echo(format_label_value("Wake up time adherence", "N/A", max_label_width))

    # Weekly summaries
    if weeks:
        click.echo(f"\n{style_heading('=== Weekly Summaries ===')}")
        current_week_id = get_week_number(datetime.now())

        for week_id in sorted(weeks.keys()):
            week_data = weeks[week_id]
            year = week_data["year"]
            week = week_data["week"]
            week_start = week_data["week_start"]
            week_end = week_data["week_end"]

            # Count sessions for this week and add to week_data
            week_checkins = [
                c
                for c in checkins
                if get_week_number(datetime.fromisoformat(c["timestamp"])) == week_id
            ]
            week_data["session_count"] = len(week_checkins)

            # Format and display week header
            # Green if all 7 days recorded, orange otherwise
            week_header = format_week_header(year, week, week_start, week_end)
            if week_data["session_count"] >= 7:
                week_header_styled = click.style(week_header, fg="green", bold=True)
            else:
                week_header_styled = f"\033[38;5;208m\033[1m{week_header}\033[0m"
            click.echo(f"\n{week_header_styled}")

            # Load the config that was active during this week for historical goal comparison
            # Use week_end to get the latest config created during or before this week
            week_config = load_config_for_date(week_end)
            week_config_path = get_config_path_for_date(week_end)
            if week_config is None:
                week_config = config  # Fallback to current config
                week_config_path = get_config_path()

            # Check goals for this week using the historical config
            goals_info = check_goals_for_week(week_data, week_checkins, week_config)

            # Display all metrics using helper function
            display_weekly_metrics(week_data, goals_info, week_config, week_config_path, verbose)

    if verbose:
        display_file_locations(get_data_path(), get_data_dir())


@click.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show config file location and directory paths.",
)
@click.option("--update", is_flag=True, help="Update your weekly goals.")
def goals_command(verbose, update):
    """Print your weekly goals."""
    config = load_config()
    if not config:
        click.echo(
            style_error(
                "Error: Configuration not found. Please run 'toobuff init' first."
            )
        )
        sys.exit(1)

    # Handle update mode
    if update:
        click.echo(f"{style_heading('Update Your Weekly Goals')}\n")

        # Label width for aligned prompts (same as init)
        LABEL_WIDTH = 22

        # Workouts per week
        config["workouts_per_week"] = aligned_prompt(
            "Workouts per week", LABEL_WIDTH, type_converter=int,
            default=config.get("workouts_per_week", 4), style_func=style_question_purple
        )

        # Wake up time goal
        wake_time_str = aligned_prompt(
            "Wake up time (HH:MM)", LABEL_WIDTH,
            default=config.get("wake_up_time_goal", "06:30"), style_func=style_question_purple
        )
        config["wake_up_time_goal"] = parse_time(wake_time_str).strftime("%H:%M")

        # Daily sleep goal (in hours)
        config["daily_sleep_goal"] = aligned_prompt(
            "Sleep goal (hours)", LABEL_WIDTH, type_converter=float,
            default=config.get("daily_sleep_goal", 8.0), style_func=style_question_purple
        )

        # Weekly cardio time goal (in minutes)
        config["weekly_cardio_time_goal"] = aligned_prompt(
            "Cardio goal (minutes)", LABEL_WIDTH, type_converter=int,
            default=config.get("weekly_cardio_time_goal", 150), style_func=style_question_purple
        )

        # Weekly average protein goal (in grams)
        config["weekly_protein_goal"] = aligned_prompt(
            "Protein goal (grams)", LABEL_WIDTH, type_converter=float,
            default=config.get("weekly_protein_goal", 150.0), style_func=style_question_purple
        )

        # Weekly average calorie goal
        config["weekly_calorie_goal"] = aligned_prompt(
            "Calorie goal", LABEL_WIDTH, type_converter=int,
            default=config.get("weekly_calorie_goal", 2500), style_func=style_question_purple
        )

        # Weekly average steps goal
        config["weekly_steps_goal"] = aligned_prompt(
            "Steps goal", LABEL_WIDTH, type_converter=int,
            default=config.get("weekly_steps_goal", 10000), style_func=style_question_purple
        )

        save_config(config, create_timestamped=True)
        click.echo(f"\n{style_success('✓ Goals updated successfully!')}")

        # Show the latest timestamped config file
        latest_config_path = get_config_path_for_date(datetime.now())
        clickable_config = format_clickable_path(str(latest_config_path), "brown")
        click.echo(f"{style_brown('Goals Config:')} {clickable_config}")
        return

    # Display mode
    click.echo(f"\n{style_heading('=== Your Weekly Goals ===')}")

    # Show when goals were set (only in verbose mode)
    effective_from = config.get("effective_from")
    if effective_from and verbose:
        try:
            dt = datetime.fromisoformat(effective_from)
            day = dt.day
            suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
            formatted_date = dt.strftime(f"%b {day}{suffix}, %Y at %-I:%M %p")
            click.echo(f"  {style_brown(f'set on {formatted_date}')}")
        except:
            pass
    click.echo()

    # Display all goals: (label, config_key, unit)
    goals = [
        ("Workouts", "workouts_per_week", ""),
        ("Wake-Up", "wake_up_time_goal", ""),
        ("Sleep", "daily_sleep_goal", " hours"),
        ("Cardio", "weekly_cardio_time_goal", " minutes"),
        ("Protein", "weekly_protein_goal", " g"),
        ("Calories", "weekly_calorie_goal", ""),
        ("Steps", "weekly_steps_goal", ""),
    ]

    max_label_width = max(len(label) for label, _, _ in goals) + 1  # +1 for colon

    for label, config_key, unit in goals:
        value = config.get(config_key, "N/A")
        click.echo(format_label_value(label, f"{value}{unit}", max_label_width))

    # Add comment about updating goals
    click.echo(
        f"\n{click.style('Not buff enough yet? Run ', fg='bright_black')}{style_heading('toobuff goals --update')}{click.style(' to update your goals!', fg='bright_black')}"
    )

    if verbose:
        # Get the latest timestamped config file
        latest_config_path = get_config_path_for_date(datetime.now())
        config_dir = get_config_dir()

        clickable_config = format_clickable_path(str(latest_config_path), "brown")
        clickable_dir = format_clickable_path(str(config_dir), "brown", open_in_finder=True)

        click.echo(f"\n{style_brown('Goals Config:')} {clickable_config}")
        click.echo(f"{style_brown('Config Folder:')} {clickable_dir}")
