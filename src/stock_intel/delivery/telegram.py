"""Telegram delivery (Specification.md Section 10/14 — Phase 2 automation).

Sends a short summary matching the planning doc's Telegram layout: top
setups, negative catalysts, and a note that the full report is elsewhere.
Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
"""
from __future__ import annotations

import os

import requests

from ..models.score import DailyReport

_TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def format_report_summary(report: DailyReport, full_report_url: str | None = None) -> str:
    lines = [f"*DAILY MARKET INTELLIGENCE*", f"{report.date.isoformat()}", ""]

    lines.append("*TOP SETUPS*")
    for i, s in enumerate(report.scores[:5], start=1):
        lines.append(f"{i}. {s.ticker} — {s.overall_score:.0f}/100 — {s.action_category.value}")

    if report.negative_catalysts:
        lines.append("")
        lines.append("*NEGATIVE CATALYSTS*")
        for s in report.negative_catalysts[:5]:
            reason = s.why_today[0] if s.why_today else "Weakening thesis"
            lines.append(f"{s.ticker} — {s.overall_score:.0f}/100 — {reason}")

    lines.append("")
    lines.append(
        f"Open full report: {full_report_url}" if full_report_url else "Full report: see daily_report.json"
    )
    return "\n".join(lines)


def format_alerts_message(alerts: list) -> str:
    lines = ["*ALERTS*", ""]
    for a in alerts:
        lines.append(f"• {a.message}")
    return "\n".join(lines)


def send_report_summary(
    report: DailyReport,
    full_report_url: str | None = None,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> None:
    bot_token = bot_token or os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    text = format_report_summary(report, full_report_url)
    resp = requests.post(
        _TELEGRAM_API_URL.format(token=bot_token),
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    resp.raise_for_status()


def send_alerts(
    alerts: list,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> None:
    if not alerts:
        return
    bot_token = bot_token or os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    text = format_alerts_message(alerts)
    resp = requests.post(
        _TELEGRAM_API_URL.format(token=bot_token),
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    resp.raise_for_status()
