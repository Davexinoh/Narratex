# Narratex — Architecture

## Overview

```
Binance Square (public feed)
        ↓
  collector.py         ← fetches posts, scores against narrative seeds
        ↓
  extractor.py         ← clusters signals into named narratives
        ↓
  momentum.py          ← computes weighted confidence scores
        ↓
  api.py (Flask)       ← serves /api/narratives with 5-min cache
        ↓
  Render (hosting)     ← auto-deploys from main branch
        ↓
  dashboard.js         ← fetches API, renders all visualizations
        ↓
  GitHub Pages         ← hosts static frontend
```

## Confidence Score Formula

```
confidence = (mentions_growth × 0.50)
           + (engagement_growth × 0.30)
           + (volume_growth × 0.20)
```

Each signal is normalized to 0–100 before weighting.

- **mentions_growth** — how fast a narrative is being discussed on Binance Square
- **engagement_growth** — depth of discussion (likes + comments + shares)
- **volume_growth** — market confirmation proxy (trading activity)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/narratives` | All narratives, sorted by confidence |
| GET | `/api/narratives/:name` | Single narrative detail |
| GET | `/api/status` | Cache metadata |

Query params on `/api/narratives`:
- `?refresh=true` — bypass cache and re-run pipeline
- `?min_confidence=N` — filter by minimum confidence

## Data Flow

1. `collector.py` fetches 5 pages of Binance Square posts
2. Each post is scored against 8 narrative seed keyword lists
3. `extractor.py` aggregates scored posts into narrative buckets
4. `momentum.py` normalizes signals and computes weighted confidence
5. Results cached in memory for 5 minutes
6. Falls back to `data/narratives.json` if API is unreachable

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Backend | Python 3.11, Flask, Gunicorn |
| Data source | Binance Square public feed |
| Backend hosting | Render |
| Frontend hosting | GitHub Pages |
