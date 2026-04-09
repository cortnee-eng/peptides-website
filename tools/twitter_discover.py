"""
Twitter/X Account Discovery Tool — Find relevant accounts in the peptide/biohacking space.

Uses web search (DuckDuckGo) instead of the Twitter API. No API keys needed.

Modes:
  1. Search for accounts tweeting about a topic:
     python3 tools/twitter_discover.py --search "peptides"

  2. Search multiple topics at once:
     python3 tools/twitter_discover.py --search "BPC-157" "GHK-Cu" "peptide therapy"

  3. Export results to a file for review:
     python3 tools/twitter_discover.py --search "peptides" --export

All modes output a curated list for YOU to follow manually.

Requirements: pip3 install ddgs
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

from ddgs import DDGS


def search_accounts(query, max_results=20):
    """Search the web for X/Twitter accounts related to a topic."""
    accounts = {}

    search_queries = [
        f"{query} twitter",
        f"{query} x.com",
        f"{query} twitter account to follow",
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

            key = username.lower()

            if key in accounts:
                accounts[key]["mentions"] += 1
                if body and len(body) > len(accounts[key]["context"]):
                    accounts[key]["context"] = body[:300]
                continue

            is_profile = "/status/" not in url

            accounts[key] = {
                "username": username,
                "context": body[:300] if body else title[:200],
                "url": f"https://x.com/{username}",
                "is_profile": is_profile,
                "mentions": 1,
                "query": query,
                "source_url": url,
            }

    return accounts


def is_twitter_url(url):
    """Check if a URL is actually from Twitter/X (not just containing the words)."""
    return bool(re.match(r'https?://(?:www\.)?(?:x\.com|twitter\.com)/', url))


def extract_username(url):
    """Extract a Twitter/X username from a URL."""
    match = re.search(r'(?:x\.com|twitter\.com)/(@?([A-Za-z0-9_]{1,15}))(?:/|$|\?)', url)
    if not match:
        return None

    username = match.group(2) if match.group(2) else match.group(1).lstrip("@")

    skip = {
        "search", "explore", "home", "hashtag", "i", "settings",
        "notifications", "messages", "compose", "intent", "share",
        "login", "signup", "tos", "privacy", "about", "help",
        "twitter", "x",
    }
    if username.lower() in skip:
        return None

    return username


def score_account(account):
    """Score an account for relevance. Higher = more worth following."""
    score = 0

    mentions = account["mentions"]
    if mentions >= 3:
        score += 5
    elif mentions >= 2:
        score += 3
    else:
        score += 1

    if account["is_profile"]:
        score += 2

    context = account["context"].lower()
    peptide_terms = [
        "peptide", "bpc", "ghk", "tb-500", "thymosin", "glp-1",
        "biohacking", "longevity", "recovery", "research",
        "clinical", "study", "healing", "anti-aging",
    ]
    term_matches = sum(1 for term in peptide_terms if term in context)
    score += min(term_matches, 4)

    return score


def display_results(accounts, title="Discovered Accounts"):
    """Display accounts sorted by relevance score."""
    if not accounts:
        print("No accounts found.")
        return []

    scored = []
    for acc in accounts.values():
        acc["score"] = score_account(acc)
        scored.append(acc)

    scored.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"  {len(scored)} accounts found, sorted by relevance")
    print(f"{'=' * 60}\n")

    for i, acc in enumerate(scored, 1):
        print(f"{i:>3}. @{acc['username']}  (score: {acc['score']}, mentions: {acc['mentions']})")
        if acc["context"]:
            context = acc["context"].replace("\n", " ")
            if len(context) > 150:
                context = context[:147] + "..."
            print(f"     {context}")
        print(f"     {acc['url']}")
        print()

    return scored


def export_results(scored, filename=None):
    """Export results to .tmp/twitter/ as JSON."""
    export_dir = Path(".tmp/twitter")
    export_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        filename = f"discover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = export_dir / filename

    export_data = {
        "generated": datetime.now().isoformat(),
        "count": len(scored),
        "accounts": scored,
    }

    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"Exported {len(scored)} accounts to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Discover relevant Twitter/X accounts in the peptide space (via web search)"
    )
    parser.add_argument(
        "--search", nargs="+", type=str, required=True,
        help="Search for accounts tweeting about these topics"
    )
    parser.add_argument(
        "--export", action="store_true",
        help="Export results to .tmp/twitter/ as JSON"
    )
    parser.add_argument(
        "--max-results", type=int, default=20,
        help="Max search results per query (default: 20)"
    )

    args = parser.parse_args()

    all_accounts = {}

    for query in args.search:
        print(f"Searching for accounts tweeting about: {query}")
        results = search_accounts(query, max_results=args.max_results)
        print(f"  Found {len(results)} accounts")

        for key, acc in results.items():
            if key in all_accounts:
                all_accounts[key]["mentions"] += acc["mentions"]
                all_accounts[key]["query"] += f", {acc['query']}"
            else:
                all_accounts[key] = acc

    title = f"Accounts tweeting about: {', '.join(args.search)}"
    scored = display_results(all_accounts, title=title)

    if args.export and scored:
        export_results(scored)


if __name__ == "__main__":
    main()
