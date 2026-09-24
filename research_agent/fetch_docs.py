"""Fetch official-doc seeds and keep short evidence excerpts.

Usage:
    python -m research_agent.fetch_docs
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from research_agent.catalog import APPS, category_name
from research_agent.extract import extract_record
from research_agent.http_util import fetch, html_to_text, page_title

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


def fetch_one(app_id: int, url: str) -> dict:
    result = fetch(url, timeout=22)
    text = html_to_text(result.get("text") or "")
    return {
        "app_id": app_id,
        "url": url,
        "final_url": result.get("final_url"),
        "status": result.get("status"),
        "error": result.get("error"),
        "title": page_title(result.get("text") or ""),
        "chars": len(text),
        "excerpt": excerpt(text) if result.get("status") == 200 else "",
        "text_sample": text[:6000] if result.get("status") == 200 else "",
    }


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [(app["id"], url) for app in APPS for url in app["seed_urls"]]
    print(f"fetching {len(jobs)} seed URLs for {len(APPS)} apps")
    pages: dict[int, list[dict]] = {app["id"]: [] for app in APPS}
    done = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(fetch_one, app_id, url): (app_id, url) for app_id, url in jobs}
        for fut in as_completed(futures):
            page = fut.result()
            pages[page["app_id"]].append(page)
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")

    records = []
    for app in APPS:
        app_pages = sorted(pages[app["id"]], key=lambda p: app["seed_urls"].index(p["url"]))
        ok = [p for p in app_pages if p["status"] == 200 and p["chars"] > 200]
        records.append({
            "id": app["id"],
            "app_name": app["app_name"],
            "category": category_name(app["category_id"]),
            "category_id": app["category_id"],
            "website": app["website"],
            "hint": app["hint"],
            "search_queries": app["search_queries"],
            "pages": [
                {k: p[k] for k in ("url", "final_url", "status", "error", "title", "chars", "excerpt")}
                for p in app_pages
            ],
            "ok_count": len(ok),
        })
        # Persist a fuller text sample for the extractor without bloating fetched.json.
        sample_path = RAW / f"{app['id']:03d}.json"
        sample_path.write_text(json.dumps({
            "id": app["id"],
            "pages": [
                {"url": p["url"], "final_url": p["final_url"], "status": p["status"],
                 "title": p["title"], "text": p.get("text_sample", "")}
                for p in app_pages
            ],
        }), encoding="utf-8")

    OUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")

    pass1 = []
    for app in APPS:
        sample = json.loads((RAW / f"{app['id']:03d}.json").read_text(encoding="utf-8"))
        pass1.append(extract_record(app, sample["pages"]))
    PASS1.write_text(json.dumps(pass1, indent=2), encoding="utf-8")
    print(f"wrote {PASS1}")

    failed = [r for r in records if r["ok_count"] == 0]
    print(f"apps with zero usable pages: {len(failed)}")
    for r in failed:
        print(f"  {r['id']:3d} {r['app_name']}")


if __name__ == "__main__":
    main()
