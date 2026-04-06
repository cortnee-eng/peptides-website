"""
GSC Index Checker — Bulk check indexing status via Google Search Console API

Reads all URLs from sitemap.xml and checks their indexing status using
the URL Inspection API. Outputs a summary grouped by status.

Setup (one-time):
  1. Go to Google Cloud Console → APIs & Services → Enable "Google Search Console API"
  2. Create OAuth 2.0 credentials (Desktop app type)
  3. Download the JSON and save as credentials_gsc.json in the project root
  4. Run this script — it will open a browser for auth on first run
     and save the token to token_gsc.json for future use

Usage:
  python tools/gsc_index_check.py                   # Check all sitemap URLs
  python tools/gsc_index_check.py --url URL          # Check a single URL
  python tools/gsc_index_check.py --save             # Save results to .tmp/
"""

import os
import sys
import json
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITEMAP_PATH = PROJECT_ROOT / "sitemap.xml"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials_gsc.json"
TOKEN_FILE = PROJECT_ROOT / "token_gsc.json"
SITE_URL = "https://peptiderevealed.com/"  # Must match GSC property exactly

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# ── Site URL Detection ────────────────────────────────────────────

def detect_site_url(service):
    """Auto-detect the correct GSC property for peptiderevealed.com."""
    # Possible formats GSC uses
    candidates = [
        "sc-domain:peptiderevealed.com",
        "https://peptiderevealed.com/",
        "http://peptiderevealed.com/",
        "https://www.peptiderevealed.com/",
    ]

    try:
        site_list = service.sites().list().execute()
        verified = [s["siteUrl"] for s in site_list.get("siteEntry", [])]
        if verified:
            print(f"Found GSC properties: {verified}")
            for candidate in candidates:
                if candidate in verified:
                    print(f"Using: {candidate}")
                    return candidate
            # If none of our candidates match, use the first verified site
            print(f"Using first verified property: {verified[0]}")
            return verified[0]
    except Exception as e:
        print(f"Could not list sites: {e}")

    return SITE_URL  # fallback

# ── Auth ──────────────────────────────────────────────────────────

def get_credentials():
    """Get or refresh OAuth2 credentials."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"ERROR: {CREDENTIALS_FILE} not found.")
                print()
                print("Setup instructions:")
                print("  1. Go to https://console.cloud.google.com/apis/credentials")
                print("  2. Enable the 'Google Search Console API'")
                print("  3. Create OAuth 2.0 Client ID (Desktop app)")
                print("  4. Download the JSON → save as credentials_gsc.json in project root")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return creds

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

# ── URL Inspection ────────────────────────────────────────────────

def inspect_url(service, url, site_url):
    """Inspect a single URL and return its indexing status."""
    try:
        result = service.urlInspection().index().inspect(
            body={
                "inspectionUrl": url,
                "siteUrl": site_url,
            }
        ).execute()

        inspection = result.get("inspectionResult", {})
        index_status = inspection.get("indexStatusResult", {})

        return {
            "url": url,
            "verdict": index_status.get("verdict", "UNKNOWN"),
            "coverageState": index_status.get("coverageState", "Unknown"),
            "robotsTxtState": index_status.get("robotsTxtState", ""),
            "indexingState": index_status.get("indexingState", ""),
            "lastCrawlTime": index_status.get("lastCrawlTime", ""),
            "pageFetchState": index_status.get("pageFetchState", ""),
            "crawledAs": index_status.get("crawledAs", ""),
            "referringUrls": index_status.get("referringUrls", []),
        }
    except Exception as e:
        return {
            "url": url,
            "verdict": "ERROR",
            "coverageState": str(e),
        }

# ── Output ────────────────────────────────────────────────────────

STATUS_ICONS = {
    "PASS": "✅",
    "NEUTRAL": "⚪",
    "FAIL": "❌",
    "ERROR": "⚠️",
    "UNKNOWN": "❓",
}

def print_results(results):
    """Print a formatted summary of indexing results."""
    # Group by verdict
    groups = {}
    for r in results:
        verdict = r["verdict"]
        groups.setdefault(verdict, []).append(r)

    total = len(results)
    indexed = len(groups.get("PASS", []))

    print()
    print("=" * 70)
    print(f"  GSC INDEXING STATUS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {indexed}/{total} URLs indexed")
    print("=" * 70)

    for verdict in ["PASS", "NEUTRAL", "FAIL", "ERROR", "UNKNOWN"]:
        if verdict not in groups:
            continue
        icon = STATUS_ICONS.get(verdict, "?")
        print(f"\n{icon} {verdict} ({len(groups[verdict])} URLs)")
        print("-" * 50)
        for r in groups[verdict]:
            short_url = r["url"].replace("https://peptiderevealed.com/", "/")
            state = r.get("coverageState", "")
            crawl = r.get("lastCrawlTime", "")
            crawl_short = crawl[:10] if crawl else "never"
            print(f"  {short_url}")
            print(f"    Status: {state} | Last crawl: {crawl_short}")
            if r.get("pageFetchState"):
                print(f"    Fetch: {r['pageFetchState']} | Bot: {r.get('crawledAs', 'N/A')}")

    print()

    # Actionable summary
    not_indexed = groups.get("NEUTRAL", []) + groups.get("FAIL", [])
    if not_indexed:
        print("📋 ACTION ITEMS:")
        print("-" * 50)
        for r in not_indexed:
            short_url = r["url"].replace("https://peptiderevealed.com/", "/")
            state = r.get("coverageState", "")
            if "Discovered" in state:
                print(f"  {short_url} → Discovered but not crawled yet. Wait or request indexing manually.")
            elif "Crawled" in state and "not indexed" in state.lower():
                print(f"  {short_url} → Crawled but not indexed. May need more backlinks or content improvement.")
            else:
                print(f"  {short_url} → {state}")
        print()


def save_results(results):
    """Save results to .tmp/ as JSON."""
    tmp_dir = PROJECT_ROOT / ".tmp" / "gsc"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    outfile = tmp_dir / f"index_status_{timestamp}.json"
    outfile.write_text(json.dumps(results, indent=2))
    print(f"💾 Results saved to {outfile}")

# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Check GSC indexing status")
    parser.add_argument("--url", help="Check a single URL instead of all sitemap URLs")
    parser.add_argument("--save", action="store_true", help="Save results to .tmp/gsc/")
    args = parser.parse_args()

    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    # Auto-detect the correct GSC property format
    site_url = detect_site_url(service)

    if args.url:
        urls = [args.url]
    else:
        urls = get_sitemap_urls()

    print(f"Checking {len(urls)} URLs against Google Search Console...")
    print("(This may take a moment — API has rate limits)\n")

    results = []
    for i, url in enumerate(urls, 1):
        short = url.replace("https://peptiderevealed.com/", "/")
        print(f"  [{i}/{len(urls)}] {short}...", end=" ", flush=True)
        result = inspect_url(service, url, site_url)
        verdict = result["verdict"]
        icon = STATUS_ICONS.get(verdict, "?")
        print(f"{icon} {verdict}")
        results.append(result)

    print_results(results)

    if args.save:
        save_results(results)

if __name__ == "__main__":
    main()
