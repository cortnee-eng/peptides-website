"""
Chief of Staff — Daily Standup from Trello

Reads the PeptideRevealed Distribution board and generates a daily briefing:
- What's overdue
- What's due today
- What's due this week
- What was completed recently
- Suggested focus for today

Usage: python tools/trello_standup.py
"""

import os
import requests
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TRELLO_API_KEY")
TOKEN = os.getenv("TRELLO_TOKEN")
BASE = "https://api.trello.com/1"

def get(endpoint, **params):
    params.update({"key": API_KEY, "token": TOKEN})
    r = requests.get(f"{BASE}/{endpoint}", params=params)
    r.raise_for_status()
    return r.json()

def find_board():
    boards = get("members/me/boards", fields="name,shortUrl")
    for b in boards:
        if "Distribution" in b["name"] and "PeptideRevealed" in b["name"]:
            return b
    raise ValueError("Could not find PeptideRevealed Distribution board")

def get_lists(board_id):
    return get(f"boards/{board_id}/lists", fields="name")

def get_cards(board_id):
    return get(f"boards/{board_id}/cards",
               fields="name,desc,due,dueComplete,idList,labels,dateLastActivity",
               checklists="all")

def get_checklist_progress(card):
    if not card.get("checklists"):
        return None
    total = 0
    complete = 0
    for cl in card["checklists"]:
        for item in cl.get("checkItems", []):
            total += 1
            if item["state"] == "complete":
                complete += 1
    if total == 0:
        return None
    return (complete, total)

def parse_due(due_str):
    if not due_str:
        return None
    return datetime.fromisoformat(due_str.replace("Z", "+00:00"))

def format_labels(card):
    names = [l["name"] for l in card.get("labels", []) if l.get("name")]
    return f" [{', '.join(names)}]" if names else ""

def main():
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    week_end = today_start.replace(day=today_start.day + (6 - today_start.weekday()))

    board = find_board()
    board_id = board["id"]
    lists = {l["id"]: l["name"] for l in get_lists(board_id)}
    cards = get_cards(board_id)

    done_list_id = None
    in_progress_list_id = None
    for lid, lname in lists.items():
        if lname == "Done":
            done_list_id = lid
        if lname == "In Progress":
            in_progress_list_id = lid

    overdue = []
    due_today = []
    due_this_week = []
    in_progress = []
    recently_done = []
    blocked = []

    for card in cards:
        list_name = lists.get(card["idList"], "Unknown")
        due = parse_due(card.get("due"))
        progress = get_checklist_progress(card)

        entry = {
            "name": card["name"],
            "labels": format_labels(card),
            "list": list_name,
            "due": due,
            "done": card.get("dueComplete", False),
            "progress": progress,
        }

        if list_name == "Blocked / Waiting":
            blocked.append(entry)
            continue

        if list_name == "Done":
            activity = datetime.fromisoformat(card["dateLastActivity"].replace("Z", "+00:00"))
            if (now - activity).days <= 3:
                recently_done.append(entry)
            continue

        if list_name == "In Progress":
            in_progress.append(entry)

        if due and not card.get("dueComplete", False):
            if due < today_start:
                overdue.append(entry)
            elif due <= today_end:
                due_today.append(entry)
            elif due <= week_end:
                due_this_week.append(entry)

    # ── Output ─────────────────────────────────────────────────
    print("=" * 60)
    print(f"  DAILY STANDUP — {now.strftime('%A, %B %d, %Y')}")
    print("=" * 60)

    if overdue:
        print(f"\n🔴 OVERDUE ({len(overdue)})")
        for e in sorted(overdue, key=lambda x: x["due"]):
            days_late = (now - e["due"]).days
            prog = f" ({e['progress'][0]}/{e['progress'][1]} done)" if e["progress"] else ""
            print(f"  - {e['name']}{e['labels']} — {days_late}d overdue{prog}")

    if due_today:
        print(f"\n🟡 DUE TODAY ({len(due_today)})")
        for e in due_today:
            prog = f" ({e['progress'][0]}/{e['progress'][1]} done)" if e["progress"] else ""
            print(f"  - {e['name']}{e['labels']}{prog}")

    if in_progress:
        print(f"\n🔵 IN PROGRESS ({len(in_progress)})")
        for e in in_progress:
            prog = f" ({e['progress'][0]}/{e['progress'][1]} done)" if e["progress"] else ""
            print(f"  - {e['name']}{e['labels']}{prog}")

    if due_this_week:
        print(f"\n📅 DUE THIS WEEK ({len(due_this_week)})")
        for e in sorted(due_this_week, key=lambda x: x["due"]):
            day_name = e["due"].strftime("%A")
            prog = f" ({e['progress'][0]}/{e['progress'][1]} done)" if e["progress"] else ""
            print(f"  - {e['name']}{e['labels']} — due {day_name}{prog}")

    if blocked:
        print(f"\n⚠️  BLOCKED ({len(blocked)})")
        for e in blocked:
            print(f"  - {e['name']}{e['labels']}")

    if recently_done:
        print(f"\n✅ RECENTLY COMPLETED ({len(recently_done)})")
        for e in recently_done:
            print(f"  - {e['name']}{e['labels']}")

    if not any([overdue, due_today, in_progress, due_this_week, blocked, recently_done]):
        print("\n  No active cards found. Board may be empty or all tasks are in Backlog.")

    # ── Today's Focus ──────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  TODAY'S FOCUS")
    print("-" * 60)

    focus_items = overdue + due_today + in_progress
    if focus_items:
        # Prioritize: overdue first, then due today, then in progress
        for i, e in enumerate(focus_items[:3], 1):
            print(f"  {i}. {e['name']}{e['labels']}")
    else:
        print("  Nothing urgent — check the weekly cards and pull something forward.")

    print()

if __name__ == "__main__":
    main()
