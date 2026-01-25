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
```

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

## Background and Motivation

This year I got an amazing christmas gift from my sister: the book ["How to Make Friends When You're Too Buff: tricks to speaking to puny strangers and not making them feel pathetic"](https://www.amazon.com/Speaking-Strangers-Pathetic-Elephant-Calendar/dp/B096CKK9DX). It's just a weekly workout log and planner, but the gag title put a smile on my face and probably yours too. 

I've been logging into it daily which has been quite helpful to ensure I track my weekly goals in nutrition, sleep, weightlifting frequency, steps and cardio time. 

While it's been helpful, it's easy to see that the best tool for the numeric aspects of the goals were computers and code over pen and paper. This is my attempt to formalize the log into a CLI tool that will help me see bigger picture things easily like: 
 - how my bench, squat or deadlift weight has tracked over time
 - how my sleep debt stacks up (total actual amount slept vs. goal sleep hours) over many months
 - weekly summaries sent to email that stack up how you fared against your goals (TBA) 

## Data Storage

All data is stored locally on your machine. Use `toobuff datafile` to see where your data is stored.

## License

MIT

