"""Fetch official docs through the Composio SDK and score a first pass.

Usage:
    # .env must contain COMPOSIO_API_KEY. It is not read from source.
    python -m research_agent.fetch_docs
    python -m research_agent.fetch_docs --limit 3

Each seed URL is read by COMPOSIO_SEARCH_FETCH_URL_CONTENT. That tool runs
on Composio's side and returns markdown, so this process does not open the
docs host itself. A thin page is retried via COMPOSIO_SEARCH_WEB, then fetched
again. The heuristic in extract.py reads only that text.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from research_agent.catalog import APPS, category_name
from research_agent.composio_client import client, fetch_url, scrub, search_urls
from research_agent.extract import extract_record

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "fetched.json"
PASS1 = ROOT / "data" / "pass1.json"

KEYWORDS = re.compile(
    r"oauth|api key|api token|authentication|authorize|bearer|basic auth|"
    r"graphql|rest |mcp|model context protocol|enterprise|trial|free |"
    r"contact sales|partner",
    re.I,
)


def excerpt(text: str, radius: int = 280, limit: int = 1800) -> str:
    if not text:
        return ""
    hits = list(KEYWORDS.finditer(text))
    if not hits:
        return text[:limit]
    chunks = []
    used = 0
    for hit in hits[:8]:
        start = max(0, hit.start() - radius)
        end = min(len(text), hit.end() + radius)
        piece = text[start:end].strip()
        if piece and piece not in chunks:
            chunks.append(piece)
            used += len(piece)
        if used >= limit:
            break
    return "\n---\n".join(chunks)[:limit]


def _usable(page: dict) -> bool:
    return page.get("status") == 200 and (page.get("chars") or 0) > 400


def fetch_one(composio, app: dict, url: str) -> dict:
    try:
        page = fetch_url(composio, url)
    except Exception as exc:  # noqa: BLE001 — recorded per URL, key already scrubbed
        return {
            "app_id": app["id"],
            "url": url,
            "final_url": url,
            "status": None,
            "error": scrub(str(exc))[:500],
            "title": "",
            "chars": 0,
            "text": "",
            "tool": "COMPOSIO_SEARCH_FETCH_URL_CONTENT",
        }
    page["app_id"] = app["id"]
    if _usable(page):
        return page
    # Second pass: search for the official page, then fetch the best hit.
    query = (app.get("search_queries") or [f"{app['app_name']} API authentication documentation"])[0]
    try:
        hits = search_urls(composio, query)
    except Exception as exc:  # noqa: BLE001
        page["error"] = (page.get("error") or "thin fetch") + "; search failed: " + scrub(str(exc))[:240]
        return page
    for hit in hits:
        if hit["url"] == url:
            continue
        try:
            retry = fetch_url(composio, hit["url"])
        except Exception:
            continue
        retry["app_id"] = app["id"]
        retry["via"] = "COMPOSIO_SEARCH_WEB"
        retry["search_query"] = query
        if _usable(retry):
            return retry
    page["via"] = "COMPOSIO_SEARCH_WEB"
    page["search_hits"] = [h["url"] for h in hits[:5]]
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official docs via the Composio SDK")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N apps. 0 means all.")
    parser.add_argument("--app", type=int, default=0, help="Only this catalog id.")
    args = parser.parse_args()

    apps = APPS
    if args.app:
        apps = [a for a in APPS if a["id"] == args.app]
        if not apps:
            raise SystemExit(f"no app with id {args.app}")
    elif args.limit:
        apps = APPS[: args.limit]

    RAW.mkdir(parents=True, exist_ok=True)
    composio = client()
    print(f"composio search {len(apps)} apps, tool COMPOSIO_SEARCH_FETCH_URL_CONTENT")

    records = []
    pass1 = []
    for index, app in enumerate(apps, start=1):
        pages = []
        for url in app["seed_urls"]:
            page = fetch_one(composio, app, url)
            pages.append(page)
            mark = "ok" if _usable(page) else "thin"
            print(f"  [{index}/{len(apps)}] {app['app_name']} {mark} {page.get('chars', 0)} {url}")
        ok = [p for p in pages if _usable(p)]
        record = {
            "id": app["id"],
            "app_name": app["app_name"],
            "category": category_name(app["category_id"]),
            "category_id": app["category_id"],
            "website": app["website"],
            "hint": app["hint"],
            "search_queries": app["search_queries"],
            "fetcher": "composio.tools.execute COMPOSIO_SEARCH_FETCH_URL_CONTENT",
            "pages": [
                {
                    "url": p["url"],
                    "final_url": p.get("final_url"),
                    "status": p.get("status"),
                    "error": p.get("error"),
                    "title": p.get("title"),
                    "chars": p.get("chars"),
                    "excerpt": excerpt(p.get("text") or "") if _usable(p) else "",
                    "tool": p.get("tool"),
                    "via": p.get("via"),
                }
                for p in pages
            ],
            "ok_count": len(ok),
        }
        records.append(record)
        raw_pages = [
            {
                "url": p["url"],
                "final_url": p.get("final_url"),
                "status": p.get("status"),
                "title": p.get("title"),
                "text": (p.get("text") or "")[:8000],
                "tool": p.get("tool"),
            }
            for p in pages
        ]
        (RAW / f"{app['id']:03d}.json").write_text(
            json.dumps({"id": app["id"], "pages": raw_pages}, indent=2),
            encoding="utf-8",
        )
        pass1.append(extract_record(app, raw_pages))
        # Checkpoint so a long run can be inspected if it is interrupted.
        OUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
        PASS1.write_text(json.dumps(pass1, indent=2), encoding="utf-8")

    failed = [r for r in records if r["ok_count"] == 0]
    print(f"wrote {OUT}")
    print(f"wrote {PASS1}")
    print(f"apps with zero usable pages: {len(failed)}")
    for row in failed:
        print(f"  {row['id']:3d} {row['app_name']}")


if __name__ == "__main__":
    main()
