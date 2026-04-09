"""
Twitter/X Engagement Finder — Surface recent tweets about peptide topics to engage with.

Uses web search (DuckDuckGo) instead of the Twitter API. No API keys needed.

Modes:
  1. Find tweets to engage with on default peptide topics:
     python3 tools/twitter_engage.py

  2. Search specific topics:
     python3 tools/twitter_engage.py --topics "BPC-157" "GHK-Cu hair loss"

  3. Export results for later review:
     python3 tools/twitter_engage.py --export

This tool finds conversations — you decide which to engage with.

Requirements: pip3 install ddgs
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

from ddgs import DDGS

# Default topics aligned with Peptide Revealed content
DEFAULT_TOPICS = [
    "BPC-157",
    "GHK-Cu peptide",
    "TB-500 healing",
    "peptide therapy",
    "GLP-1 peptide",
    "peptides for recovery",
    "thymosin alpha-1",
    "peptide research",
]


def search_tweets(topic, max_results=15):
    """Search the web for recent tweets/discussions about a topic."""
    tweets = []

    search_queries = [
        f"{topic} x.com",
        f"{topic} twitter thread",
        f"{topic} twitter discussion",
    ]

    ddgs = DDGS()

    for sq in search_queries:
        try:
            results = list(ddgs.text(sq, max_results=max_results))
        except Exception as e:
            print(f"  Search error for '{sq}': {e}")
            continue

        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            body = r.get("body", "")

            # Only process actual Twitter/X URLs
            if not is_twitter_url(url):
                continue

            username = extract_username(url)
            if not username:
                continue

            is_tweet = "/status/" in url

            # Clean URL
            clean_url = url.split("?")[0].rstrip("/")

            tweets.append({
                "username": username,
                "text": body[:400] if body else title[:300],
                "title": title[:200],
                "url": clean_url,
                "topic": topic,
                "is_tweet": is_tweet,
            })

    return tweets


def is_twitter_url(url):
    """Check if a URL is actually from Twitter/X."""
    return bool(re.match(r'https?://(?:www\.)?(?:x\.com|twitter\.com)/', url))


def extract_username(url):
    """Extract username from a Twitter/X URL."""
    match = re.search(
        r'(?:x\.com|twitter\.com)/([A-Za-z0-9_]{1,15})',
        url
    )
    if not match:
        return None

    username = match.group(1)

    skip = {
        "search", "explore", "home", "hashtag", "i", "settings",
        "notifications", "messages", "compose", "intent", "share",
        "login", "signup", "tos", "privacy", "about", "help",
        "twitter", "x",
    }
    if username.lower() in skip:
        return None

    return username


def display_results(all_results, limit=30):
    """Display tweet results deduplicated and formatted."""
    if not all_results:
        print("\nNo tweets found matching your criteria.")
        return []

    # Deduplicate by URL
    seen = set()
    unique = []
    for t in all_results:
        key = t["url"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    unique = unique[:limit]

    print(f"\n{'=' * 60}")
    print(f"  Found {len(unique)} Tweets / Conversations")
    print(f"{'=' * 60}\n")

    for i, t in enumerate(unique, 1):
        tag = "TWEET" if t.get("is_tweet") else "PROFILE"

        print(f"{i:>3}. [{tag}] @{t['username']} — {t['topic']}")

        text = t["text"].replace("\n", " ").strip()
        if len(text) > 200:
            text = text[:197] + "..."
        if text:
            print(f"     \"{text}\"")

        print(f"     {t['url']}")
        print()

    return unique


def export_results(results, filename=None):
    """Export results to .tmp/twitter/ as JSON."""
    export_dir = Path(".tmp/twitter")
    export_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        filename = f"engage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = export_dir / filename

    export_data = {
        "generated": datetime.now().isoformat(),
        "count": len(results),
        "tweets": results,
    }

    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"Exported {len(results)} results to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Find recent tweets about peptide topics to engage with (via web search)"
    )
    parser.add_argument(
        "--topics", nargs="+", type=str,
        help="Topics to search (default: built-in peptide topics)"
    )
    parser.add_argument(
        "--limit", type=int, default=30,
        help="Max total results to display (default: 30)"
    )
    parser.add_argument(
        "--max-results", type=int, default=15,
        help="Max search results per topic (default: 15)"
    )
    parser.add_argument(
        "--export", action="store_true",
        help="Export results to .tmp/twitter/ as JSON"
    )

    args = parser.parse_args()

    topics = args.topics or DEFAULT_TOPICS
    all_results = []

    for topic in topics:
        print(f"Searching: {topic}")
        tweets = search_tweets(topic, max_results=args.max_results)
        print(f"  Found {len(tweets)} results")
        all_results.extend(tweets)

    results = display_results(all_results, limit=args.limit)

    if args.export and results:
        export_results(results)

    if results:
        print(f"{'─' * 60}")
        print("Open the URLs above to engage directly on X.")
        print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
