"""Tiny HTTP helper. Stdlib only so the agent runs without a virtualenv."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (compatible; ComposioToolkitResearch/1.0; "
    "+https://github.com/varun939-p/composio-api-research-agent)"
)

_SSL = ssl.create_default_context()


def fetch(url: str, timeout: int = 20, method: str = "GET", data: bytes | None = None,
          headers: dict | None = None, max_bytes: int = 1_500_000) -> dict:
    req_headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            raw = resp.read(max_bytes + 1)
            truncated = len(raw) > max_bytes
            body = raw[:max_bytes]
            charset = resp.headers.get_content_charset() or "utf-8"
            text = body.decode(charset, errors="replace")
            return {
                "url": url,
                "final_url": resp.geturl(),
                "status": getattr(resp, "status", 200),
                "content_type": resp.headers.get("Content-Type", ""),
                "text": text,
                "truncated": truncated,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(80_000) if exc.fp else b""
        text = body.decode("utf-8", errors="replace")
        return {
            "url": url,
            "final_url": exc.geturl() if hasattr(exc, "geturl") else url,
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "text": text,
            "truncated": False,
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:  # noqa: BLE001 — record every failure, never crash the loop
        return {
            "url": url,
            "final_url": url,
            "status": 0,
            "content_type": "",
            "text": "",
            "truncated": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def html_to_text(html: str) -> str:
    """Drop scripts/styles and tags. Good enough for keyword extraction."""
    import re

    cleaned = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?is)<!--.*?-->", " ", cleaned)
    cleaned = re.sub(r"(?is)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?is)</(p|div|li|h1|h2|h3|h4|tr|section)>", "\n", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = (
        cleaned.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def page_title(html: str) -> str:
    import re

    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if not match:
        return ""
    return html_to_text(match.group(1))[:180]
