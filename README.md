# Deepfake Risk Pipeline

An enterprise-grade defensive OSINT platform that protects company employees and executives from impersonation and deepfake attacks. The system combines three independent modules into one unified risk dashboard.

---

## Modules

| Module | Entry point | What it does |
|--------|-------------|--------------|
| **YouTube Deepfake Scanner** | `python main.py` | Discovers executives, collects public videos, scores each for deepfake signals |
| **Facebook Fake Profile Detector** | `python app.py` | Web UI — scores a Facebook profile for authenticity using 9 behavioural signals |
| **Media Analysis Backend** | `uvicorn backend.app:app` | FastAPI service — runs face match, deepfake detection, watermark/provenance, and audio analysis on any uploaded image or video |

---

## Quick start

### 1 — Install dependencies

```bash
pip install -r requirements.txt

# Optional: voice matching for the YouTube scanner (requires ffmpeg on PATH)
pip install yt-dlp resemblyzer

# Optional: face matching for the media backend
pip install deepface
```

### 2 — Set API keys (YouTube scanner only)

```bash
export YOUTUBE_API_KEY="..."    # Google Cloud Console → YouTube Data API v3 (free)
export APOLLO_API_KEY="..."     # Apollo.io free tier (optional, improves discovery)
```

### 3 — Run

```bash
# YouTube deepfake scanner (CLI)
python main.py --company "Acme Corp" --domain "acme.com" --top-n 5

# Web UI — Facebook detector + media analyser frontend (port 5000)
python app.py

# Media analysis API (port 8000)
uvicorn backend.app:app --reload --port 8000
```

---

## Project structure

```
main.py                        YouTube scanner entry point
app.py                         Flask web UI (port 5000)

pipeline/                      YouTube scanner stages
  discovery.py                 Stage 1-2: find public executives
  prioritize.py                Stage 3:   score by exposure
  baseline.py                  Stage 4a:  collect known-real clips
  evidence.py                  Stage 4b:  collect candidate videos
  score.py                     Stage 5:   multi-signal scoring + voice match
  report.py                    Stage 6:   Markdown + JSON report

facebook/                      Facebook fake-profile detector
  profile.py                   FacebookProfile model
  detector.py                  FakeProfileDetector — score, classify, reasons
  mock_search.py               Deterministic mock profile lookup

backend/                       Media analysis FastAPI backend (port 8000)
  app.py                       POST /analyze-media endpoint
  risk_engine.py               Weighted final risk score
  video_frame_extractor.py     Extract frames from video for analysis
  face_match/
    face_matcher.py            DeepFace comparison vs employees_db/
  deepfake_detection/
    deepfake_detector.py       Deepfake suspicion scorer (placeholder → HuggingFace)
  watermark/
    media_analyzer.py          Orchestrates all watermark checks
    metadata_checker.py        EXIF / video metadata extraction
    c2pa_checker.py            C2PA content credentials readiness stub
    synthid_checker.py         SynthID detection readiness stub
  audio_analysis/
    audio_checker.py           Audio risk scorer for video files
  employees_db/                Add <name>/ folders with reference photos here

db/
  database.py                  SQLite schema + deduplication helpers
data/
  pipeline.db                  Auto-created SQLite DB
reports/
  *.md / *.json                Generated scanner reports
templates/
  index.html                   Facebook detector UI
  analyze.html                 Media analyser UI (served at /analyze)
```

---

## YouTube scanner — scoring breakdown

| Signal | Max | Notes |
|--------|-----|-------|
| Source credibility | 30 | New channel, suspicious title keywords |
| Upload recency | 20 | How recently the video was uploaded |
| Metadata | 20 | Missing description/tags, view anomalies |
| Voice match | 30 | Resemblyzer cosine similarity vs baseline |

- Score ≥ 70 → 🔴 high
- Score 45–69 → 🟡 medium
- Score 20–44 → 🟢 low
- Score < 20 → ⚪ unverified

Official/verified channels are capped at 15 regardless of other signals.

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--company` | *(required)* | Company name |
| `--domain` | *(required)* | Company domain (e.g. `acme.com`) |
| `--top-n` | `5` | Number of executives to analyse |
| `--db` | `data/pipeline.db` | SQLite database path |
| `--skip-voice` | off | Skip audio download + voice matching |

---

## Facebook fake-profile detector — scoring breakdown

| Criterion | Condition | Risk score |
|-----------|-----------|----------:|
| No profile picture | `has_profile_picture == False` | +20 |
| Very few friends | `friends_count < 10` | +20 |
| Very few posts | `posts_count < 5` | +20 |
| Missing basic info | `has_basic_info == False` | +15 |
| Suspicious name | `suspicious_name == True` | +10 |
| Low interactions | `low_interactions == True` | +15 |
| No mutual connections | `no_mutual_connections == True` | +10 |
| Employee info mismatch | `employee_info_match == False` | +25 |
| Abnormal posting frequency | `posts_per_hour >= 10` | +20 |

- Score ≥ 60 → LIKELY_FAKE
- Score 30–59 → SUSPICIOUS
- Score 0–29 → LIKELY_REAL

---

## Media analysis backend — scoring breakdown

The `POST /analyze-media` endpoint returns scores from four modules combined into one final risk score.

| Module | Weight | Notes |
|--------|-------:|-------|
| Deepfake detection | 30% | Visual deepfake suspicion score |
| Face mismatch | 25% | `100 − face_match_score` |
| Watermark & provenance | 25% | Missing metadata, no C2PA, SynthID signal |
| Audio analysis | 20% | Voice/lip-sync suspicion (video only) |

- Final score ≥ 70 → high risk
- Final score 40–69 → medium risk
- Final score < 40 → low risk

### Face matching setup

Add reference photos under `backend/employees_db/`:

```
backend/employees_db/
  nir_cohen/
    photo1.jpg
    photo2.jpg
  sara_bebar/
    photo.jpg
```

### Watermark & provenance notes

> Our Watermark & Provenance layer is ready for SynthID integration once enterprise API access is available. For the MVP, metadata checks and C2PA readiness are implemented.

> Watermark detection alone cannot prove whether media is real or fake — it is one signal alongside face verification, deepfake detection, and audio analysis.

---

## Ethics

- Public data only. No private profiles scraped.
- Results are risk signals, not verdicts. Always verify manually.
- Do not use to accuse individuals without independent confirmation.
