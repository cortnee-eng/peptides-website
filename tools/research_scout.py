"""
Research Scout — Daily content intelligence briefing

Scrapes Reddit, Google News, and Google Trends for peptide/GLP-1 content.
Outputs a briefing with:
- Trending Reddit threads (what people are asking/discussing)
- News headlines (what's happening in the space)
- Content ideas (article topics + social post angles)

Usage: python tools/research_scout.py
       python tools/research_scout.py --channel reddit
       python tools/research_scout.py --channel news
       python tools/research_scout.py --save  (writes to .tmp/research/)
"""

import os
import re
import json
import argparse
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

HEADERS = {"User-Agent": "PeptideRevealed-ResearchBot/1.0"}

# ── Reddit ─────────────────────────────────────────────────────
SUBREDDITS = {
    "glp1": ["Ozempic", "Mounjaro", "Semaglutide", "tirzepatidehelp"],
    "peptides": ["Peptides", "sarms", "peptides_"],
    "health": ["loseit", "SkincareAddiction", "30PlusSkinCare", "Biohackers"],
}

def scrape_subreddit(sub, sort="hot", limit=15):
    """Fetch top posts from a subreddit using Reddit's public JSON API."""
    url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 429:
            print(f"  Rate limited on r/{sub}, skipping...")
            return []
        r.raise_for_status()
        data = r.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            if "title" not in p or "score" not in p:
                continue
            posts.append({
                "title": p["title"],
                "score": p.get("score", 0),
                "comments": p.get("num_comments", 0),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "selftext": (p.get("selftext") or "")[:200],
                "created": datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc),
                "subreddit": sub,
                "flair": p.get("link_flair_text", ""),
            })
        return posts
    except Exception as e:
        print(f"  Error fetching r/{sub}: {e}")
        return []

def get_reddit_intel():
    """Scan all target subreddits for trending discussions."""
    print("\nScanning Reddit...")
    all_posts = []

    for category, subs in SUBREDDITS.items():
        for sub in subs:
            posts = scrape_subreddit(sub, sort="hot", limit=10)
            all_posts.extend(posts)
            # Also check "new" for emerging topics
            new_posts = scrape_subreddit(sub, sort="new", limit=5)
            all_posts.extend(new_posts)

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in all_posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    # Filter to last 48 hours and sort by engagement
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    recent = [p for p in unique if p["created"] > cutoff]
    recent.sort(key=lambda x: x["score"] + x["comments"] * 2, reverse=True)

    return recent

def format_reddit_briefing(posts):
    """Format Reddit posts into a readable briefing."""
    if not posts:
        return "  No recent posts found.\n"

    lines = []

    # High engagement posts (potential content ideas)
    high = [p for p in posts if p["score"] >= 20 or p["comments"] >= 15]
    if high:
        lines.append("  HIGH ENGAGEMENT (content opportunity):")
        for p in high[:10]:
            lines.append(f"    [{p['score']}pts, {p['comments']}c] r/{p['subreddit']}: {p['title']}")
            if p["flair"]:
                lines.append(f"      Flair: {p['flair']}")
        lines.append("")

    # Questions being asked (article/social ideas)
    questions = [p for p in posts if "?" in p["title"]]
    if questions:
        lines.append("  QUESTIONS PEOPLE ARE ASKING:")
        for p in questions[:10]:
            lines.append(f"    r/{p['subreddit']}: {p['title']}")
        lines.append("")

    # New/emerging discussions
    new = sorted(posts, key=lambda x: x["created"], reverse=True)[:8]
    if new:
        lines.append("  NEWEST DISCUSSIONS:")
        for p in new:
            age_hrs = (datetime.now(timezone.utc) - p["created"]).total_seconds() / 3600
            lines.append(f"    [{age_hrs:.0f}h ago] r/{p['subreddit']}: {p['title']}")
        lines.append("")

    return "\n".join(lines)


# ── Google News ────────────────────────────────────────────────
NEWS_QUERIES = [
    "peptides",
    "GLP-1 semaglutide",
    "tirzepatide Mounjaro",
    "BPC-157",
    "peptide regulation FDA",
    "GHK-Cu copper peptide",
]

def scrape_google_news(query, num=5):
    """Fetch news via Google News RSS feed."""
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()

        # Simple XML parsing without lxml
        items = re.findall(r"<item>(.*?)</item>", r.text, re.DOTALL)
        results = []
        for item in items[:num]:
            title = re.search(r"<title>(.*?)</title>", item)
            link = re.search(r"<link/>(.*?)(?:<|$)", item)
            if not link:
                link = re.search(r"<link>(.*?)</link>", item)
            pub_date = re.search(r"<pubDate>(.*?)</pubDate>", item)
            source = re.search(r"<source.*?>(.*?)</source>", item)

            results.append({
                "title": title.group(1) if title else "Unknown",
                "url": link.group(1).strip() if link else "",
                "date": pub_date.group(1) if pub_date else "",
                "source": source.group(1) if source else "",
                "query": query,
            })
        return results
    except Exception as e:
        print(f"  Error fetching news for '{query}': {e}")
        return []

