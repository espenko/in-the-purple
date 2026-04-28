# In The Purple — Deployment Guide

## What's in this folder

```
index.html              ← The app (deploy this to Netlify)
data.json               ← All player + news data (edit this to update content)
netlify.toml            ← Netlify config (auto-detected, nothing to change)
scripts/
  update_portal.py      ← Python script run by the GitHub Action daily
.github/
  workflows/
    daily-update.yml    ← GitHub Action — runs at 4pm CT every day
```

---

## Step 1 — Get it live on Netlify (15 minutes)

1. Go to [github.com](https://github.com) and create a free account if you don't have one
2. Click **New repository** → name it `in-the-purple` → set to **Public** → Create
3. Upload ALL files from this folder into the repo (drag and drop into the GitHub web interface)
4. Go to [netlify.com](https://netlify.com) → **Sign up free** → **Add new site** → **Import from Git**
5. Connect your GitHub account → select `in-the-purple` → click **Deploy**
6. In ~60 seconds your site is live at a URL like `https://in-the-purple.netlify.app`

**Optional custom URL:** In Netlify → Site configuration → Domain management → Add a custom domain. Domains cost ~$12/year at [Namecheap](https://namecheap.com).

---

## Step 2 — Set up the 4pm CT auto-update

The GitHub Action needs one secret to call the Claude API:

1. In your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your Anthropic API key (get one free at [console.anthropic.com](https://console.anthropic.com))
5. Click **Add secret**

The Action will now run automatically every day at 4pm CT during portal season (April–May). It:
- Scrapes Inside NU and On3 Wildcat Report
- Asks Claude to identify new commits, visits, offers, and rumors
- Updates `data.json` and commits it back to GitHub
- Netlify detects the commit and redeploys the site in ~30 seconds

---

## Step 3 — Manual updates (fastest option)

You don't need to wait for the daily run. Any time there's breaking news:

1. Open `data.json` in GitHub (click the file → click the pencil edit icon)
2. Add a new player to the `"players"` array or news item to the `"news"` array
3. Click **Commit changes**
4. Netlify redeploys automatically in ~30 seconds

### Adding a player manually

Copy this template into the `"players"` array (paste at the top, before the first `{`):

```json
{
  "name": "Player Name",
  "school": "Previous School",
  "height": "6'X\"",
  "position": "SG",
  "status": "rumor",
  "eligibility": "2 yrs left",
  "stats": [
    { "label": "PPG", "value": "14.2" },
    { "label": "RPG", "value": "3.1" },
    { "label": "3PT%", "value": "38.5%" }
  ],
  "looksLikeName": "Former NU Player 'YY",
  "looksLikeSub": "Short comparison note",
  "sources": "Inside NU",
  "date": "Apr 28"
},
```

Status options: `"confirmed"` `"visited"` `"offered"` `"rumor"`

---

## Sharing the link

Once deployed, share your Netlify URL directly:
- Text it to family and friends
- Add it to your group chat
- Bookmark it on your phone

The site works on mobile — no app download needed.
