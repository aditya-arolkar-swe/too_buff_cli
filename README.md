<p align="center">
<img width="250" height="250" alt="too_buff_logo" src="https://github.com/user-attachments/assets/695d80df-b8b2-4ecd-9007-25e57834c4ea" />
</p>

# Too Buff CLI
Install this software if you want to get [Too Buff](https://www.amazon.com/Speaking-Strangers-Pathetic-Elephant-Calendar/dp/B096CKK9DX) 💪🏽

## Installation

Install with:

```bash
curl -fsSL https://raw.githubusercontent.com/aditya-arolkar-swe/too_buff_cli/main/install.sh | bash
```

After installation, you can use `toobuff` from anywhere:

```bash
toobuff init
toobuff checkin
toobuff data
toobuff goals
```

## Usage

### Initialize your goals

```bash
toobuff init
```

This will prompt you to set up your weekly goals:
- Workouts per week
- Wake-up time goal
- Daily sleep goal (hours)
- Weekly cardio time goal (minutes)
- Protein goal (grams)
- Calorie goal
- Step goal

### Record daily check-ins

```bash
toobuff checkin
```

This interactive command will ask you about:
- Wake-up time
- Sleep duration
- Workout details (block week/day, primary lifts with weights)
- Cardio (medium, duration, zone)
- Protein
- Calories
- Steps

**Options:**
- `--backfill` - Add a check-in for a previous day

### View data summary

```bash
toobuff data
```

Shows a summary of your recorded data including:
- Days recorded
- Average sleep time
- Sleep balance (surplus/deficit vs goal)
- Average workouts per week
- Average wake time
- Wake-up time adherence

**Weekly Summaries** show weekly results against your goals ✅/❌:
- Sessions recorded
- Workouts hit 
- Average sleep 
- Average protein 
- Average calories 
- Total cardio 
- Average steps 
- Wake-up times and adherence 

### View and update goals

```bash
toobuff goals
```

Displays your current weekly goals with the date they were set.

**Options:**
- `--update` - Interactively update your weekly goals

When you update goals, weekly summaries compare against the goals that were active during that specific week.

## Background and Motivation

This year I got an amazing christmas gift from my sister: the book ["How to Make Friends When You're Too Buff: tricks to speaking to puny strangers and not making them feel pathetic"](https://www.amazon.com/Speaking-Strangers-Pathetic-Elephant-Calendar/dp/B096CKK9DX). It's just a weekly workout log and planner, but the gag title put a smile on my face and probably yours too. 

I've been logging into it daily which has been quite helpful to ensure I track my weekly goals in nutrition, sleep, weightlifting frequency, steps and cardio time. 

While it's been helpful, it's easy to see that the best tool for the numeric aspects of the goals were computers and code over pen and paper. This is my attempt to formalize the log into a CLI tool that will help me see bigger picture things easily like: 
 - how my bench, squat or deadlift weight has tracked over time
 - how my sleep debt stacks up (total actual amount slept vs. goal sleep hours) over many months
 - weekly summaries sent to email that stack up how you fared against your goals (TBA) 

## Data Storage

All data is stored locally on your machine in the application support directory:
- **macOS**: `~/Library/Application Support/toobuff/`
- **Linux**: `~/.local/share/toobuff/`

Use `toobuff data -v` to see the exact file locations.


