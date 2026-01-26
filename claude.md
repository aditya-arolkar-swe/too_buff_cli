# Claude Development Rules for Too Buff CLI

## Alignment Rules

### Colons Must Always Be in the Same Column

**Rule**: All label-value pairs in CLI output AND interactive prompts must have their colons aligned in the same column. Values are left-aligned after the colon.

**Implementation Guidelines**:

1. **Interactive Prompts (checkin command)**:
   - Use a single `LABEL_WIDTH` constant for ALL prompts in the checkin flow
   - The width must accommodate the longest label (currently "Did you work out today?" at 23 chars)
   - Use `aligned_prompt()` function which pads labels to the specified width
   - Never use different widths for different prompts - ALL must use the same `LABEL_WIDTH`

2. **Data Summary Section**: 
   - All labels in the `=== Data Summary ===` section should be padded to the same width
   - Use `format_label_value()` function with a consistent `label_width` parameter
   - For custom formatted values (e.g., sleep balance with color), manually pad the label to match

3. **Weekly Summaries Section**:
   - Labels are padded using `weekly_label_width` to ensure colons align
   - Goals displayed on the right side of metric lines use `goal_column` and `max_goal_width` for alignment

4. **Formatting Functions**:
   - `aligned_prompt(label, label_width, ...)`: For interactive prompts with aligned colons and bold answers
   - `format_label_value(label, value, label_width)`: Pads label to `label_width` so colon is always in the same column
   - Custom formatted values: Use `label.ljust(max_label_width)` to align with other labels

**Example**:
```python
# Interactive prompts - ALL use same LABEL_WIDTH
LABEL_WIDTH = 24  # Must fit longest label
wake_time = aligned_prompt("Wake up time", LABEL_WIDTH, default="05:30")
did_workout = click.confirm(style_question("Did you work out today?".ljust(LABEL_WIDTH)), default=True)

# Data summary - all use same max_label_width
click.echo(format_label_value("Days recorded", str(len(checkins)), max_label_width))
```

**Rationale**: Aligned colons create a clean, readable appearance that makes it easy to scan labels and their corresponding values.

