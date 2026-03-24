"""
Setup Trello board for PeptideRevealed 30-day content distribution plan.

Creates:
- Board: "PeptideRevealed Distribution"
- Lists for each channel + weekly sprints
- Cards with specific action items, due dates, checklists, and labels

Usage: python tools/setup_trello_board.py
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TRELLO_API_KEY")
TOKEN = os.getenv("TRELLO_TOKEN")
BASE = "https://api.trello.com/1"

def auth():
    return {"key": API_KEY, "token": TOKEN}

def post(endpoint, **kwargs):
    params = {**auth(), **kwargs}
    r = requests.post(f"{BASE}/{endpoint}", params=params)
    r.raise_for_status()
    return r.json()

def create_board(name):
    return post("boards", name=name, defaultLists="false",
                prefs_background="green", desc="30-day content distribution plan for peptiderevealed.com")

def create_label(board_id, name, color):
    return post(f"boards/{board_id}/labels", name=name, color=color)

def create_list(board_id, name, pos):
    return post(f"boards/{board_id}/lists", name=name, pos=pos)

def create_card(list_id, name, desc="", due=None, label_ids=None, pos="bottom"):
    params = {"name": name, "desc": desc, "pos": pos, "idList": list_id}
    if due:
        params["due"] = due.strftime("%Y-%m-%dT12:00:00.000Z")
    if label_ids:
        params["idLabels"] = ",".join(label_ids)
    return post("cards", **params)

def add_checklist(card_id, name, items):
    cl = post(f"cards/{card_id}/checklists", name=name)
    for item in items:
        post(f"checklists/{cl['id']}/checkItems", name=item)
    return cl

# ── Dates ──────────────────────────────────────────────────────
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
def day(n): return today + timedelta(days=n)

# ── Board Setup ────────────────────────────────────────────────
print("Creating board...")
board = create_board("PeptideRevealed Distribution")
board_id = board["id"]
print(f"Board created: {board['shortUrl']}")

# ── Labels ─────────────────────────────────────────────────────
print("Creating labels...")
labels = {}
label_defs = [
    ("Reddit", "orange"),
    ("TikTok/Reels", "purple"),
    ("Pinterest", "pink"),
    ("Facebook", "blue"),
    ("SEO", "green"),
    ("Email Capture", "red"),
    ("Chief of Staff", "black"),
]
for name, color in label_defs:
    l = create_label(board_id, name, color)
    labels[name] = l["id"]

# ── Lists ──────────────────────────────────────────────────────
print("Creating lists...")
list_names = [
    "Backlog",
    "Week 1 (Mar 24-30)",
    "Week 2 (Mar 31-Apr 6)",
    "Week 3 (Apr 7-13)",
    "Week 4 (Apr 14-20)",
    "In Progress",
    "Done",
    "Blocked / Waiting",
]
lists = {}
for i, name in enumerate(list_names):
    l = create_list(board_id, name, (i + 1) * 1000)
    lists[name] = l["id"]

# ── Helper ─────────────────────────────────────────────────────
def card(list_name, name, desc="", due=None, label_names=None, checklist=None, checklist_name="Tasks"):
    lbl_ids = [labels[n] for n in (label_names or [])]
    c = create_card(lists[list_name], name, desc=desc, due=due, label_ids=lbl_ids)
    if checklist:
        add_checklist(c["id"], checklist_name, checklist)
    return c

# ══════════════════════════════════════════════════════════════
#  WEEK 1 — Foundation (Mar 24-30)
# ══════════════════════════════════════════════════════════════
print("Creating Week 1 cards...")
W1 = "Week 1 (Mar 24-30)"

card(W1, "Set up email capture on meal planner",
     desc="Add email gate on save/export: 'Enter your email to save your plan and get weekly GLP-1 nutrition tips.' Don't gate the tool itself, gate the save.",
     due=day(2), label_names=["Email Capture"],
     checklist=["Add email input to meal planner save flow",
                "Set up email list (ConvertKit/Mailchimp/Beehiiv)",
                "Test signup flow end to end",
                "Add exit-intent popup to top 3 GLP-1 articles"])

card(W1, "Internal linking pass — GLP-1 cluster",
     desc="Tightly interlink all GLP-1 content:\n- glp-1-peptides.html -> appetite cycle + protein timing\n- glp-1-appetite-cycle.html -> meal planner + protein timing\n- protein-timing-glp1.html -> appetite cycle + meal planner + GLP-1 overview\n- meal-planner.html -> all three GLP-1 articles\n- Every peptide profile -> injury recovery hub piece",
     due=day(3), label_names=["SEO"],
     checklist=["Link glp-1-peptides -> appetite cycle + protein timing",
                "Link appetite-cycle -> meal planner + protein timing",
                "Link protein-timing -> appetite cycle + meal planner + GLP-1 overview",
                "Link meal-planner -> all 3 GLP-1 articles",
                "Link BPC-157, TB-500, GHK-Cu -> injury recovery hub",
                "Verify all links work"])

card(W1, "Sign up for HARO / Connectively / Qwoted",
     desc="Register as a source on journalist query platforms. Set up alerts for: peptides, GLP-1, semaglutide, weight loss, biohacking.",
     due=day(3), label_names=["SEO"],
     checklist=["Sign up for Connectively", "Sign up for Qwoted", "Set keyword alerts", "Draft bio/credentials blurb"])

card(W1, "Reddit — establish presence (NO links this week)",
     desc="Goal: 10-15 genuine, helpful comments across target subs. Build karma and credibility. DO NOT post any links to peptiderevealed.com this week.",
     due=day(7), label_names=["Reddit"],
     checklist=[
         "Join r/Ozempic, r/Mounjaro, r/GLP1users, r/loseit, r/Semaglutide, r/PeptideResearch",
         "Comment on 2-3 'hungry on day 5-6' posts in r/Ozempic (share appetite cycle knowledge)",
         "Comment on 'what should I eat' threads in r/Mounjaro (30g protein-first framework)",
         "Answer GLP-1 questions in r/loseit factually (evidence-based, not pro or anti)",
         "Reply to nausea/side-effect threads in r/Semaglutide with timing strategies",
         "Reach 10+ helpful comments total across all subs",
     ])

card(W1, "Pinterest — set up account and boards",
     desc="Create Pinterest business account. Set up boards and create first 5 pins.",
     due=day(5), label_names=["Pinterest"],
     checklist=[
         "Create Pinterest business account for Peptide Revealed",
         "Create boards: 'GLP-1 Meal Planning', 'Peptide Research', 'Health & Wellness'",
         "Design pin template in Canva (1000x1500, forest green + cream, brand colors)",
         "Pin 1: GLP-1 Meal Planner — Free Tool -> meal-planner.html",
         "Pin 2: What to Eat on Ozempic Day-by-Day -> glp-1-appetite-cycle.html",
         "Pin 3: High Protein Meals for GLP-1 -> protein-timing-glp1.html",
         "Pin 4: Peptide Beginner's Guide -> what-are-peptides-beginners-guide.html",
         "Pin 5: BPC-157 Research Guide -> bpc-157-guide.html",
         "Repin 10-15 related health pins to seed boards",
     ])

card(W1, "TikTok/Reels — film first 3 videos",
     desc="Talking head, 30-60 sec each, text overlays. Set up Linktree with email capture as first link.",
     due=day(7), label_names=["TikTok/Reels"],
     checklist=[
         "Set up Linktree (email signup first, then meal planner, then articles)",
         "Film Video 1: 'The GLP-1 hunger curve no one talks about' (whiteboard appetite curve)",
         "Film Video 2: 'Why you're losing muscle on Ozempic' (30g protein-first rule)",
         "Film Video 3: 'Peptide Sciences just shut down' (news-style, 45 sec)",
         "Edit with text overlays + captions",
         "Post all 3 to TikTok AND Instagram Reels",
     ])

card(W1, "Facebook — join groups and start commenting",
     desc="Join 5-8 GLP-1 groups with 10K+ members. Comment only this week — no links.",
     due=day(7), label_names=["Facebook"],
     checklist=[
         "Search and join: 'Ozempic Support', 'Mounjaro Weight Loss', 'GLP-1 Medications', 'Semaglutide Support Group'",
         "Read group rules for each",
         "Comment on 2-3 threads/day with helpful advice (appetite, protein, timing)",
         "DO NOT post any links yet",
     ])

# ══════════════════════════════════════════════════════════════
#  WEEK 2 — Build Momentum (Mar 31 - Apr 6)
# ══════════════════════════════════════════════════════════════
print("Creating Week 2 cards...")
W2 = "Week 2 (Mar 31-Apr 6)"

card(W2, "Reddit — continue commenting + 1 text post (no link)",
     desc="Keep commenting 2-3x/day. Post ONE text-only value post — share knowledge, no link to site yet.",
     due=day(14), label_names=["Reddit"],
     checklist=[
         "Continue 2-3 helpful comments/day across subs",
         "Write text post in r/Ozempic or r/Mounjaro: share appetite cycle pattern you've observed (no link)",
         "Track which comments get upvotes — note what resonates",
     ])

card(W2, "TikTok/Reels — post videos 1-3, film 4-5",
     desc="Post the 3 videos from Week 1. Film 2 more.",
     due=day(12), label_names=["TikTok/Reels"],
     checklist=[
         "Post Video 1, 2, 3 (stagger: Mon, Wed, Fri)",
         "Film Video 4: '3 peptides athletes use for injury recovery' (BPC-157, TB-500, GHK-Cu)",
         "Film Video 5: 'Is it legal to buy peptides in 2026?' (legal landscape)",
         "Edit with text overlays",
     ])

card(W2, "Pinterest — create 5 more pins",
     desc="Continue building pin library. Mix article pins with meal planning content.",
     due=day(12), label_names=["Pinterest"],
     checklist=[
         "Pin 6: GHK-Cu Benefits -> ghk-cu-copper-peptide.html",
         "Pin 7: Injury Recovery Peptides Compared -> best-peptides-for-injury-recovery.html",
         "Pin 8: GLP-1 Injection Day Meal Plan -> meal-planner.html",
         "Pin 9: Protein Timing on Semaglutide -> protein-timing-glp1.html",
         "Pin 10: Are Peptides Legal? 2026 Guide -> are-peptides-legal.html",
         "Repin 10+ related pins",
     ])

card(W2, "Facebook — keep commenting, build relationships",
     desc="Continue daily helpful comments. Start recognizing regulars and building rapport.",
     due=day(14), label_names=["Facebook"],
     checklist=[
         "15-20 min/day, 5 days this week",
         "Reply to people who responded to your previous comments",
         "Note which groups are most active and receptive",
     ])

card(W2, "HARO/Connectively — first pitches",
     desc="Respond to 2-3 journalist queries. Pitch 1 podcast.",
     due=day(14), label_names=["SEO"],
     checklist=[
         "Respond to 2-3 relevant HARO/Connectively queries",
         "Research 5 health/biohacking podcasts (smaller shows, Huberman-adjacent)",
         "Pitch 1 podcast: topic 'What the science actually says about peptides'",
     ])

# ══════════════════════════════════════════════════════════════
#  WEEK 3 — Start Linking (Apr 7-13)
# ══════════════════════════════════════════════════════════════
print("Creating Week 3 cards...")
W3 = "Week 3 (Apr 7-13)"

card(W3, "Reddit — share links (carefully)",
     desc="You've built credibility. Now share 2 links this week — always with substantial text in the post.",
     due=day(21), label_names=["Reddit"],
     checklist=[
         "Post in r/Ozempic: 'I mapped out how GLP-1 appetite suppression works day-by-day' — full text + link at bottom to appetite cycle article",
         "Post in r/Mounjaro or r/GLP1users: 'I built a free meal planner for people on GLP-1s' — describe what it does + link to meal-planner.html",
         "Continue 2-3 comments/day (maintain ratio of value vs. self-links)",
         "DO NOT post same link to multiple subs on same day",
     ])

card(W3, "TikTok/Reels — post videos 4-5, film 6-7",
     due=day(19), label_names=["TikTok/Reels"],
     checklist=[
         "Post Video 4, 5 (Tue, Thu)",
         "Film Video 6: 'What I eat on injection day vs day 6' (show two meal plates)",
         "Film Video 7: 'The copper peptide that grew 1000% in search' (GHK-Cu)",
         "Check analytics — which videos got traction? Double down on that style",
     ])

card(W3, "Pinterest — 5 more pins + optimize",
     due=day(19), label_names=["Pinterest"],
     checklist=[
         "Create 5 new pins (variations on best performers + new articles)",
         "Check Pinterest analytics — which pins getting impressions?",
         "Optimize descriptions with search terms (ozempic meal plan, glp-1 what to eat)",
         "Repin 10+ related pins",
     ])

card(W3, "Facebook — share meal planner when relevant",
     desc="You've been helpful for 2 weeks. Now share the tool when someone asks about meal planning.",
     due=day(21), label_names=["Facebook"],
     checklist=[
         "When someone asks 'what should I eat' — share meal planner link with context",
         "Keep it natural: 'I was struggling with the same thing so I built this free planner...'",
         "Continue daily commenting (don't go link-heavy)",
     ])

card(W3, "Pitch 2 podcasts + HARO responses",
     due=day(21), label_names=["SEO"],
     checklist=[
         "Pitch 2 more podcasts",
         "Respond to 2-3 HARO/Connectively queries",
         "Check if any pitches from Week 2 got responses",
     ])

# ══════════════════════════════════════════════════════════════
#  WEEK 4 — Expand & Evaluate (Apr 14-20)
# ══════════════════════════════════════════════════════════════
print("Creating Week 4 cards...")
W4 = "Week 4 (Apr 14-20)"

card(W4, "Reddit — 2-3 more link posts (broaden topics)",
     desc="Expand beyond GLP-1 into peptide topics. Share Peptide Sciences shutdown, GHK-Cu, legal guide.",
     due=day(28), label_names=["Reddit"],
     checklist=[
         "r/PeptideResearch: 'Peptide Sciences closed — here's what happened' + link",
         "r/SkincareAddiction or r/30PlusSkinCare: GHK-Cu content (if relevant thread exists)",
         "r/loseit: 'After researching peptide legality for months...' text post + link to legal article",
         "Continue daily comments to maintain credibility ratio",
     ])

card(W4, "TikTok/Reels — post videos 6-7 + review performance",
     due=day(26), label_names=["TikTok/Reels"],
     checklist=[
         "Post Video 6, 7",
         "Review all 7 videos: which got views? Which drove profile clicks?",
         "Plan next 4 videos based on what worked",
     ])

card(W4, "Pinterest — continue pinning + first analytics review",
     due=day(26), label_names=["Pinterest"],
     checklist=[
         "Create 5 more pins",
         "Full analytics review: impressions, clicks, saves by pin",
         "Identify top 3 performers — create 2-3 variations of each",
     ])

card(W4, "Facebook — share articles when contextually relevant",
     due=day(28), label_names=["Facebook"],
     checklist=[
         "Share 1-2 article links in groups where relevant threads come up",
         "Continue daily commenting",
         "Note which groups drive clicks (check analytics if possible)",
     ])

card(W4, "30-day performance review + plan Month 2",
     desc="Review all channels. What worked? What flopped? Where are signups coming from? Plan next 30 days.",
     due=day(28), label_names=["Chief of Staff"],
     checklist=[
         "Pull email signup numbers by source",
         "Reddit: total karma earned, best-performing posts, any removed posts?",
         "TikTok: total views, profile clicks, best video",
         "Pinterest: impressions, clicks, top pins",
         "Facebook: qualitative assessment — which groups most receptive?",
         "Google Search Console: any movement in rankings?",
         "Decision: which 2 channels to double down on for Month 2?",
         "Decision: what content angles to create more of?",
     ])

card(W4, "SEO — evaluate rankings and double down",
     due=day(28), label_names=["SEO"],
     checklist=[
         "Check Search Console: which articles getting impressions?",
         "Any keywords on page 2 that need a push?",
         "Continue HARO responses (2-3/week)",
         "Follow up on podcast pitches",
     ])

# ── Backlog ────────────────────────────────────────────────────
print("Creating backlog cards...")

card("Backlog", "Set up content upgrade — downloadable GLP-1 meal plan PDF",
     desc="Create a printable PDF meal plan gated behind email. Place on appetite cycle and protein timing articles.",
     label_names=["Email Capture"],
     checklist=["Design 1-page printable meal plan PDF",
                "Set up download gate (email required)",
                "Add CTA to glp-1-appetite-cycle.html",
                "Add CTA to protein-timing-glp1.html"])

card("Backlog", "GHK-Cu skincare subreddit strategy",
     desc="r/SkincareAddiction and r/30PlusSkinCare are high-value targets for GHK-Cu content. Needs careful approach — skincare subs are strict.",
     label_names=["Reddit"],
     checklist=["Read sub rules thoroughly", "Comment helpfully for 1-2 weeks before any link",
                "Identify active GHK-Cu/copper peptide threads", "Share research when contextually appropriate"])

card("Backlog", "Newsletter launch — weekly peptide briefing",
     desc="'The Peptide Briefing' — weekly email with 1 research highlight, 1 practical tip, 1 article link.",
     label_names=["Email Capture"])

card("Backlog", "Chief of Staff agent — daily standup automation",
     desc="Build a scheduled agent that checks the Trello board daily and posts a summary of: what's due today, what's overdue, what was completed yesterday. Eventually runs via claude schedule.",
     label_names=["Chief of Staff"])

card("Backlog", "Backlink tracking spreadsheet",
     desc="Track all backlinks earned: source, date, target page, dofollow/nofollow. Google Sheet.",
     label_names=["SEO"])

print("\n✅ Board setup complete!")
print(f"Board URL: {board['shortUrl']}")
