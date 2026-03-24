# Chief of Staff Agent

## Objective
Keep the operator on track with the 30-day content distribution plan. Surface what matters, hide what doesn't.

## Tool
`tools/trello_standup.py` — reads the PeptideRevealed Distribution Trello board

## When to Run
- Every morning (ideal: 7-8 AM local time)
- On demand: `python tools/trello_standup.py`

## What It Does
1. Reads all cards from the Trello board
2. Categorizes by: overdue, due today, due this week, in progress, blocked, recently done
3. Checks checklist progress on each card
4. Outputs a focused standup with today's top 3 priorities

## How to Use the Output
- **Overdue items**: Either do them now or move to "Blocked / Waiting" with a reason
- **Due today**: These are your non-negotiables
- **Today's Focus**: The top 3 things to work on right now
- Move cards to "In Progress" when you start, "Done" when finished

## Scheduling (Future)
When ready to automate via `claude schedule`:
```
Run tools/trello_standup.py every morning at 7:00 AM PT.
Summarize the output and post it to [channel TBD — Slack, email, or file].
If anything is overdue by 2+ days, flag it prominently.
```

## Evolution
This agent should grow to:
1. Read the board and generate standup (now)
2. Suggest card moves based on dates and progress
3. Create next week's cards automatically from the backlog
4. Track velocity (cards completed per week) over time
