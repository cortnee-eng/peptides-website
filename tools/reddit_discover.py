#!/usr/bin/env python3
"""
Reddit Post Discovery Tool — Find threads worth replying to for peptide education.

Scans peptide-related subreddits for recent question posts with low comment counts
where a knowledgeable reply would stand out. Uses Reddit's public JSON feeds.

Usage:
  python3 tools/reddit_discover.py
  python3 tools/reddit_discover.py --limit 10
  python3 tools/reddit_discover.py --subreddit Peptides
  python3 tools/reddit_discover.py --sort score
  python3 tools/reddit_discover.py --subreddit Biohackers --limit 5

No API keys needed. Be respectful — don't run this more than a few times per hour.
"""

import argparse
import json
import subprocess
import time
import random
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUBREDDITS = [
    "Peptides",
    "Ozempic",
    "Mounjaro",
    "Semaglutide",
    "glp1",
    "loseit",
    "Biohackers",
    "SkincareAddiction",
]

# Keywords that signal a post matches our expertise
EXPERTISE_KEYWORDS = [
    # Peptide names
    "bpc-157", "bpc 157", "bpc157",
    "tb-500", "tb 500", "tb500", "thymosin",
    "ghk-cu", "ghk cu", "copper peptide",
    "glp-1", "glp1", "glp 1",
    "semaglutide", "ozempic", "wegovy", "rybelsus",
    "tirzepatide", "mounjaro", "zepbound",
    "retatrutide",
    "ipamorelin", "cjc-1295", "cjc 1295",
    "epithalon", "epitalon",
    "selank", "semax",
    "mots-c", "humanin",
    "pt-141", "pt 141",
    "aod-9604",
    # Topics
    "reconstitution", "reconstitute", "bacteriostatic",
    "dosing", "dosage", "mcg",
    "subcutaneous", "injection", "inject",
    "side effect", "side effects",
    "peptide stack", "stacking",
    "sourcing", "source", "vendor", "supplier",
    "legal", "legality", "prescription",
    "purity", "third party test", "coa",
    "half-life", "half life",
    "peptide sciences", "peptidesciences",
    "weight loss", "fat loss",
    "muscle", "recovery", "healing",
    "collagen", "anti-aging", "longevity",
    "hair loss", "hair growth",
    "research chemical",
]

# Flair values that suggest a question/advice post
QUESTION_FLAIRS = {"question", "help", "advice", "discussion", "newbie", "new user", "beginner"}

# Words that suggest low-value posts to skip
SKIP_SIGNALS = [
    "meme", "shitpost", "progress pic", "face reveal",
    "before and after",  # often just pics, no question
]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

MAX_POST_AGE_HOURS = 48
MAX_COMMENTS = 15

# Subreddits where posts MUST mention a peptide keyword to be included.
# Without this, generic skincare/weight-loss posts flood results.
REQUIRE_KEYWORD_SUBS = {"SkincareAddiction", "loseit"}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_subreddit(subreddit, sort="new", limit=50):
    """Fetch recent posts from a subreddit using public JSON feed via curl."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"

    try:
        result = subprocess.run(
            ["curl", "-s", "-f", "-L", "--max-time", "15",
             "-H", f"User-Agent: {USER_AGENT}",
             url],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            print(f" [!] Failed to fetch r/{subreddit} (curl exit {result.returncode}) — skipping")
            return []
        data = json.loads(result.stdout)
        return data.get("data", {}).get("children", [])
    except subprocess.TimeoutExpired:
        print(f" [!] Timeout fetching r/{subreddit} — skipping")
        return []
    except (json.JSONDecodeError, Exception) as e:
        print(f" [!] Error fetching r/{subreddit}: {e}")
        return []


# ---------------------------------------------------------------------------
# Filtering & Scoring
# ---------------------------------------------------------------------------

def age_hours(created_utc):
    """Return how many hours old a post is."""
    now = datetime.now(timezone.utc).timestamp()
    return (now - created_utc) / 3600


def format_age(hours):
    """Human-readable age string."""
    if hours < 1:
        return f"{int(hours * 60)}m ago"
    elif hours < 24:
        return f"{int(hours)}h ago"
    else:
        days = hours / 24
        if days < 2:
            return "1d ago"
        return f"{int(days)}d ago"


def is_question_post(post):
    """Check if a post looks like it's asking a question."""
    title = post.get("title", "")
    flair = (post.get("link_flair_text") or "").lower()
    selftext = (post.get("selftext") or "")[:500].lower()

    if "?" in title:
        return True
    if any(f in flair for f in QUESTION_FLAIRS):
        return True
    # Common question starters in title
    title_lower = title.lower()
    question_starters = [
        "how ", "what ", "why ", "is ", "are ", "can ", "should ",
        "does ", "do ", "has anyone", "anyone", "help", "advice",
        "need help", "confused", "new to", "first time", "eli5",
    ]
    if any(title_lower.startswith(s) for s in question_starters):
        return True
    if "?" in selftext[:300]:
        return True
    return False


