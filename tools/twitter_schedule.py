"""
Twitter/X Scheduled Posting Tool — Queue tweets and post them on a schedule.

Modes:
  1. Add a tweet to the queue:
     python tools/twitter_schedule.py --add "Your tweet text here"

  2. Add a tweet scheduled for a specific time:
     python tools/twitter_schedule.py --add "Tweet text" --at "2026-04-01 09:00"

  3. Add a tweet from an article (auto-generates options):
     python tools/twitter_schedule.py --from-article articles/bpc-157-guide.html

  4. View the current queue:
     python tools/twitter_schedule.py --list

  5. Post the next due tweet:
     python tools/twitter_schedule.py --post-next

  6. Post all due tweets:
     python tools/twitter_schedule.py --post-due

  7. Remove a queued tweet:
     python tools/twitter_schedule.py --remove 3

  8. Dry run (show what would be posted):
     python tools/twitter_schedule.py --post-due --dry-run

Queue is stored in .tmp/twitter/queue.json.

Combine with cron for true scheduling:
  */15 * * * * cd /path/to/project && python tools/twitter_schedule.py --post-due

Environment variables required in .env:
  TWITTER_API_KEY, TWITTER_API_KEY_SECRET,
  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import tweepy

QUEUE_DIR = Path(".tmp/twitter")
QUEUE_FILE = QUEUE_DIR / "queue.json"


def get_client():
    """Authenticate and return a tweepy Client (API v2)."""
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    missing = []
    if not api_key:
        missing.append("TWITTER_API_KEY")
    if not api_secret:
        missing.append("TWITTER_API_KEY_SECRET")
    if not access_token:
        missing.append("TWITTER_ACCESS_TOKEN")
    if not access_secret:
        missing.append("TWITTER_ACCESS_TOKEN_SECRET")

    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )


def load_queue():
    """Load the tweet queue from disk."""
    if not QUEUE_FILE.exists():
        return []
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_queue(queue):
    """Save the tweet queue to disk."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def add_to_queue(text, scheduled_at=None):
    """Add a tweet to the queue."""
    if len(text) > 280:
        print(f"WARNING: Tweet is {len(text)} chars (max 280).")

    queue = load_queue()

    entry = {
        "id": len(queue) + 1,
        "text": text,
        "chars": len(text),
        "status": "queued",
        "added_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_at": scheduled_at,
        "posted_at": None,
        "tweet_id": None,
    }
    queue.append(entry)
    save_queue(queue)

    time_str = f" (scheduled: {scheduled_at})" if scheduled_at else " (no specific time)"
    print(f"Added to queue (#{entry['id']}, {len(text)} chars){time_str}:")
    print(f"  {text[:100]}{'...' if len(text) > 100 else ''}")


def list_queue():
    """Display the current queue."""
    queue = load_queue()
    pending = [t for t in queue if t["status"] == "queued"]
    posted = [t for t in queue if t["status"] == "posted"]

    if not queue:
        print("Queue is empty.")
        return

    print(f"\n{'=' * 60}")
    print(f"  Tweet Queue — {len(pending)} pending, {len(posted)} posted")
    print(f"{'=' * 60}\n")

    if pending:
        print("PENDING:")
        for t in pending:
            sched = t.get("scheduled_at", "anytime")
            print(f"  #{t['id']} ({t['chars']} chars) — scheduled: {sched or 'anytime'}")
            text = t["text"].replace("\n", " ")
            if len(text) > 120:
                text = text[:117] + "..."
            print(f"    \"{text}\"")
            print()

    if posted:
        print("POSTED:")
        for t in posted[-5:]:  # Show last 5 posted
            print(f"  #{t['id']} — posted: {t.get('posted_at', '?')}")
            text = t["text"].replace("\n", " ")
            if len(text) > 80:
                text = text[:77] + "..."
            print(f"    \"{text}\"")
        if len(posted) > 5:
            print(f"  ... and {len(posted) - 5} more")


def get_due_tweets(queue):
    """Get tweets that are due to be posted."""
    now = datetime.now(timezone.utc)
    due = []

    for entry in queue:
        if entry["status"] != "queued":
            continue

        scheduled = entry.get("scheduled_at")
        if scheduled:
            try:
                sched_time = datetime.fromisoformat(scheduled)
                # Add UTC timezone if naive
                if sched_time.tzinfo is None:
                    sched_time = sched_time.replace(tzinfo=timezone.utc)
                if sched_time > now:
                    continue  # Not yet due
            except (ValueError, TypeError):
                pass  # Can't parse — treat as due

        due.append(entry)

    return due


