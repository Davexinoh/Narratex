#!/usr/bin/env python3
"""
briefing.py
Narratex OpenClaw Skill — Briefing Formatter

Reads narrative JSON from stdin or file and prints
a formatted intelligence briefing for OpenClaw to deliver.

Usage:
  python3 briefing.py                    # reads from stdin
  python3 briefing.py --top 3            # top 3 only
  python3 briefing.py --stage emerging   # filter by stage
  python3 briefing.py --tokens           # token radar view
  python3 briefing.py --file data.json   # read from file
"""

import json
import sys
import argparse
from datetime import datetime, timezone


STAGE_ICONS = {
    "emerging":  "↗",
    "rising":    "↑",
    "peak":      "▲",
    "declining": "↘",
}

STAGE_LABELS = {
    "emerging":  "EMERGING",
    "rising":    "RISING",
    "peak":      "PEAK",
    "declining": "DECLINING",
}


def confidence_bar(score, width=8):
    filled = round((score / 100) * width)
    return "█" * filled + "░" * (width - filled)


def format_briefing(data, top=None, stage_filter=None, tokens_view=False):
    narratives = data.get("narratives", [])
    source     = data.get("source", "unknown")

    # Use the actual data timestamp — not the current wall clock time
    fetched_at = data.get("fetched_at", "")
    if fetched_at:
        try:
            dt = datetime.fromisoformat(fetched_at)
            timestamp = dt.strftime("%H:%M UTC · %b %d")
        except ValueError:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC · %b %d")
    else:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC · %b %d")

    if stage_filter:
        narratives = [n for n in narratives if n.get("stage") == stage_filter]

    if top:
        narratives = narratives[:top]

    source_label = {
        "live":           "🟢 LIVE — NARRATEX API",
        "binance_square": "🟡 DIRECT — BINANCE SQUARE",
        "seed":           "🔵 CACHED — SEED DATA",
        "demo":           "🔵 CACHED — DEMO DATA",
    }.get(source, f"● {source.upper()}")

    lines = []
    lines.append("📡 NARRATEX INTELLIGENCE BRIEFING")
    lines.append("━" * 38)
    lines.append(source_label)
    lines.append(f"Updated: {timestamp}")
    lines.append("")

    if tokens_view:
        token_map = {}
        for n in data.get("narratives", []):
            for t in n.get("tokens", []):
                if t not in token_map or token_map[t]["score"] < n["confidence"]:
                    token_map[t] = {"score": n["confidence"], "narrative": n["name"]}

        top_tokens = sorted(token_map.items(), key=lambda x: x[1]["score"], reverse=True)[:10]
        lines.append("🎯 TOKEN RADAR — TOP 10")
        lines.append("")
        for i, (token, info) in enumerate(top_tokens, 1):
            bar = confidence_bar(info["score"], 6)
            lines.append(f"  {i:2}. {token:<8} {bar} {info['score']}%  ({info['narrative']})")
        lines.append("")
        lines.append("━" * 38)
        lines.append("🔗 https://davexinoh.github.io/Narratex/dashboard.html")
        return "\n".join(lines)

    lines.append("TOP NARRATIVES")
    lines.append("")

    for i, n in enumerate(narratives, 1):
        name       = n["name"]
        conf       = n["confidence"]
        mentions   = n.get("mentions_growth", 0)
        engagement = n.get("engagement_growth", 0)
        stage      = n.get("stage", "rising")
        tokens     = n.get("tokens", [])[:5]
        bar        = confidence_bar(conf)
        icon       = STAGE_ICONS.get(stage, "↑")
        label      = STAGE_LABELS.get(stage, "RISING")

        lines.append(f"{i}. {name:<26} {bar} {conf}%  {icon} {label}")
        lines.append(f"   Tokens: {' · '.join(tokens)}")
        lines.append(f"   Mentions +{mentions}% · Engagement +{engagement}%")
        lines.append("")

    lines.append("━" * 38)
    lines.append("LIFECYCLE STAGES")

    all_narratives = data.get("narratives", [])
    for stage in ["emerging", "rising", "peak", "declining"]:
        group = [n["name"] for n in all_narratives if n.get("stage") == stage]
        if group:
            icon  = STAGE_ICONS[stage]
            label = STAGE_LABELS[stage]
            lines.append(f"  {icon} {label:<12} {' · '.join(group)}")

    lines.append("")
    lines.append("━" * 38)
    lines.append("🔗 https://davexinoh.github.io/Narratex/dashboard.html")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top",    type=int, default=None)
    parser.add_argument("--stage",  type=str, default=None,
                        choices=["emerging", "rising", "peak", "declining"])
    parser.add_argument("--tokens", action="store_true")
    parser.add_argument("--file",   type=str, default=None)
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            data = json.load(f)
    else:
        raw  = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {"narratives": [], "source": "seed"}

    print(format_briefing(data, top=args.top, stage_filter=args.stage, tokens_view=args.tokens))


if __name__ == "__main__":
    main()