def should_skip(post):
    """Return True if this post is low-value (memes, deleted, spam)."""
    title_lower = post.get("title", "").lower()
    selftext = post.get("selftext", "")

    # Deleted / removed
    if selftext in ("[removed]", "[deleted]"):
        return True
    if post.get("removed_by_category"):
        return True

    # Memes, progress pics without questions
    for signal in SKIP_SIGNALS:
        if signal in title_lower:
            # Exception: "before and after" with a question mark is fine
            if signal == "before and after" and "?" in post.get("title", ""):
                continue
            return True

    # Link-only posts to external sites (often spam/vendor links)
    if post.get("is_self") is False and not post.get("is_reddit_media_domain"):
        domain = post.get("domain", "")
        if domain and "reddit" not in domain and "imgur" not in domain:
            return True

    return False


def count_keyword_matches(post):
    """Count how many expertise keywords appear in the post."""
    text = (post.get("title", "") + " " + (post.get("selftext") or "")[:1000]).lower()
    matches = []
    for kw in EXPERTISE_KEYWORDS:
        if kw in text:
            matches.append(kw)
    return matches


def score_post(post):
    """Score a post's reply opportunity (higher = better). Returns (score, reasons)."""
    score = 0
    reasons = []

    title = post.get("title", "")
    num_comments = post.get("num_comments", 0)
    upvotes = post.get("score", 0)
    hours = age_hours(post.get("created_utc", 0))

    # Question signals
    if "?" in title:
        score += 3
        reasons.append("direct question")
    flair = (post.get("link_flair_text") or "").lower()
    if any(f in flair for f in QUESTION_FLAIRS):
        score += 2

    # Fewer comments = more opportunity
    if num_comments == 0:
        score += 5
        reasons.append("no replies yet")
    elif num_comments <= 3:
        score += 4
        reasons.append(f"only {num_comments} comment{'s' if num_comments != 1 else ''}")
    elif num_comments <= 7:
        score += 2
    elif num_comments <= 15:
        score += 1

    # Keyword matches
    matches = count_keyword_matches(post)
    kw_score = min(len(matches), 5)  # cap at 5
    score += kw_score
    if matches:
        # Pick the most specific/interesting match for the reason
        # Prefer peptide names over generic terms
        best = matches[0]
        for m in matches:
            if any(c in m for c in ["-", "157", "500", "cu", "glp", "sema", "tirz"]):
                best = m
                break
        reasons.append(f"mentions {best}")

    # Recency bonus
    if hours < 4:
        score += 3
        reasons.append("very fresh")
    elif hours < 12:
        score += 2
    elif hours < 24:
        score += 1

    # Upvotes show engagement potential
    if upvotes >= 10:
        score += 1
    if upvotes >= 50:
        score += 1

    return score, reasons


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def discover(subreddit_filter=None, limit=20, sort_by="score"):
    """Discover high-value Reddit posts to reply to."""
    targets = [subreddit_filter] if subreddit_filter else SUBREDDITS
    candidates = []

    for i, sub in enumerate(targets):
        print(f"  Scanning r/{sub}...", end="", flush=True)
        posts = fetch_subreddit(sub)
        count = 0

        for item in posts:
            post = item.get("data", {})

            # Age filter
            hours = age_hours(post.get("created_utc", 0))
            if hours > MAX_POST_AGE_HOURS:
                continue

            # Comment count filter
            if post.get("num_comments", 0) > MAX_COMMENTS:
                continue

            # Skip low-value posts
            if should_skip(post):
                continue

            # Must look like a question or discussion
            if not is_question_post(post):
                continue

            # In broad subs, require at least one peptide keyword match
            if sub in REQUIRE_KEYWORD_SUBS and not count_keyword_matches(post):
                continue

            score, reasons = score_post(post)
            candidates.append({
                "subreddit": sub,
                "title": post.get("title", ""),
                "num_comments": post.get("num_comments", 0),
                "upvotes": post.get("score", 0),
                "age_hours": hours,
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "score": score,
                "reasons": reasons,
            })
            count += 1

        print(f" {count} candidates")

        # Rate limiting between subreddit fetches
        if i < len(targets) - 1:
            delay = 1.0 + random.random()  # 1-2 seconds
            time.sleep(delay)

    # Sort
    if sort_by == "score":
        candidates.sort(key=lambda x: x["score"], reverse=True)
    elif sort_by == "comments":
        candidates.sort(key=lambda x: x["num_comments"])
    elif sort_by == "age":
        candidates.sort(key=lambda x: x["age_hours"])

    return candidates[:limit]


