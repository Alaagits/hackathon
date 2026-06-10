"""Stage 6: Generate Markdown + JSON report."""

import json
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone


_RISK_EMOJI = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
    "unverified": "⚪",
}

_RISK_ORDER = {"high": 0, "medium": 1, "low": 2, "unverified": 3}


def generate_report(
    db: sqlite3.Connection,
    company: str,
    results: list[dict],
) -> str:
    """Write .md and .json reports; return path to the .md file."""
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%S")
    safe_company = re.sub(r"[^\w]+", "_", company)

    os.makedirs("reports", exist_ok=True)
    md_path = os.path.join("reports", f"{safe_company}_{timestamp}.md")
    json_path = md_path.replace(".md", ".json")

    # ---------- JSON ----------
    report_data = {
        "company": company,
        "generated_at": now.isoformat(),
        "voice_matching_enabled": any(r["voice_similarity"] is not None for r in results),
        "summary": _build_summary(results),
        "findings": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, default=str)

    # ---------- Markdown ----------
    md = _render_markdown(company, now, results, report_data["summary"])
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"      JSON: {json_path}")
    return md_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_summary(results: list[dict]) -> dict:
    counts = defaultdict(int)
    persons: set[str] = set()
    for r in results:
        counts[r["risk_level"]] += 1
        persons.add(r["person_name"])
    return {
        "persons_analyzed": len(persons),
        "videos_scored": len(results),
        "high": counts["high"],
        "medium": counts["medium"],
        "low": counts["low"],
        "unverified": counts["unverified"],
    }


def _render_markdown(
    company: str,
    now: datetime,
    results: list[dict],
    summary: dict,
) -> str:
    lines: list[str] = []

    # Header
    lines += [
        f"# Deepfake Risk Report: {company}",
        f"",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Persons analysed:** {summary['persons_analyzed']}  ",
        f"**Videos scored:** {summary['videos_scored']}  ",
        f"",
    ]

    # Executive summary table
    lines += [
        "## Executive Summary",
        "",
        "| Risk Level | Count |",
        "|------------|-------|",
        f"| 🔴 High     | {summary['high']} |",
        f"| 🟡 Medium   | {summary['medium']} |",
        f"| 🟢 Low      | {summary['low']} |",
        f"| ⚪ Unverified | {summary['unverified']} |",
        "",
    ]

    # High-risk callout
    high = [r for r in results if r["risk_level"] == "high"]
    if high:
        lines += ["## ⚠️  High-Risk Findings", ""]
        for r in high:
            lines += [
                f"### {r['person_name']} — *{r['person_title']}*",
                f"- **Video:** [{r['title']}]({r['url']})",
                f"- **Channel:** {r['channel_name']}"
                + (" ✅ verified" if r["channel_verified"] else ""),
                f"- **Score:** {r['total_score']}/100"
                + (f" | voice similarity: {r['voice_similarity']:.3f}" if r["voice_similarity"] is not None else ""),
                f"- **Signals:** {r['notes'] or '—'}",
                "",
            ]

    # Full per-person breakdown
    lines += ["## Full Analysis", ""]

    by_person: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_person[r["person_name"]].append(r)

    for person_name, person_results in by_person.items():
        person_results_sorted = sorted(
            person_results, key=lambda x: _RISK_ORDER.get(x["risk_level"], 9)
        )
        title = person_results[0].get("person_title", "")
        lines += [f"### {person_name}" + (f" — *{title}*" if title else ""), ""]
        lines += [
            "| Risk | Score | Title | Channel | Published | Notes |",
            "|------|-------|-------|---------|-----------|-------|",
        ]
        for r in person_results_sorted:
            emoji = _RISK_EMOJI.get(r["risk_level"], "⚪")
            pub = (r["published_at"] or "")[:10]
            title_cell = f"[{_trunc(r['title'], 45)}]({r['url']})"
            lines.append(
                f"| {emoji} {r['risk_level']} | {r['total_score']} "
                f"| {title_cell} | {_trunc(r['channel_name'], 25)} "
                f"| {pub} | {_trunc(r['notes'], 60)} |"
            )
        lines.append("")

    # Score breakdown legend
    lines += [
        "## Scoring Breakdown",
        "",
        "| Signal | Max | Description |",
        "|--------|-----|-------------|",
        "| Source credibility | 30 | New channel, suspicious title keywords |",
        "| Upload recency | 20 | How recently the video was uploaded |",
        "| Metadata | 20 | Missing description/tags, view anomalies |",
        "| Voice match | 30 | Resemblyzer cosine similarity vs baseline |",
        "",
        "Score ≥ 70 → 🔴 high · 45–69 → 🟡 medium · 20–44 → 🟢 low · < 20 → ⚪ unverified",
        "",
    ]

    # Ethics footer
    lines += [
        "---",
        "",
        "> **Ethics notice:** Results are risk signals based on public data, not verdicts. "
        "Always verify findings manually and do not use to accuse individuals without "
        "independent confirmation.",
        "",
    ]

    return "\n".join(lines)


def _trunc(s: str, n: int) -> str:
    if not s:
        return ""
    s = s.replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"
