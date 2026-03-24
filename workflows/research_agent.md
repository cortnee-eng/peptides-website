# Research Agent

## Objective
Surface content opportunities daily by monitoring what people are asking, sharing, and discussing across Reddit, news, and social media. Turn raw signals into actionable article topics and social post ideas.

## Tool
`tools/research_scout.py` — scrapes Reddit and Google News for peptide/GLP-1 intelligence

## When to Run
- Daily (ideal: morning, before content planning)
- On demand: `python tools/research_scout.py`
- Reddit only: `python tools/research_scout.py --channel reddit`
- Save to file: `python tools/research_scout.py --save`

## Data Sources

### Reddit (live now)
Monitors 13 subreddits across 3 categories:
- **GLP-1**: r/Ozempic, r/Mounjaro, r/GLP1users, r/Semaglutide, r/tirzepatide
- **Peptides**: r/PeptideResearch, r/Peptides, r/sarms
- **Health**: r/loseit, r/SkincareAddiction, r/30PlusSkinCare, r/Biohackers

### Google News (live now)
Monitors queries: peptides, GLP-1 semaglutide, tirzepatide Mounjaro, BPC-157, peptide regulation FDA, GHK-Cu copper peptide

### TikTok / Instagram (future — requires API or scraping tool)
Not yet implemented. When added:
- Monitor #ozempic, #mounjaro, #glp1, #peptides hashtags
- Track trending audio/formats in the health niche
- Identify viral hooks to adapt

## How to Read the Output

### Reddit Intelligence
- **High Engagement**: Posts with 20+ upvotes or 15+ comments. These topics resonate — consider writing about them or creating social content.
- **Questions People Are Asking**: Direct article ideas. If many people ask the same question, there's search demand.
- **Newest Discussions**: Emerging topics before they trend. Early content wins.

### News Headlines
- Timely hooks for social posts or article updates
- Regulatory changes that affect the legal article
- New studies to cite in existing articles

### Content Ideas
- Auto-generated from the data above
- Article ideas come from Reddit questions
- Social post angles come from trending discussions
- Hot topic frequency shows what the audience cares about right now

## How to Act on It
1. **Article ideas**: Cross-reference with keyword difficulty. If a Reddit question has search volume + low KD, write the article.
2. **Social posts**: Take a trending Reddit topic and create a TikTok/Reel about it within 24-48 hours.
3. **Community engagement**: If you see a high-engagement thread you can add value to, go comment (following the distribution workflow rules).
4. **Article updates**: If news breaks that affects an existing article, update it.

## Scheduling (Future)
```
Run tools/research_scout.py --save every morning at 6:00 AM PT.
Summarize the top 5 content opportunities and post to [channel TBD].
If any topic appears in 3+ subreddits, flag it as high priority.
```

## Saved Briefings
When run with `--save`, output goes to `.tmp/research/briefing_YYYY-MM-DD.txt`
These accumulate over time and can be reviewed for patterns.