def post_tweet(client, text, dry_run=False):
    """Post a single tweet and return the tweet ID."""
    if dry_run:
        print(f"  [DRY RUN] Would post ({len(text)} chars): {text[:100]}...")
        return "dry-run-id"

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        print(f"  Posted tweet {tweet_id} ({len(text)} chars)")
        return str(tweet_id)
    except tweepy.TweepyException as e:
        print(f"  ERROR posting tweet: {e}")
        return None


def post_next(client, dry_run=False):
    """Post the next due tweet from the queue."""
    queue = load_queue()
    due = get_due_tweets(queue)

    if not due:
        print("No tweets are due to be posted.")
        return

    entry = due[0]
    print(f"Posting queue item #{entry['id']}...")
    tweet_id = post_tweet(client, entry["text"], dry_run=dry_run)

    if tweet_id and not dry_run:
        # Update the entry in the queue
        for item in queue:
            if item["id"] == entry["id"]:
                item["status"] = "posted"
                item["posted_at"] = datetime.now(timezone.utc).isoformat()
                item["tweet_id"] = tweet_id
                break
        save_queue(queue)
        log_posted(entry["text"], tweet_id)


def post_all_due(client, dry_run=False):
    """Post all due tweets from the queue."""
    queue = load_queue()
    due = get_due_tweets(queue)

    if not due:
        print("No tweets are due to be posted.")
        return

    print(f"Posting {len(due)} due tweet(s)...\n")

    for entry in due:
        print(f"Queue item #{entry['id']}:")
        tweet_id = post_tweet(client, entry["text"], dry_run=dry_run)

        if tweet_id and not dry_run:
            for item in queue:
                if item["id"] == entry["id"]:
                    item["status"] = "posted"
                    item["posted_at"] = datetime.now(timezone.utc).isoformat()
                    item["tweet_id"] = tweet_id
                    break
            log_posted(entry["text"], tweet_id)
        print()

    if not dry_run:
        save_queue(queue)

    print(f"Done. {len(due)} tweet(s) processed.")


def remove_from_queue(item_id):
    """Remove a tweet from the queue by ID."""
    queue = load_queue()
    original_len = len(queue)
    queue = [t for t in queue if t["id"] != item_id]

    if len(queue) == original_len:
        print(f"No queue item with ID #{item_id} found.")
        return

    save_queue(queue)
    print(f"Removed item #{item_id} from queue.")


def log_posted(text, tweet_id):
    """Log posted tweets for tracking."""
    log_file = QUEUE_DIR / f"tweets_{datetime.now().strftime('%Y-%m')}.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tweet_id": tweet_id,
        "text": text,
        "mode": "scheduled",
        "chars": len(text),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def add_from_article(filepath):
    """Generate tweet options from an article and add the best one to queue."""
    # Import from the posting tool
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from twitter_post import extract_article_data, generate_tweet_options

    article = extract_article_data(filepath)
    options = generate_tweet_options(article)

    if not options:
        print(f"Could not generate tweet options from {filepath}")
        return

    print(f"Article: {article['title']}")
    print(f"Generated {len(options)} options:\n")

    for i, (label, text) in enumerate(options, 1):
        char_count = len(text.split("---")[0]) if "---" in text else len(text)
        print(f"  {i}. [{label}] ({char_count} chars)")
        preview = text.split("---")[0] if "---" in text else text
        preview = preview.replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        print(f"     {preview}")
        print()

    # Add the "short and punchy" option by default, or first available
    best = None
    for label, text in options:
        if "short" in label.lower() or "punchy" in label.lower():
            best = text
            break
    if not best:
        best = options[0][1]
        # For threads, just use the first tweet
        if "---" in best:
            best = best.split("---")[0].strip()

    add_to_queue(best)
    print("\nTo add a different option, copy the text and run:")
    print('  python tools/twitter_schedule.py --add "your chosen text"')


def main():
    parser = argparse.ArgumentParser(
        description="Queue and schedule tweets for Peptide Revealed"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", type=str, help="Add a tweet to the queue")
    group.add_argument("--from-article", type=str, help="Generate and queue a tweet from an article")
    group.add_argument("--list", action="store_true", help="View the current queue")
    group.add_argument("--post-next", action="store_true", help="Post the next due tweet")
    group.add_argument("--post-due", action="store_true", help="Post all due tweets")
    group.add_argument("--remove", type=int, help="Remove a tweet from queue by ID")

    parser.add_argument("--at", type=str, help="Schedule time (ISO format, e.g. '2026-04-01 09:00')")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without posting")

    args = parser.parse_args()

    if args.add:
        add_to_queue(args.add, scheduled_at=args.at)
    elif args.from_article:
        add_from_article(args.from_article)
    elif args.list:
        list_queue()
    elif args.remove:
        remove_from_queue(args.remove)
    elif args.post_next or args.post_due:
        client = get_client()
        if args.post_next:
            post_next(client, dry_run=args.dry_run)
        else:
            post_all_due(client, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