def get_news_intel():
    """Fetch recent news across all peptide/GLP-1 queries."""
    print("Scanning Google News...")
    all_articles = []
    for query in NEWS_QUERIES:
        articles = scrape_google_news(query, num=5)
        all_articles.extend(articles)

    # Deduplicate by title similarity
    seen_titles = set()
    unique = []
    for a in all_articles:
        key = a["title"][:50].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(a)

    return unique

def format_news_briefing(articles):
    """Format news articles into a readable briefing."""
    if not articles:
        return "  No recent news found.\n"

    lines = []
    by_query = {}
    for a in articles:
        by_query.setdefault(a["query"], []).append(a)

    for query, items in by_query.items():
        lines.append(f"  [{query.upper()}]")
        for a in items[:3]:
            source = f" — {a['source']}" if a['source'] else ""
            lines.append(f"    {a['title']}{source}")
        lines.append("")

    return "\n".join(lines)


# ── Content Ideas Generator ───────────────────────────────────
def generate_content_ideas(reddit_posts, news_articles):
    """Analyze scraped data and suggest content ideas."""
    lines = []

    # Reddit questions = article ideas
    questions = [p for p in reddit_posts if "?" in p["title"]]
    if questions:
        lines.append("  ARTICLE IDEAS (from Reddit questions):")
        seen = set()
        for p in questions[:8]:
            # Clean up the title as a topic
            topic = p["title"].strip("?").strip()
            if topic.lower() not in seen:
                seen.add(topic.lower())
                lines.append(f"    - \"{topic}\" (r/{p['subreddit']}, {p['comments']} comments)")
        lines.append("")

    # High-engagement Reddit = social post angles
    hot = [p for p in reddit_posts if p["score"] >= 20]
    if hot:
        lines.append("  SOCIAL POST ANGLES (from trending Reddit):")
        for p in hot[:5]:
            lines.append(f"    - Riff on: \"{p['title']}\" ({p['score']}pts in r/{p['subreddit']})")
        lines.append("")

    # News = timely content opportunities
    if news_articles:
        lines.append("  TIMELY HOOKS (from news):")
        for a in news_articles[:5]:
            lines.append(f"    - {a['title']}")
        lines.append("")

    # Subreddit-specific opportunities
    glp1_posts = [p for p in reddit_posts if p["subreddit"] in SUBREDDITS["glp1"]]
    peptide_posts = [p for p in reddit_posts if p["subreddit"] in SUBREDDITS["peptides"]]

    if glp1_posts:
        top_topics = {}
        for p in glp1_posts:
            for keyword in ["nausea", "plateau", "muscle", "protein", "appetite", "hunger",
                           "dose", "insurance", "cost", "side effect", "hair", "constipation"]:
                if keyword in p["title"].lower():
                    top_topics[keyword] = top_topics.get(keyword, 0) + 1
        if top_topics:
            sorted_topics = sorted(top_topics.items(), key=lambda x: x[1], reverse=True)
            lines.append("  HOT GLP-1 TOPICS (by mention frequency):")
            for topic, count in sorted_topics[:6]:
                lines.append(f"    - \"{topic}\" — mentioned in {count} posts")
            lines.append("")

    return "\n".join(lines) if lines else "  Not enough data to generate ideas yet.\n"


# ── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Research Scout — daily content intelligence")
    parser.add_argument("--channel", choices=["reddit", "news", "all"], default="all")
    parser.add_argument("--save", action="store_true", help="Save output to .tmp/research/")
    args = parser.parse_args()

    now = datetime.now()
    output_lines = []

    def out(line=""):
        print(line)
        output_lines.append(line)

    out("=" * 60)
    out(f"  RESEARCH BRIEFING — {now.strftime('%A, %B %d, %Y')}")
    out("=" * 60)

    reddit_posts = []
    news_articles = []

    if args.channel in ("reddit", "all"):
        reddit_posts = get_reddit_intel()
        out(f"\n{'=' * 40}")
        out("  REDDIT INTELLIGENCE")
        out(f"{'=' * 40}")
        out(format_reddit_briefing(reddit_posts))

    if args.channel in ("news", "all"):
        news_articles = get_news_intel()
        out(f"{'=' * 40}")
        out("  NEWS HEADLINES")
        out(f"{'=' * 40}")
        out(format_news_briefing(news_articles))

    out(f"{'=' * 40}")
    out("  CONTENT IDEAS")
    out(f"{'=' * 40}")
    out(generate_content_ideas(reddit_posts, news_articles))

    out("-" * 60)
    out(f"  Scanned {len(reddit_posts)} Reddit posts + {len(news_articles)} news articles")
    out(f"  Run at {now.strftime('%H:%M')}")
    out("")

    if args.save:
        save_dir = Path(".tmp/research")
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = save_dir / f"briefing_{now.strftime('%Y-%m-%d')}.txt"
        filename.write_text("\n".join(output_lines))
        print(f"Saved to {filename}")

if __name__ == "__main__":
    main()
