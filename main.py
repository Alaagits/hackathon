#!/usr/bin/env python3
"""Deepfake Risk Pipeline — entry point."""

import argparse
import os
import sys

from db.database import init_db
from pipeline.discovery import discover_persons
from pipeline.prioritize import prioritize_persons
from pipeline.baseline import collect_baseline
from pipeline.evidence import collect_evidence
from pipeline.score import score_candidates
from pipeline.report import generate_report


def _banner(step: int, total: int, msg: str) -> None:
    print(f"\n[{step}/{total}] {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score public videos of company executives for deepfake risk signals."
    )
    parser.add_argument("--company", required=True, help="Company name (e.g. 'Acme Corp')")
    parser.add_argument("--domain", required=True, help="Company domain (e.g. 'acme.com')")
    parser.add_argument(
        "--top-n", type=int, default=5, metavar="N",
        help="Number of top executives to analyse (default: 5)",
    )
    parser.add_argument(
        "--db", default=os.path.join("data", "pipeline.db"),
        help="SQLite database path (default: data/pipeline.db)",
    )
    parser.add_argument(
        "--skip-voice", action="store_true",
        help="Skip audio download and voice-match scoring (faster, no yt-dlp/resemblyzer needed)",
    )
    args = parser.parse_args()

    youtube_key = os.environ.get("YOUTUBE_API_KEY")
    apollo_key = os.environ.get("APOLLO_API_KEY")

    if not youtube_key:
        print("ERROR: YOUTUBE_API_KEY environment variable is not set.")
        print("       Get one at: https://console.cloud.google.com/ (YouTube Data API v3)")
        sys.exit(1)

    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    db = init_db(args.db)

    # ── Stage 1-2: Discovery ──────────────────────────────────────────────────
    _banner(1, 6, f"Discovering executives at {args.company} ({args.domain}) …")
    persons = discover_persons(
        db,
        company=args.company,
        domain=args.domain,
        apollo_key=apollo_key,
        youtube_key=youtube_key,
    )

    if not persons:
        print("\nNo persons found. Add APOLLO_API_KEY or check company/domain spelling.")
        sys.exit(1)

    print(f"      {len(persons)} person(s) discovered.")

    # ── Stage 3: Prioritise ───────────────────────────────────────────────────
    _banner(2, 6, f"Prioritising top {args.top_n} by exposure score …")
    top_persons = prioritize_persons(db, persons, args.top_n)
    for p in top_persons:
        print(f"      {p['name']:30s}  {(p.get('title') or ''):35s}  exposure={p['exposure_score']}")

    # ── Stage 4a: Baseline ────────────────────────────────────────────────────
    _banner(3, 6, "Collecting baseline clips (known-real ground truth) …")
    collect_baseline(
        db,
        persons=top_persons,
        youtube_key=youtube_key,
        skip_download=args.skip_voice,
    )

    # ── Stage 4b: Evidence ────────────────────────────────────────────────────
    _banner(4, 6, "Collecting candidate videos to analyse …")
    collect_evidence(
        db,
        persons=top_persons,
        youtube_key=youtube_key,
        skip_download=args.skip_voice,
    )

    # ── Stage 5: Score ────────────────────────────────────────────────────────
    _banner(5, 6, "Scoring candidates …")
    results = score_candidates(db, top_persons, skip_voice=args.skip_voice)
    print(f"      Scored {len(results)} video(s).")

    # ── Stage 6: Report ───────────────────────────────────────────────────────
    _banner(6, 6, "Generating report …")
    report_path = generate_report(db, args.company, results)
    print(f"      Report: {report_path}")

    # ── Summary ───────────────────────────────────────────────────────────────
    high = sum(1 for r in results if r["risk_level"] == "high")
    medium = sum(1 for r in results if r["risk_level"] == "medium")
    print(f"\nDone.  🔴 {high} high-risk  🟡 {medium} medium-risk  (see report for details)\n")


if __name__ == "__main__":
    main()
