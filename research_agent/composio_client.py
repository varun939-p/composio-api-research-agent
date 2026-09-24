"""Composio SDK client for official-doc retrieval.

The fetch path is Composio Search, which needs no second vendor key:

- COMPOSIO_SEARCH_FETCH_URL_CONTENT reads a public page server-side (Exa)
  and returns markdown. A local HTTP client never sees the docs host.
- COMPOSIO_SEARCH_WEB finds a better official URL when that fetch is thin.

Toolkit version is pinned so the parsed fields do not move under us.
Override with COMPOSIO_SEARCH_VERSION if the dashboard shows a newer pin.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEARCH_VERSION = os.environ.get("COMPOSIO_SEARCH_VERSION", "20260903_00")
USER_ID = os.environ.get("COMPOSIO_USER_ID", "api-research")
FETCH_SLUG = "COMPOSIO_SEARCH_FETCH_URL_CONTENT"
SEARCH_SLUG = "COMPOSIO_SEARCH_WEB"


def load_env(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from .env. Existing environment wins."""
    env_path = path or (ROOT / ".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def api_key() -> str:
    load_env()
    key = os.environ.get("COMPOSIO_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "COMPOSIO_API_KEY is not set. Put it in .env (see .env.example) "
            "or export it. Do not commit the key."
        )
    return key


def scrub(message: str) -> str:
    key = os.environ.get("COMPOSIO_API_KEY", "")
    if key:
        message = message.replace(key, "[redacted]")
    return message


def client():
    from composio import Composio

    return Composio(
        api_key=api_key(),
        toolkit_versions={"composio_search": SEARCH_VERSION},
        timeout=120,
    )


def _as_dict(result: Any) -> dict:
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif not isinstance(result, dict):
        result = {
            "data": getattr(result, "data", None),
            "error": getattr(result, "error", None),
            "successful": getattr(result, "successful", None),
        }
    data = result.get("data") or {}
    if isinstance(data, dict) and "response" in data and not any(
        k in data for k in ("results", "citations", "text")
    ):
        inner = data.get("response")
        if isinstance(inner, dict):
            data = inner
    if result.get("successful") is False:
        raise RuntimeError(scrub(str(result.get("error") or "Composio tool returned unsuccessful")))
    if isinstance(data, dict):
        return data
    return {"text": "" if data is None else str(data)}


def execute(composio, slug: str, arguments: dict) -> dict:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = composio.tools.execute(
                slug,
                arguments=arguments,
                user_id=USER_ID,
                version=SEARCH_VERSION,
            )
            return _as_dict(result)
        except Exception as exc:  # noqa: BLE001 — retried, then reported without the key
            last_error = exc
            text = scrub(str(exc))
            if "429" in text or "rate" in text.lower():
                time.sleep(2 ** attempt)
                continue
            if attempt < 2 and any(token in text.lower() for token in ("timeout", "connection", "temporarily")):
                time.sleep(1 + attempt)
                continue
            raise RuntimeError(text) from exc
    raise RuntimeError(scrub(str(last_error)))


def page_text(data: dict, limit: int = 8000) -> str:
    results = data.get("results") or data.get("contents") or []
    if isinstance(results, dict):
        results = [results]
    chunks: list[str] = []
    for page in results:
        if not isinstance(page, dict):
            continue
        text = page.get("text") or page.get("content") or page.get("markdown") or ""
        if text:
            chunks.append(str(text))
    if not chunks:
        for key in ("text", "content", "markdown"):
            if data.get(key):
                chunks.append(str(data[key]))
    return "\n\n".join(chunks)[:limit]


def fetch_url(composio, url: str, max_characters: int = 8000) -> dict:
    data = execute(
        composio,
        FETCH_SLUG,
        {"urls": [url], "text": True, "max_characters": max_characters},
    )
    text = page_text(data, max_characters)
    final_url = url
    results = data.get("results") or []
    if results and isinstance(results[0], dict):
        final_url = results[0].get("url") or results[0].get("id") or url
    return {
        "url": url,
        "final_url": final_url,
        "status": 200 if len(text) > 80 else 204,
        "error": None if text else "Composio Search returned no page text",
        "title": _title(text),
        "chars": len(text),
        "text": text,
        "tool": FETCH_SLUG,
    }


def search_urls(composio, query: str, limit: int = 5) -> list[dict]:
    data = execute(composio, SEARCH_SLUG, {"query": query})
    citations = data.get("citations") or data.get("results") or []
    found = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        href = item.get("url") or item.get("href") or ""
        if not href:
            continue
        found.append({
            "title": item.get("title") or href,
            "url": href,
        })
        if len(found) >= limit:
            break
    return found


def _title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:180]
    return ""
