"""
IndexNow Pinger — Notify Bing & Yandex of new/updated URLs instantly

IndexNow is a protocol that lets you push URL changes to search engines
immediately instead of waiting for them to crawl. Supported by Bing, Yandex,
Seznam, and Naver (NOT Google — Google ignores IndexNow).

Setup (one-time):
  1. Run: python tools/indexnow_ping.py --generate-key
     This creates a key file that must be deployed to your site root.
  2. Deploy the key file to Vercel (just commit and push — it's a .txt file)
  3. Add INDEXNOW_KEY=<your-key> to .env

Usage:
  python tools/indexnow_ping.py --url URL                    # Ping a single URL
  python tools/indexnow_ping.py --sitemap                    # Ping all sitemap URLs
  python tools/indexnow_ping.py --urls URL1 URL2 URL3        # Ping multiple URLs
  python tools/indexnow_ping.py --generate-key               # One-time key setup
"""

import os
import sys
import json
import argparse
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITEMAP_PATH = PROJECT_ROOT / "sitemap.xml"
HOST = "peptiderevealed.com"
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "")

# IndexNow endpoints — submit to one, it fans out to all partners
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

# ── Key Generation ────────────────────────────────────────────────

def generate_key():
    """Generate an IndexNow API key and create the verification file."""
    key = uuid.uuid4().hex  # 32-char hex string
    key_file = PROJECT_ROOT / f"{key}.txt"
    key_file.write_text(key)

    print(f"✅ IndexNow key generated: {key}")
    print()
    print(f"Key file created: {key_file.name}")
    print()
    print("Next steps:")
    print(f"  1. Add to .env:  INDEXNOW_KEY={key}")
    print(f"  2. Commit and push {key_file.name} so it's accessible at:")
    print(f"     https://{HOST}/{key_file.name}")
    print(f"  3. After deploy, verify: curl https://{HOST}/{key_file.name}")
    print()
    return key

# ── Sitemap Parser ────────────────────────────────────────────────

def get_sitemap_urls():
    """Parse all URLs from sitemap.xml."""
    if not SITEMAP_PATH.exists():
        print(f"ERROR: sitemap.xml not found at {SITEMAP_PATH}")
        sys.exit(1)

    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = []
    for url_elem in root.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        if loc is not None and loc.text:
            urls.append(loc.text.strip())

    return urls

# ── IndexNow Submission ──────────────────────────────────────────

def ping_single(url):
    """Submit a single URL to IndexNow."""
    if not INDEXNOW_KEY:
        print("ERROR: INDEXNOW_KEY not set in .env")
        print("Run: python tools/indexnow_ping.py --generate-key")
        sys.exit(1)

    params = {
        "url": url,
        "key": INDEXNOW_KEY,
    }

    resp = requests.get(INDEXNOW_ENDPOINT, params=params, timeout=10)

    if resp.status_code in (200, 202):
        print(f"  ✅ {url} → Accepted ({resp.status_code})")
        return True
    elif resp.status_code == 429:
        print(f"  ⏳ {url} → Rate limited. Try again later.")
        return False
    else:
        print(f"  ❌ {url} → {resp.status_code}: {resp.text[:200]}")
        return False


def ping_batch(urls):
    """Submit multiple URLs to IndexNow in a single batch request."""
    if not INDEXNOW_KEY:
        print("ERROR: INDEXNOW_KEY not set in .env")
        print("Run: python tools/indexnow_ping.py --generate-key")
        sys.exit(1)

    # IndexNow batch API accepts up to 10,000 URLs per request
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{HOST}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }

    resp = requests.post(
        INDEXNOW_ENDPOINT,
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
    )

    if resp.status_code in (200, 202):
        print(f"✅ Batch submitted: {len(urls)} URLs accepted ({resp.status_code})")
        return True
    elif resp.status_code == 429:
        print(f"⏳ Rate limited. Try again later.")
        return False
    else:
        print(f"❌ Batch failed: {resp.status_code}")
        print(f"   {resp.text[:300]}")
        return False

# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ping IndexNow for URL indexing")
    parser.add_argument("--url", help="Submit a single URL")
    parser.add_argument("--urls", nargs="+", help="Submit multiple URLs")
    parser.add_argument("--sitemap", action="store_true", help="Submit all sitemap URLs")
    parser.add_argument("--generate-key", action="store_true", help="Generate IndexNow API key")
    args = parser.parse_args()

    if args.generate_key:
        generate_key()
        return

    if args.url:
        print(f"Pinging IndexNow for 1 URL...")
        ping_single(args.url)

    elif args.urls:
        urls = args.urls
        print(f"Pinging IndexNow for {len(urls)} URLs...")
        if len(urls) == 1:
            ping_single(urls[0])
        else:
            ping_batch(urls)

    elif args.sitemap:
        urls = get_sitemap_urls()
        print(f"Pinging IndexNow for {len(urls)} sitemap URLs...")
        ping_batch(urls)

    else:
        parser.print_help()
        print()
        print("Quick start:")
        print("  python tools/indexnow_ping.py --generate-key    # First-time setup")
        print("  python tools/indexnow_ping.py --sitemap          # Ping all pages")

if __name__ == "__main__":
    main()
