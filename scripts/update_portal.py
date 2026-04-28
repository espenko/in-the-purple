"""
update_portal.py
Scrapes Inside NU, On3, and 247Sports for Northwestern MBB portal news,
then uses Claude to parse and summarize new items into data.json.
Run daily by the GitHub Action at 4pm CT.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
import anthropic

# ── Config ──────────────────────────────────────────────────────────────────

DATA_FILE = "data.json"
CT = ZoneInfo("America/Chicago")

SOURCES = [
    {
        "name": "Inside NU",
        "url": "https://www.insidenu.com/northwestern-mens-basketball/64230/northwestern-mens-basketball-portal-tracker-2026",
        "selector": "div.c-entry-content p",
    },
    {
        "name": "On3 Wildcat Report",
        "url": "https://www.on3.com/sites/wildcat-report/news/2026-northwestern-basketball-transfer-tracker-5/",
        "selector": "div.article-body p",
    },
]

SEARCH_TERMS = [
    "northwestern basketball transfer",
    "northwestern wildcats portal 2026",
    "northwestern mbb commit",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"lastUpdated": "", "players": [], "news": []}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_page_text(url, selector):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; InThePurpleBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = soup.select(selector)
        return "\n\n".join(p.get_text(" ", strip=True) for p in paragraphs[:40])
    except Exception as e:
        print(f"  Warning: could not fetch {url}: {e}")
        return ""


def scrape_all_sources():
    combined = []
    for src in SOURCES:
        print(f"  Fetching {src['name']}...")
        text = fetch_page_text(src["url"], src["selector"])
        if text:
            combined.append(f"=== SOURCE: {src['name']} ===\n{text}")
    return "\n\n".join(combined)


# ── Claude integration ───────────────────────────────────────────────────────

def ask_claude(raw_text, existing_data):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    existing_titles = [n["title"] for n in existing_data.get("news", [])]
    existing_players = [p["name"] for p in existing_data.get("players", [])]

    prompt = f"""You are the editor of "In The Purple", a Northwestern men's basketball transfer portal tracker.

Below is raw scraped text from Inside NU, On3 Wildcat Report, and 247Sports covering the 2026 portal cycle.

Your job:
1. Extract any NEW portal developments not already in our tracker.
2. Update existing player statuses if they have changed (e.g., rumor → visited → offered → confirmed).
3. Return a JSON object with two arrays: "newPlayers" and "newNews".

EXISTING PLAYERS (do not duplicate): {json.dumps(existing_players)}
EXISTING NEWS TITLES (do not duplicate): {json.dumps(existing_titles)}

For each NEW player, return:
{{
  "name": "Full Name",
  "school": "Previous School",
  "height": "6'X\"",
  "position": "PG/SG/SF/PF/C/G/F",
  "status": "confirmed|visited|offered|rumor",
  "eligibility": "X yr left|Multi-yr|Graduate",
  "stats": [
    {{"label": "PPG", "value": "X.X"}},
    {{"label": "RPG or APG or FG% or 3PT%", "value": "X.X"}}
  ],
  "looksLikeName": "Former NU Player 'YY",
  "looksLikeSub": "One-line comparison note",
  "sources": "Source name(s)",
  "date": "Mon DD"
}}

For each NEW news item, return:
{{
  "title": "Headline",
  "status": "confirmed|visited|offered|rumor",
  "source": "Source name",
  "date": "Mon DD",
  "body": "One or two sentence summary of the news."
}}

For any EXISTING player whose status has changed, include them in "updatedPlayers" with their name and new status:
{{
  "name": "Player Name",
  "status": "new_status"
}}

If there is nothing new, return empty arrays.
Return ONLY valid JSON. No markdown, no explanation.

--- SCRAPED TEXT ---
{raw_text[:8000]}
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```$", "", raw)
    return json.loads(raw)


# ── Merge updates into data.json ─────────────────────────────────────────────

def merge_updates(data, updates):
    changed = False

    # Add new players
    existing_names = {p["name"].lower() for p in data["players"]}
    for player in updates.get("newPlayers", []):
        if player["name"].lower() not in existing_names:
            data["players"].insert(0, player)
            print(f"  + Added player: {player['name']}")
            changed = True

    # Update existing player statuses
    status_order = {"rumor": 0, "offered": 1, "visited": 2, "confirmed": 3}
    for update in updates.get("updatedPlayers", []):
        for player in data["players"]:
            if player["name"].lower() == update["name"].lower():
                old = player["status"]
                new = update["status"]
                if status_order.get(new, -1) > status_order.get(old, -1):
                    player["status"] = new
                    print(f"  ↑ Updated {player['name']}: {old} → {new}")
                    changed = True

    # Add new news items (prepend so newest is first)
    existing_titles = {n["title"].lower() for n in data["news"]}
    for item in updates.get("newNews", []):
        if item["title"].lower() not in existing_titles:
            data["news"].insert(0, item)
            print(f"  + Added news: {item['title'][:60]}...")
            changed = True

    # Update last-updated timestamp
    now_ct = datetime.now(tz=CT)
    data["lastUpdated"] = now_ct.strftime("%-B %-d") + _ordinal(now_ct.day)

    return data, changed


def _ordinal(n):
    if 11 <= n <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("In The Purple — Daily Portal Update")
    print(f"  Running at {datetime.now(tz=CT).strftime('%B %d, %Y %I:%M %p CT')}")

    # Load existing data
    data = load_data()
    print(f"  Existing players: {len(data['players'])}, news items: {len(data['news'])}")

    # Scrape sources
    print("Scraping sources...")
    raw_text = scrape_all_sources()

    if not raw_text.strip():
        print("  No content scraped. Updating timestamp only.")
        now_ct = datetime.now(tz=CT)
        data["lastUpdated"] = now_ct.strftime("%-B %-d") + _ordinal(now_ct.day)
        save_data(data)
        return

    # Ask Claude to parse updates
    print("Asking Claude to parse updates...")
    try:
        updates = ask_claude(raw_text, data)
    except Exception as e:
        print(f"  Claude error: {e}")
        print("  Updating timestamp only.")
        now_ct = datetime.now(tz=CT)
        data["lastUpdated"] = now_ct.strftime("%-B %-d") + _ordinal(now_ct.day)
        save_data(data)
        return

    # Merge into data
    print("Merging updates...")
    data, changed = merge_updates(data, updates)

    # Save
    save_data(data)
    if changed:
        print(f"  data.json updated — {len(data['players'])} players, {len(data['news'])} news items.")
    else:
        print("  No new content found. Timestamp updated.")


if __name__ == "__main__":
    main()