def print_results(candidates):
    """Print formatted results to terminal."""
    if not candidates:
        print("\n  No matching posts found. Try again later or broaden filters.\n")
        return

    print(f"\n{'='*80}")
    print(f"  TOP {len(candidates)} REPLY OPPORTUNITIES")
    print(f"{'='*80}\n")

    for i, c in enumerate(candidates, 1):
        age_str = format_age(c["age_hours"])
        reason_str = ", ".join(c["reasons"]) if c["reasons"] else "general match"

        print(f"  {i:>2}. r/{c['subreddit']}")
        print(f"      {c['title'][:90]}")
        print(f"      {c['num_comments']} comments | {c['upvotes']} upvotes | {age_str} | opportunity: {c['score']}/15")
        print(f"      Why: {reason_str}")
        print(f"      {c['url']}")
        print()

    print(f"{'='*80}")
    print(f"  Tip: Reply with genuine expertise. No links. Just be helpful.")
    print(f"{'='*80}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Find Reddit posts worth replying to for peptide education. "
                    "Scans peptide-related subreddits for recent questions with few replies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python3 tools/reddit_discover.py\n"
               "  python3 tools/reddit_discover.py --limit 10\n"
               "  python3 tools/reddit_discover.py --subreddit Peptides\n"
               "  python3 tools/reddit_discover.py --sort age\n",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Number of results to show (default: 20)",
    )
    parser.add_argument(
        "--subreddit", type=str, default=None,
        help="Filter to a single subreddit (e.g., Peptides, Ozempic)",
    )
    parser.add_argument(
        "--sort", choices=["score", "comments", "age"], default="score",
        help="Sort results by: score (best opportunity), comments (fewest first), age (newest first)",
    )

    args = parser.parse_args()

    print()
    print("  Reddit Reply Discovery — peptiderevealed.com")
    print("  " + "-" * 45)
    print()

    candidates = discover(
        subreddit_filter=args.subreddit,
        limit=args.limit,
        sort_by=args.sort,
    )

    print_results(candidates)


if __name__ == "__main__":
    main()
