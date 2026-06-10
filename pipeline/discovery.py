"""Stage 1-2: Discover public employees (executives) for a given company."""

import re
import time
import sqlite3
from typing import Optional

import requests
from googleapiclient.discovery import build

from db.database import upsert_person

EXECUTIVE_SENIORITIES = ["c_suite", "vp", "director", "owner"]
TITLE_SEARCH_TERMS = ["CEO", "CFO", "CTO", "COO", "President", "founder", "CMO", "CISO"]

# Regex to pull "Firstname Lastname" style names from plain text
_NAME_RE = re.compile(r'\b([A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20}){1,2})\b')


def discover_persons(
    db: sqlite3.Connection,
    company: str,
    domain: str,
    apollo_key: Optional[str] = None,
    youtube_key: Optional[str] = None,
) -> list[dict]:
    persons = []

    if apollo_key:
        persons = _discover_via_apollo(db, company, domain, apollo_key)
        if persons:
            print(f"      [Apollo] Found {len(persons)} person(s).")
            return persons
        print("      [Apollo] No results — falling back.")

    if youtube_key:
        persons = _discover_via_youtube(db, company, domain, youtube_key)
        if persons:
            print(f"      [YouTube fallback] Found {len(persons)} candidate(s) — verify manually.")
            return persons

    print("      WARNING: No persons found. Add APOLLO_API_KEY for reliable discovery.")
    return persons


# ---------------------------------------------------------------------------
# Apollo.io
# ---------------------------------------------------------------------------

def _discover_via_apollo(
    db: sqlite3.Connection,
    company: str,
    domain: str,
    api_key: str,
) -> list[dict]:
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload = {
        "q_organization_domains_list": [domain],
        "person_seniorities": EXECUTIVE_SENIORITIES,
        "page": 1,
        "per_page": 25,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        print(f"      [Apollo] Request failed: {exc}")
        return []

    persons = []
    for person in data.get("people", []):
        name = (person.get("name") or "").strip()
        title = (person.get("title") or "").strip()
        if not name:
            continue
        pid = upsert_person(
            db,
            name=name,
            title=title,
            company=company,
            domain=domain,
            linkedin_url=person.get("linkedin_url"),
            apollo_id=person.get("id"),
        )
        persons.append({
            "id": pid,
            "name": name,
            "title": title,
            "company": company,
            "domain": domain,
            "linkedin_url": person.get("linkedin_url"),
        })

    return persons


# ---------------------------------------------------------------------------
# YouTube title-based fallback
# ---------------------------------------------------------------------------

def _discover_via_youtube(
    db: sqlite3.Connection,
    company: str,
    domain: str,
    youtube_key: str,
) -> list[dict]:
    youtube = build("youtube", "v3", developerKey=youtube_key)
    seen: set[str] = set()
    persons: list[dict] = []

    for term in TITLE_SEARCH_TERMS:
        query = f'"{company}" {term}'
        try:
            resp = (
                youtube.search()
                .list(part="snippet", q=query, type="video", maxResults=10, order="relevance")
                .execute()
            )
        except Exception as exc:
            print(f"      [YouTube discovery] search error for '{query}': {exc}")
            continue

        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            text_blob = f"{snippet.get('title', '')} {snippet.get('description', '')}"
            for match in _NAME_RE.finditer(text_blob):
                name = match.group(1)
                # Skip obvious non-names: company name tokens, single-word matches caught by 2+word req
                if any(w.lower() in name.lower() for w in company.split()):
                    continue
                if name in seen:
                    continue
                seen.add(name)
                pid = upsert_person(db, name=name, title=term, company=company, domain=domain)
                persons.append({
                    "id": pid,
                    "name": name,
                    "title": term,
                    "company": company,
                    "domain": domain,
                })

        time.sleep(0.5)

    # Deduplicate by id
    seen_ids: set[int] = set()
    deduped = []
    for p in persons:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            deduped.append(p)
    return deduped
