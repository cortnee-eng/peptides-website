"""
Twitter/X Posting Tool — Post tweets from the Peptide Revealed account.

Modes:
  1. Post a single tweet:
     python tools/twitter_post.py --tweet "Your tweet text here"

  2. Post a thread (multiple tweets chained together):
     python tools/twitter_post.py --thread "First tweet" "Second tweet" "Third tweet"

  3. Generate and preview tweets from an article (does NOT post):
     python tools/twitter_post.py --preview articles/bpc-157-guide.html

  4. Dry run (show what would be posted without posting):
     python tools/twitter_post.py --tweet "Test tweet" --dry-run

Environment variables required in .env:
  TWITTER_API_KEY, TWITTER_API_KEY_SECRET,
  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
"""

import os
import sys
import re
import argparse
import json
from pathlib import Path
from datetime import datetime

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import tweepy


def get_client():
    """Authenticate and return a tweepy Client (API v2)."""
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    missing = []
    if not api_key: missing.append("TWITTER_API_KEY")
    if not api_secret: missing.append("TWITTER_API_KEY_SECRET")
    if not access_token: missing.append("TWITTER_ACCESS_TOKEN")
    if not access_secret: missing.append("TWITTER_ACCESS_TOKEN_SECRET")

    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Add them to your .env file.")
        sys.exit(1)

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    return client


def post_tweet(client, text, reply_to_id=None, dry_run=False):
    """Post a single tweet. Returns the tweet ID."""
    if len(text) > 280:
        print(f"WARNING: Tweet is {len(text)} chars (max 280). Truncating.")
        text = text[:277] + "..."

    if dry_run:
        print(f"[DRY RUN] Would post ({len(text)} chars):")
        print(f"  {text}")
        if reply_to_id:
            print(f"  (reply to tweet {reply_to_id})")
        return "dry-run-id"

    try:
        kwargs = {"text": text}
        if reply_to_id:
            kwargs["in_reply_to_tweet_id"] = reply_to_id

        response = client.create_tweet(**kwargs)
        tweet_id = response.data["id"]
        print(f"Posted tweet {tweet_id} ({len(text)} chars)")
        return tweet_id
    except tweepy.TweepyException as e:
        print(f"ERROR posting tweet: {e}")
        sys.exit(1)


def post_thread(client, tweets, dry_run=False):
    """Post a thread (list of tweet texts chained as replies)."""
    if not tweets:
        print("ERROR: No tweets provided for thread.")
        sys.exit(1)

    print(f"Posting thread ({len(tweets)} tweets)...")
    previous_id = None
    for i, text in enumerate(tweets, 1):
        print(f"\n--- Tweet {i}/{len(tweets)} ---")
        previous_id = post_tweet(client, text, reply_to_id=previous_id, dry_run=dry_run)

    print(f"\nThread complete. {len(tweets)} tweets posted.")


def extract_article_data(filepath):
    """Extract title, excerpt, URL, and key points from an article HTML file."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    content = path.read_text()

    # Extract title
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else path.stem

    # Extract meta description
    desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', content)
    description = desc_match.group(1) if desc_match else ""

    # Extract H2 headings for key topics
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', content)
    # Filter out "References" and utility headings
    h2s = [h for h in h2s if h.lower() not in ("references", "sources")]

    # Build article URL
    filename = path.name
    url = f"https://peptiderevealed.com/articles/{filename}"

    return {
        "title": title,
        "description": description,
        "h2s": h2s,
        "url": url,
        "filename": filename,
    }


def generate_tweet_options(article):
    """Generate several tweet options from article data."""
    title = article["title"]
    desc = article["description"]
    url = article["url"]
    h2s = article["h2s"]

    options = []

    # Option 1: Title + description + link
    tweet1 = f"{title}.\n\n{desc}\n\n{url}"
    if len(tweet1) <= 280:
        options.append(("Title + description", tweet1))

    # Option 2: Hook question + link
    tweet2 = f"What does the research actually say about {title.split(':')[0].lower() if ':' in title else title.lower()}?\n\nWe dug into the studies.\n\n{url}"
    if len(tweet2) <= 280:
        options.append(("Hook question", tweet2))

    # Option 3: Key sections teaser
    if len(h2s) >= 3:
        sections = "\n".join(f"→ {h}" for h in h2s[:4])
        tweet3 = f"{title}\n\nWhat we cover:\n{sections}\n\n{url}"
        if len(tweet3) <= 280:
            options.append(("Sections teaser", tweet3))

    # Option 4: Short and punchy
    short_title = title.split(":")[0] if ":" in title else title
    tweet4 = f"New deep dive: {short_title}\n\nEvidence-based. No hype.\n\n{url}"
    if len(tweet4) <= 280:
        options.append(("Short and punchy", tweet4))

    # Option 5: Thread starter (for longer content)
    thread_start = f"🧵 {title}\n\nA thread on what the research says (with sources):"
    if len(thread_start) <= 280:
        thread_tweets = [thread_start]
        for h2 in h2s[:5]:
            thread_tweets.append(f"→ {h2}")
        thread_tweets.append(f"Full breakdown with PubMed citations:\n{url}")
        options.append(("Thread format", "\n---\n".join(thread_tweets)))

    return options


def preview_article(filepath):
    """Show tweet options generated from an article."""
    article = extract_article_data(filepath)

    print(f"Article: {article['title']}")
    print(f"URL: {article['url']}")
    print(f"Sections: {len(article['h2s'])}")
    print("=" * 50)

    options = generate_tweet_options(article)
    for i, (label, text) in enumerate(options, 1):
        char_count = len(text.split("---")[0]) if "---" in text else len(text)
        print(f"\n{'─' * 40}")
        print(f"Option {i}: {label} ({char_count} chars)")
        print(f"{'─' * 40}")
        print(text)

    print(f"\n{'=' * 50}")
    print(f"Generated {len(options)} tweet options.")
    print("To post one, copy the text and run:")
    print('  python tools/twitter_post.py --tweet "your chosen text"')


def log_tweet(text, tweet_id, mode):
    """Log posted tweets to .tmp/twitter/ for tracking."""
    log_dir = Path(".tmp/twitter")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"tweets_{datetime.now().strftime('%Y-%m')}.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tweet_id": str(tweet_id),
        "text": text,
        "mode": mode,
        "chars": len(text),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Twitter/X posting tool for Peptide Revealed")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tweet", type=str, help="Post a single tweet")
    group.add_argument("--thread", nargs="+", type=str, help="Post a thread (multiple tweets)")
    group.add_argument("--preview", type=str, help="Preview tweet options from an article file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted without posting")

    args = parser.parse_args()

    if args.preview:
        preview_article(args.preview)
        return

    client = get_client()

    if args.tweet:
        tweet_id = post_tweet(client, args.tweet, dry_run=args.dry_run)
        if not args.dry_run:
            log_tweet(args.tweet, tweet_id, "single")

    elif args.thread:
        post_thread(client, args.thread, dry_run=args.dry_run)
        if not args.dry_run:
            for t in args.thread:
                log_tweet(t, "thread", "thread")


if __name__ == "__main__":
    main()
