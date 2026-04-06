# Indexing Management Workflow

## Objective
Monitor and accelerate search engine indexing for peptiderevealed.com across Google, Bing, and Yandex.

## Tools

| Tool | Purpose |
|------|---------|
| `tools/gsc_index_check.py` | Bulk check Google indexing status via Search Console API |
| `tools/indexnow_ping.py` | Instantly notify Bing/Yandex of new or updated URLs |

---

## One-Time Setup

### Google Search Console API
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Enable the **Google Search Console API** (also called "Search Console API" in the library)
3. Create **OAuth 2.0 Client ID** → Application type: **Desktop app**
4. Download the credentials JSON → save as `credentials_gsc.json` in project root
5. Run `python3 tools/gsc_index_check.py` — browser will open for auth
6. After auth, `token_gsc.json` is saved automatically for future runs

### IndexNow (already done)
- Key generated and stored in `.env` as `INDEXNOW_KEY`
- Key verification file: `f70119434670469993d064858ed05e92.txt` in project root
- Must be deployed (committed and pushed) so Bing can verify it

---

## After Publishing a New Article

Run these two commands after every new article is published and deployed:

```bash
# 1. Ping Bing/Yandex immediately (instant)
python3 tools/indexnow_ping.py --url https://peptiderevealed.com/articles/NEW-ARTICLE.html

# 2. Check Google indexing status (if curious — not required every time)
python3 tools/gsc_index_check.py --url https://peptiderevealed.com/articles/NEW-ARTICLE.html
```

## Weekly Audit

Run a full indexing audit weekly to catch pages that aren't getting indexed:

```bash
# Full sitemap check
python3 tools/gsc_index_check.py --save

# Ping all URLs to Bing/Yandex (safe to do periodically)
python3 tools/indexnow_ping.py --sitemap
```

Results are saved to `.tmp/gsc/` for comparison over time.

---

## Interpreting GSC Results

| Status | Meaning | Action |
|--------|---------|--------|
| **PASS** | Indexed and appearing in search | None needed |
| **NEUTRAL** – "Discovered, not indexed" | Google knows about it but hasn't crawled yet | Wait. Build backlinks. Request indexing manually in GSC UI. |
| **NEUTRAL** – "Crawled, not indexed" | Google crawled it but chose not to index | Content quality issue or low authority. Improve content, add backlinks, strengthen internal linking. |
| **FAIL** – "Blocked by robots.txt" | robots.txt is blocking crawl | Check robots.txt for accidental blocks |
| **FAIL** – "URL not on Google" | Not in Google's index at all | Request indexing in GSC UI |

---

## Tips for Faster Indexing

1. **Manual request indexing**: 10-12 URLs/day via GSC URL Inspection tool. Prioritize your best content.
2. **Internal links**: Every new article should link to 3-4 existing articles AND be linked from existing articles.
3. **Backlinks**: Even 1-2 external links dramatically speed up indexing for new domains.
4. **Sitemap**: Keep `sitemap.xml` updated (it already is — publishing checklist covers this).
5. **IndexNow**: Handles Bing/Yandex instantly. Google doesn't support it but the other engines are free traffic.
6. **Patience**: New domains typically take 2-8 weeks for full indexing. Google is slow but will get there.
