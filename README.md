# Narratex

**Crypto narrative intelligence powered by Binance Square.**

Narratex monitors Binance Square in real time and detects which crypto narratives are gaining momentum — before the crowd arrives. Instead of tracking individual tokens, it tracks the *themes* driving the market.

🔗 **Dashboard:** https://davexinoh.github.io/Narratex/dashboard.html
🤖 **Telegram Bot:** https://t.me/Narratexbot

---

## What It Does

Most tools track prices. Narratex tracks narratives.

It scans Binance Square posts, scores them against 8 narrative clusters, and surfaces which themes are accelerating — along with the tokens most likely to benefit.

**Example output:**

```
AI Infrastructure     ████████ 84%  ↑ RISING
Tokens: FET · TAO · RNDR · AKT
Mentions +91% · Engagement +88%

Solana Ecosystem      ███████░ 79%  ▲ PEAK
Tokens: SOL · JUP · RAY · BONK

DePIN Compute         ██████░░ 67%  ↗ EMERGING
Tokens: HNT · IOTX · FIL · AKT
```

---

## Architecture

```
Binance Square (public feed)
        ↓
collector.py      — fetches posts, scores against narrative seeds
        ↓
extractor.py      — clusters signals into named narrative buckets
        ↓
momentum.py       — weighted confidence scoring + lifecycle stage
        ↓
api.py (Flask)    — /api/narratives with 5-min cache
        ↓
Render            — always-on backend deployment
        ↓
dashboard.js      — fetches API, renders 9-section dashboard
        ↓
GitHub Pages      — static frontend
```

---

## Confidence Score

Each narrative is scored using three signals, normalized to 0–100 and weighted:

| Signal | Weight | Source |
|--------|--------|--------|
| Mentions Growth | 50% | Binance Square post frequency |
| Engagement Growth | 30% | Likes + comments + shares |
| Volume Momentum | 20% | Binance public ticker (24hr change) |

---

## Lifecycle Stages

Each narrative is assigned a stage based on confidence and signal velocity:

| Stage | Meaning |
|-------|---------|
| ↗ EMERGING | New narrative forming, low confidence but accelerating |
| ↑ RISING | Gaining momentum, worth watching |
| ▲ PEAK | Maximum narrative strength |
| ↘ DECLINING | Losing momentum |

---

## Dashboard — 9 Pages

| # | Page | Description |
|---|------|-------------|
| 01 | Narrative Leaderboard | All narratives ranked by confidence |
| 02 | Lifecycle Tracker | Narratives grouped by market cycle stage |
| 03 | Narrative Heatmap | Color-coded confidence grid |
| 04 | Signal Breakdown | Bar chart of all three signals per narrative |
| 05 | Token Radar | Top 10 tokens by narrative strength |
| 06 | Active Narratives | Full signal breakdown with token lists |
| 07 | Capital Rotation | Liquidity flow between narrative sectors |
| 08 | Narrative Token Map | Every narrative cluster with all associated tokens |
| 09 | Predictions | Emerging narratives scored by signal acceleration |

---

## Telegram Bot

**@Narratexbot** delivers live narrative intelligence on demand.

| Command | Response |
|---------|----------|
| `/start` | Introduction and command list |
| `/briefing` | Full narrative intelligence briefing |
| `/leaderboard` | Top narratives ranked by confidence |
| `/rotation` | Capital flow between narrative sectors |
| `/predictions` | Predicted emerging narratives |
| `/tokens <narrative>` | Tokens associated with a specific narrative |
| `/refresh` | Force re-fetch of live Binance Square data |

Or ask anything in plain text — the bot uses AI to answer based on live narrative data.

---

## OpenClaw Skill

Narratex ships as an OpenClaw-compatible skill in `skill/`.

```bash
# Install
git clone https://github.com/Davexinoh/Narratex ~/.openclaw/skills/narratex

# Or via ClawHub
clawhub install narratex
```

Trigger phrases: `narrative briefing`, `what's trending`, `token radar`, `what's emerging`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data source | Binance Square public feed |
| Market data | Binance REST API (`/api/v3/ticker/24hr`) |
| Backend | Python 3.11, Flask, Gunicorn |
| Frontend | HTML, CSS, JavaScript, Chart.js 4.4.2 |
| Bot | python-telegram-bot 21.5 |
| Backend hosting | Render |
| Frontend hosting | GitHub Pages |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/narratives` | All narratives sorted by confidence |
| GET | `/api/narratives/<name>` | Single narrative detail |
| GET | `/api/status` | Cache metadata |

Query params on `/api/narratives`:
- `?refresh=true` — bypass cache and re-run pipeline
- `?min_confidence=N` — filter by minimum confidence score

---

## Repo Structure

```
Narratex/
├── backend/
│   ├── api.py           — Flask API
│   ├── collector.py     — Binance Square signal collector
│   ├── extractor.py     — Narrative clustering engine
│   ├── momentum.py      — Confidence scoring + lifecycle stage
│   └── seeds.py         — Single source of truth for narrative seeds
├── data/
│   └── narratives.json  — Seed/fallback data
├── skill/
│   ├── SKILL.md         — OpenClaw skill definition
│   └── scripts/
│       ├── fetch_narratives.py
│       └── briefing.py
├── bot.py               — Telegram bot (runs on Render)
├── dashboard.html       — 9-page dashboard
├── dashboard.js         — Data fetching and rendering
├── index.html           — Landing page
├── styles.css           — All styles
├── render.yaml          — Render deployment config
└── requirements.txt
```

---

## Deployment

**Backend (Render):**
- Auto-deploys from `main` branch
- Single Gunicorn worker (required for in-memory cache)
- `TELEGRAM_TOKEN` and `ANTHROPIC_API_KEY` set as env vars

**Frontend (GitHub Pages):**
- Static files served from repo root
- No build step required

---

Built for the **Binance OpenClaw AI Hackathon 2026** · by Davexinoh and Xavier
