# narratex-skill 🦞

> Crypto narrative intelligence for OpenClaw — powered by Binance Square.

Detect emerging market narratives before they trend. Get AI-generated intelligence briefings through any messaging platform OpenClaw supports — Telegram, Discord, WhatsApp, and more.

---

## What It Does

Narratex monitors Binance Square in real time and detects which crypto narratives are gaining momentum — before the crowd arrives.

Ask your OpenClaw agent:
- *"What narratives are trending?"*
- *"Give me a narrative briefing"*
- *"What's emerging on Binance Square?"*
- *"Token radar"*
- *"Show me rising narratives"*

And get back a live intelligence briefing like:

```
📡 NARRATEX INTELLIGENCE BRIEFING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 LIVE — NARRATEX API
Updated: 09:15 UTC · Mar 14

TOP NARRATIVES

1. AI Infrastructure           ████████ 84%  ↑ RISING
   Tokens: FET · TAO · RNDR · AKT · WLD
   Mentions +91% · Engagement +88%

2. Solana Ecosystem            ███████░ 79%  ▲ PEAK
   Tokens: SOL · JUP · RAY · BONK · PYTH
   Mentions +86% · Engagement +82%

3. Bitcoin Ecosystem           ███████░ 76%  ▲ PEAK
   Tokens: STX · ORDI · SATS · RUNE · WBTC
   Mentions +84% · Engagement +79%
```

---

## Install

### Via ClawHub (recommended)
```bash
clawhub install narratex
```

### Manual install
```bash
git clone https://github.com/Davexinoh/narratex-skill ~/.openclaw/skills/narratex
```

### Requirements
- Python 3.8+
- No extra packages needed — uses stdlib only

---

## Commands

| What you say | What happens |
|---|---|
| `narrative briefing` | Full intelligence briefing |
| `top narratives` | Top 3 by confidence |
| `what's emerging` | Emerging-stage narratives only |
| `what's rising` | Rising-stage narratives |
| `token radar` | Top 10 tokens by narrative strength |
| `refresh narratives` | Re-fetch live data |

---

## Architecture

```
User asks OpenClaw a question
        ↓
OpenClaw activates narratex skill
        ↓
scripts/fetch_narratives.py runs
        ↓
Hits Narratex API (narratex.onrender.com)
        ↓ (fallback)
Hits Binance Square directly
        ↓ (fallback)
Returns seed data
        ↓
scripts/briefing.py formats output
        ↓
OpenClaw delivers briefing via Telegram/Discord/WhatsApp
```

---

## Signals Tracked

| Signal | Weight |
|---|---|
| Mentions Growth | 50% |
| Engagement Growth | 30% |
| Volume Momentum | 20% |

---

## Lifecycle Stages

| Stage | Meaning |
|---|---|
| ↗ EMERGING | New narrative forming, low confidence |
| ↑ RISING | Gaining momentum, worth watching |
| ▲ PEAK | Maximum narrative strength |
| ↘ DECLINING | Losing momentum |

---

## Full Dashboard

[https://davexinoh.github.io/Narratex/dashboard.html](https://davexinoh.github.io/Narratex/dashboard.html)

---

## Built For

Binance OpenClaw AI Hackathon 2026 · Built by Davexinoh
