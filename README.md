# Deepfake Risk Pipeline

Defensive OSINT tool that scores public videos of company executives for deepfake risk signals.

## Setup

```bash
pip install -r requirements.txt

# Optional: voice matching (requires ffmpeg on PATH)
pip install yt-dlp resemblyzer
```

## API keys needed

```bash
export YOUTUBE_API_KEY="..."    # Google Cloud Console → YouTube Data API v3 (free)
export APOLLO_API_KEY="..."     # Apollo.io free tier (optional, improves discovery)
```

## Run

```bash
python main.py --company "Acme Corp" --domain "acme.com" --top-n 5
```

Report is saved to `reports/Acme_Corp_<timestamp>.md` + `.json`.

## Project structure

```
main.py                  Entry point
db/
  database.py            SQLite schema + deduplication helpers
pipeline/
  discovery.py           Stage 1→2: find public employees
  prioritize.py          Stage 3:   score by exposure
  baseline.py            Stage 4a:  collect known-real clips (ground truth)
  evidence.py            Stage 4b:  collect candidate videos
  score.py               Stage 5:   multi-signal scoring + voice match
  report.py              Stage 6:   Markdown + JSON report
data/
  pipeline.db            Auto-created SQLite DB
reports/
  *.md / *.json          Generated reports
```

## Scoring breakdown

| Signal           | Max  | Notes                                      |
|------------------|------|--------------------------------------------|
| Source credibility | 30 | New channel, suspicious title keywords     |
| Upload recency    | 20  | How recently the video was uploaded        |
| Metadata          | 20  | Missing description/tags, view anomalies   |
| Voice match       | 30  | Resemblyzer cosine similarity vs baseline  |

- Score ≥ 70 → 🔴 high
- Score 45–69 → 🟡 medium
- Score 20–44 → 🟢 low
- Score < 20 → ⚪ unverified

Official/verified channels are capped at 15 regardless of other signals.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--company` | *(required)* | Company name |
| `--domain` | *(required)* | Company domain (e.g. `acme.com`) |
| `--top-n` | `5` | Number of executives to analyse |
| `--db` | `data/pipeline.db` | SQLite database path |
| `--skip-voice` | off | Skip audio download + voice matching (faster) |

## Ethics

- Public data only. No private profiles scraped.
- Results are risk signals, not verdicts. Always verify manually.
- Do not use to accuse individuals without independent confirmation.
