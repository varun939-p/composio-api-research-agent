"""Pass-1 extractor. Rules only — no model call — so the misses are reproducible.

This is intentionally not the final answer. It reads fetched page text and
guesses the schema fields. The human adjudication pass compares against it.
"""

from __future__ import annotations

import re

AUTH_PATTERNS = [
    ("OAuth2", re.compile(r"\boauth\s*2(\.0)?\b|\boauth2\b", re.I)),
    ("OAuth2", re.compile(r"\bauthorization code\b|\b3LO\b|\bconnected app\b", re.I)),
    ("API key", re.compile(r"\bapi[\s_-]?key\b|\bprivate[\s_-]?app\b|\bx-api-key\b|\baccess token\b.*\bsettings\b", re.I)),
    ("API key", re.compile(r"\bpersonal access token\b|\bprivate integration token\b|\bapi token\b", re.I)),
    ("Basic", re.compile(r"\bbasic auth(?:entication)?\b|\bhttp basic\b", re.I)),
    ("token", re.compile(r"\bbearer token\b|\bbot token\b", re.I)),
    ("other", re.compile(r"\bhmac\b|\bsignature\b|\bkey pair\b|\bjwt\b", re.I)),
]

GATE_PATTERNS = [
    ("partnership", re.compile(r"\bpartner(ship)? program\b|\bapproved partner\b|\bcontact sales\b|\brequest access\b|\baccount manager\b", re.I)),
    ("app-review", re.compile(r"\bapp review\b|\bdeveloper token\b|\bbusiness verification\b|\bproduction access\b", re.I)),
    ("enterprise", re.compile(r"\benterprise (plan|only|customers)\b|\blicen[sc]e required\b", re.I)),
    ("paid", re.compile(r"\bpaid plan\b|\bsubscription required\b|\bupgrade your plan\b", re.I)),
]

SELF_SERVE_PATTERNS = [
    re.compile(r"\bfree (developer|trial|account|tier)\b", re.I),
    re.compile(r"\bcreate (an |a )?(api key|token|app)\b", re.I),
    re.compile(r"\bsign up\b", re.I),
    re.compile(r"\bdeveloper (account|edition|portal|dashboard)\b", re.I),
    re.compile(r"\bno (credit card|approval)\b", re.I),
]


def _hits(text: str, patterns) -> list[str]:
    found = []
    for label, pattern in patterns:
        if pattern.search(text) and label not in found:
            found.append(label)
    return found


def extract_record(app: dict, pages: list[dict]) -> dict:
    usable = [p for p in pages if p.get("status") == 200 and len(p.get("text") or "") > 400]
    blob = "\n\n".join((p.get("text") or "")[:12_000] for p in usable[:3])
    lowered = blob.lower()

    if not usable:
        return {
            "id": app["id"],
            "app_name": app["app_name"],
            "auth_method": "Not found",
            "access_type": "Could not verify",
            "api_surface": "Could not verify",
            "mcp": "Could not verify",
            "buildability_verdict": "Could not verify",
            "evidence_url": "",
            "pass": "heuristic-v1",
            "note": "No fetched page with enough text.",
        }

    auth = []
    for label, pattern in AUTH_PATTERNS:
        if pattern.search(blob) and label not in auth:
            auth.append(label)
    # Bearer-only is usually the transport, not a distinct scheme, if we already have a scheme.
    if len(auth) > 1 and "token" in auth and any(a in auth for a in ("OAuth2", "API key")):
        auth = [a for a in auth if a != "token"]

    gates = _hits(blob, GATE_PATTERNS)
    self_serve = any(p.search(blob) for p in SELF_SERVE_PATTERNS)
    if gates and not self_serve:
        access = "Gated (" + ", ".join(gates) + ")"
    elif self_serve and not gates:
        access = "Self-serve (free/trial)"
    elif self_serve and gates:
        access = "Self-serve with a gate (" + ", ".join(gates) + ")"
    else:
        access = "Could not verify"

    styles = []
    if re.search(r"\bgraphql\b", lowered):
        styles.append("GraphQL")
    if re.search(r"\brest\b|\brestful\b|/api/v\d", lowered):
        styles.append("REST")
    if not styles:
        styles.append("Could not verify")

    mcp = "none found on fetched pages"
    if re.search(r"\bmcp server\b|\bmodel context protocol\b", lowered):
        mcp = "MCP mentioned"
        styles.append("MCP")

    evidence = usable[0].get("final_url") or usable[0].get("url")
    if access.startswith("Could not") or auth == []:
        verdict = "Could not verify"
    elif access.startswith("Gated") and "partnership" in access:
        verdict = "No — partnership/sales gate"
    elif "Could not verify" in styles:
        verdict = "Conditional — API style unclear"
    else:
        verdict = "Yes"

    return {
        "id": app["id"],
        "app_name": app["app_name"],
        "category_id": app["category_id"],
        "auth_method": ", ".join(auth) if auth else "Not found",
        "access_type": access,
        "api_surface": ", ".join(styles),
        "mcp": mcp,
        "buildability_verdict": verdict,
        "evidence_url": evidence,
        "pass": "heuristic-v1",
        "pages_used": [p.get("final_url") or p.get("url") for p in usable[:3]],
    }
