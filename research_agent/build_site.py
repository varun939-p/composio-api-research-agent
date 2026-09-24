"""Render the case study from adjudicated findings, and score the heuristic.

Usage:
    python -m research_agent.build_site
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path

from research_agent.catalog import APPS, CATEGORIES, category_name
from research_agent.extract import extract_record
from research_agent.findings import FINDINGS
from research_agent.sample_pages import SAMPLES

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DOCS = ROOT / "docs"
DATA = ROOT / "data"

VERDICTS = ("Yes", "Conditional", "No", "Could not verify")


def _norm_verdict(value: str) -> str:
    text = (value or "").strip()
    if text in VERDICTS:
        return text
    if text.startswith("Yes"):
        return "Yes"
    if text.startswith("Conditional"):
        return "Conditional"
    if text.startswith("No"):
        return "No"
    if text.startswith("Could not"):
        return "Could not verify"
    return text or "Could not verify"


def extract_v2(app: dict, pages: list[dict]) -> dict:
    """v1 plus rules added after reading the 12-page sample. In-sample, not held-out."""
    row = extract_record(app, pages)
    usable = [p for p in pages if p.get("status") == 200 and len(p.get("text") or "") > 400]
    blob = "\n".join((p.get("text") or "") for p in usable)
    notes = []

    auth = row.get("auth_method") or "Not found"
    if auth in ("", "Not found"):
        found = []
        if re.search(r"\boauth\b", blob, re.I):
            found.append("OAuth2")
        if re.search(r"\bapi[\s_-]?keys?\b", blob, re.I):
            found.append("API key")
        if re.search(r"authorization:\s*bearer|\bbearer\b", blob, re.I):
            found.append("token")
        if found:
            auth = ", ".join(found)
            row["auth_method"] = auth
            notes.append("rescanned auth; v1 missed plurals and bare Bearer.")

    has_auth = auth not in ("", "Not found")
    gate = re.search(
        r"eligible paid plans|commerce advanced|app review|get licenses|"
        r"account admin or card admin|developer token|enterprise tier|"
        r"developer api agreement",
        blob,
        re.I,
    )
    docs_only = re.search(r"does not execute api calls", blob, re.I)
    sales = re.search(r"contact sales", blob, re.I)
    self_path = re.search(
        r"create an account|create a free account|generate one from your|"
        r"free developer account|click create token|pay-as-you-go",
        blob,
        re.I,
    )
    action_mcp = re.search(r"creating, and updating|tools are available for finding", blob, re.I)

    verdict = _norm_verdict(row["buildability_verdict"])
    if docs_only:
        verdict = "Conditional"
        notes.append("MCP page says it does not execute calls.")
    elif has_auth and gate:
        verdict = "Conditional"
        notes.append("gate phrase v1 does not treat as a gate.")
    elif has_auth and sales and self_path:
        verdict = "Conditional"
        notes.append("contact sales is not a hard no when a key path is also on the page.")
    elif has_auth and action_mcp and not gate and not sales:
        verdict = "Yes"
        notes.append("action MCP with standard auth and no gate.")
    elif (
        verdict == "Could not verify"
        and has_auth
        and self_path
        and not gate
        and not sales
        and re.search(r"\brest\b|\bgraphql\b", blob, re.I)
    ):
        verdict = "Yes"
        notes.append("REST or GraphQL plus a signup path.")

    row["buildability_verdict"] = verdict
    row["pass"] = "heuristic-v2"
    row["note"] = " ".join(notes)
    return row


def _page(app: dict, text: str) -> list[dict]:
    return [{
        "status": 200,
        "text": text,
        "url": "sample://excerpt",
        "final_url": "sample://excerpt",
    }]


def score_sample() -> dict:
    apps = {a["id"]: a for a in APPS}
    rows = []
    for sample in SAMPLES:
        app = apps[sample["id"]]
        pages = _page(app, sample["text"])
        v1 = extract_record(app, pages)
        v2 = extract_v2(app, pages)
        human = sample["human_verdict"]
        rows.append({
            "id": sample["id"],
            "app_name": app["app_name"],
            "page": sample["label"],
            "v1": _norm_verdict(v1["buildability_verdict"]),
            "v1_raw": v1["buildability_verdict"],
            "v1_auth": v1["auth_method"],
            "v1_access": v1["access_type"],
            "v2": _norm_verdict(v2["buildability_verdict"]),
            "human": human,
            "human_note": sample["human_note"],
            "v1_hit": _norm_verdict(v1["buildability_verdict"]) == human,
            "v2_hit": _norm_verdict(v2["buildability_verdict"]) == human,
        })
    n = len(rows)
    v1_hits = sum(1 for r in rows if r["v1_hit"])
    v2_hits = sum(1 for r in rows if r["v2_hit"])
    return {
        "n": n,
        "v1_hits": v1_hits,
        "v2_hits": v2_hits,
        "v1_accuracy": round(v1_hits / n, 3) if n else 0,
        "v2_accuracy": round(v2_hits / n, 3) if n else 0,
        "rows": rows,
    }


def transport_stats() -> dict:
    path = DATA / "fetched.json"
    if not path.exists():
        return {"apps": 0, "pages": 0, "ok": 0, "tls": 0}
    data = json.loads(path.read_text())
    pages = 0
    ok = 0
    tls = 0
    for row in data:
        for page in row.get("pages") or []:
            pages += 1
            if page.get("status") == 200 and (page.get("chars") or 0) > 0:
                ok += 1
            err = page.get("error") or ""
            if "TLS" in err or "SSL" in err or "EOF" in err:
                tls += 1
    return {"apps": len(data), "pages": pages, "ok": ok, "tls": tls}


def records() -> list[dict]:
    if set(FINDINGS) != {a["id"] for a in APPS}:
        missing = sorted({a["id"] for a in APPS} - set(FINDINGS))
        extra = sorted(set(FINDINGS) - {a["id"] for a in APPS})
        raise SystemExit(f"findings do not match catalog. missing={missing} extra={extra}")
    out = []
    for app in APPS:
        finding = FINDINGS[app["id"]]
        verdict = finding["buildability_verdict"]
        if verdict not in VERDICTS:
            raise SystemExit(f"{app['app_name']}: bad verdict {verdict}")
        if verdict in ("Yes", "Conditional") and not finding.get("evidence_url"):
            raise SystemExit(f"{app['app_name']}: {verdict} without an evidence URL")
        if finding.get("confidence") == "unverified" and verdict in ("Yes", "No"):
            raise SystemExit(f"{app['app_name']}: unverified row cannot be Yes or No")
        out.append({
            "id": app["id"],
            "app_name": app["app_name"],
            "category": category_name(app["category_id"]),
            "category_id": app["category_id"],
            "category_description": f"{category_name(app['category_id'])} — {finding['one_liner']}",
            "auth_method": finding["auth_method"],
            "access_type": finding["access_type"],
            "api_surface": finding["api_surface"],
            "mcp": finding["mcp"],
            "buildability_verdict": verdict,
            "blocker": finding["blocker"],
            "evidence_url": finding.get("evidence_url") or "",
            "quote": finding.get("quote") or "",
            "confidence": finding.get("confidence") or "unverified",
        })
    return out


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def _tag(verdict: str) -> str:
    kind = {
        "Yes": "yes",
        "Conditional": "cond",
        "No": "no",
        "Could not verify": "unk",
    }[verdict]
    return f'<span class="tag {kind}">{_esc(verdict)}</span>'


def render(rows: list[dict], sample: dict, transport: dict) -> str:
    counts = Counter(r["buildability_verdict"] for r in rows)
    by_cat = {}
    for cat in CATEGORIES:
        subset = [r for r in rows if r["category_id"] == cat["id"]]
        by_cat[cat["id"]] = Counter(r["buildability_verdict"] for r in subset)

    yes = [r for r in rows if r["buildability_verdict"] == "Yes"]
    cond = [r for r in rows if r["buildability_verdict"] == "Conditional"]
    blank = [r for r in rows if r["buildability_verdict"] == "Could not verify"]
    dual = sum(1 for r in rows if " or " in r["auth_method"].lower() or " + " in r["auth_method"])
    action_mcp = [
        r["app_name"] for r in rows
        if "Official action server" in r["mcp"] or "Official MCP documented" in r["mcp"]
        or r["mcp"].startswith("Official server")
        or "Agent API keys are documented" in r["mcp"]
    ]

    def chips(items: list[dict]) -> str:
        return "".join(
            f'<a class="chip" href="#row-{r["id"]}">{_esc(r["app_name"])}'
            f'<small>{_esc(r["category"].split()[0])}</small></a>'
            for r in items
        )

    body_rows = []
    for r in rows:
        evidence = (
            f'<a href="{_esc(r["evidence_url"])}" target="_blank" rel="noopener">Source</a>'
            if r["evidence_url"] else "—"
        )
        quote = f'<q>{_esc(r["quote"])}</q> ' if r["quote"] else ""
        body_rows.append(
            f'<tr id="row-{r["id"]}" data-v="{_esc(r["buildability_verdict"])}" '
            f'data-c="{_esc(r["category_id"])}" data-k="{_esc(r["confidence"])}" '
            f'data-q="{_esc((r["app_name"] + " " + r["auth_method"] + " " + r["blocker"]).lower())}">'
            f'<td class="num">{r["id"]}</td>'
            f'<td class="name">{_esc(r["app_name"])}<span class="conf">{_esc(r["category"])}</span></td>'
            f'<td>{_esc(r["auth_method"])}</td>'
            f'<td>{_esc(r["access_type"])}</td>'
            f'<td>{_esc(r["api_surface"])}<span class="conf">{_esc(r["mcp"])}</span></td>'
            f'<td>{_tag(r["buildability_verdict"])}<span class="conf">{_esc(r["confidence"])}</span></td>'
            f'<td class="blocker">{quote}{_esc(r["blocker"])}</td>'
            f'<td>{evidence}</td>'
            f'</tr>'
        )

    miss_rows = []
    for row in sample["rows"]:
        v1 = "hit" if row["v1_hit"] else "miss"
        v2 = "hit" if row["v2_hit"] else "miss"
        miss_rows.append(
            "<tr>"
            f"<td>{_esc(row['app_name'])}<span class='conf'>{_esc(row['page'])}</span></td>"
            f"<td>{_esc(row['v1'])}</td>"
            f"<td>{_esc(row['v2'])}</td>"
            f"<td>{_esc(row['human'])}</td>"
            f"<td>{v1} → {v2}<span class='conf'>{_esc(row['human_note'])}</span></td>"
            "</tr>"
        )

    missed = [r for r in sample["rows"] if not r["v2_hit"]]
    still = len(missed)
    still_names = (
        " ".join(
            f"{r['app_name']} stayed {r['v2']} against a human {r['human']}."
            for r in missed
        )
        or "Nothing in this 12 remained wrong, which would itself be a reason to distrust the fit."
    )

    short = {
        "crm": "CRM",
        "support": "Support",
        "comms": "Comms",
        "marketing": "Marketing",
        "ecom": "Commerce",
        "data": "Data",
        "dev": "Dev tools",
        "productivity": "Productivity",
        "finance": "Finance",
        "ai": "AI",
    }
    cat_filters = "".join(
        f'<button type="button" data-cat="{_esc(c["id"])}" aria-pressed="false">{_esc(short[c["id"]])}</button>'
        for c in CATEGORIES
    )
    bars = []
    for cat in CATEGORIES:
        bucket = by_cat[cat["id"]]
        total = sum(bucket.values()) or 1
        bars.append(
            '<div class="bar-row">'
            f'<span class="lab">{_esc(short[cat["id"]])}</span>'
            '<div class="track" role="img" aria-label="'
            + _esc(
                f"{short[cat['id']]}: {bucket['Yes']} yes, {bucket['Conditional']} conditional, {bucket['Could not verify']} unverified"
            )
            + '">'
            f'<i class="yes" style="width:{bucket["Yes"] / total * 100:.1f}%"></i>'
            f'<i class="cond" style="width:{bucket["Conditional"] / total * 100:.1f}%"></i>'
            f'<i class="unk" style="width:{bucket["Could not verify"] / total * 100:.1f}%"></i>'
            "</div>"
            f'<span class="n">{bucket["Yes"]} yes</span>'
            "</div>"
        )
    bar_html = "".join(bars)

    css = (WEB / "brief.css").read_text()
    payload = {
        "generated_from": "research_agent.findings",
        "counts": dict(counts),
        "sample": sample,
        "transport": transport,
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>100 APIs, read from the docs — Composio research brief</title>
<meta name="description" content="Which of 100 apps a developer can actually connect, from official docs. Gated is a finding. Unverified stays blank.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,520;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Outfit:wght@380;480;560&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
<nav class="top">
  <div class="wrap">
    <a class="brand" href="#brief">Composio · API brief</a>
    <div class="links">
      <a href="#patterns">Patterns</a>
      <a href="#staff">Where to staff</a>
      <a href="#table">100 apps</a>
      <a href="#proof">Proof</a>
      <a href="#rerun">Rerun</a>
    </div>
  </div>
</nav>

<header class="hero" id="brief">
  <div class="wrap">
    <div class="kicker">Product ops field brief · 24 Sep 2026 · 100 apps, 10 categories</div>
    <h1>Most of these APIs are open. The locked ones are clustered.</h1>
    <p class="lede">A developer can start on {counts['Yes']} of these 100 apps without a sales call. {counts['Conditional']} more have a real API, and a real gate. {counts['Could not verify']} stayed blank on purpose. Gated is a finding. A guess is not.</p>
    <div class="meta-row">
      <span>Read time <strong>2 minutes</strong> above the table</span>
      <span>Evidence <strong>official docs only</strong></span>
      <span>Agent <strong>catalog → fetch → heuristic → human read</strong></span>
      <span><a href="verified.json">verified.json</a></span>
    </div>
    <div class="scores" aria-label="Verdict counts">
      <div class="score yes"><b>{counts['Yes']}</b><span>Yes. Public API, credential a developer can create.</span></div>
      <div class="score cond"><b>{counts['Conditional']}</b><span>Conditional. Documented, but paid, reviewed, or admin-only.</span></div>
      <div class="score unk"><b>{counts['Could not verify']}</b><span>Could not verify. Page missing, 403, 404, or auth not in the text.</span></div>
      <div class="score"><b>{counts['No']}</b><span>No. None in this pass. Absence was not proved, so it was not claimed.</span></div>
    </div>
    <div class="bars" aria-label="Yes share by category">
      {bar_html}
    </div>
  </div>
</header>

<section id="patterns">
  <div class="wrap">
    <h2>Four patterns worth staffing around</h2>
    <p class="section-lead">These are the sentences a reviewer should be able to repeat. The table underneath is the evidence, not the point.</p>
    <div class="patterns">
      <article class="pattern">
        <div class="num">01 — Auth</div>
        <h3>OAuth and a static key are usually both true.</h3>
        <p>{dual} verified apps document more than one way in. OAuth is how you act for someone else's account. A token or key is how you act for your own. A connector that ships only one of them will look finished and fail the other job.</p>
        <p>Watch the transport. Mailchimp's "API key" is HTTP Basic. Close's key is Basic with an empty password. monday.com and ClickUp put the personal token in Authorization with no Bearer prefix. higgsfield wants <code>Authorization: Key id:secret</code>.</p>
      </article>
      <article class="pattern">
        <div class="num">02 — Gates</div>
        <h3>The blockers clump. They are not sprinkled.</h3>
        <p>Ads and Meta surfaces want a review: Google Ads access levels, LinkedIn's higher tiers, Pinterest trial approval, Threads App Review, WhatsApp production. Enterprise commerce wants an instance you already pay for: SFCC, Adobe Commerce, Amazon Selling Partner, Squarespace custom keys on Commerce Advanced.</p>
        <p>Finance production is a second door behind a friendly sandbox. Plaid sandbox is self-serve. Brex needs an admin and a signed developer agreement, and documents no sandbox. Data vendors are the quiet middle: Ahrefs is not "enterprise only" — eligible paid plans, plus free test queries.</p>
      </article>
      <article class="pattern">
        <div class="num">03 — MCP</div>
        <h3>MCP is three products wearing one name.</h3>
        <p>Action servers, confirmed on a vendor page: {", ".join(action_mcp) or "none"}.</p>
        <p>Docs-only: Twilio's server at <code>mcp.twilio.com/docs</code> requires no account and does not execute calls. Hosting platform: Cloudflare's MCP docs are about deploying your own server, not connecting a Cloudflare account. Devin's docs show Devin as an MCP client. Front documents an MCP token scope but not a URL on the page we fetched.</p>
      </article>
      <article class="pattern">
        <div class="num">04 — Easy wins</div>
        <h3>Start where the credential is a settings page.</h3>
        <p>Developer tools, productivity, support, and email are the dense Yes band. CRM is close behind, except DealCloud, which reads as an existing-customer token, and Salesforce, where new connected apps are restricted as of Spring '26.</p>
        <p>Do not staff a build against fanbasis, Paygent Connect, PitchBook, Pumble, iPayX, Telegram, Datadog, Neo4j, Smartsheet, MongoDB Atlas, or Freshdesk until a page comes back with an auth scheme. Those are blanks, not nos.</p>
      </article>
    </div>
  </div>
</section>

<section id="staff">
  <div class="wrap">
    <h2>Where to staff, and where to stop</h2>
    <p class="section-lead">Yes means a developer can get a credential without a partnership. Conditional means the API is real and the blocker is the work. Unverified means we will not invent the row.</p>
    <div class="staff">
      <div class="col">
        <h3>Start this week · {len(yes)}</h3>
        <p class="hint">Self-serve free, trial, or paid. Standard auth. Public REST, GraphQL, or an action MCP.</p>
        <div class="chips">{chips(yes)}</div>
      </div>
      <div class="col gate">
        <h3>Real API, real gate · {len(cond)}</h3>
        <p class="hint">Worth a connector design. Not worth pretending the first call will succeed on a free signup.</p>
        <div class="chips">{chips(cond)}</div>
      </div>
      <div class="col stop">
        <h3>Do not guess · {len(blank)}</h3>
        <p class="hint">Docs 404, 403, nav-only, or no official reference found. Recheck. Do not map a neighbor product onto the name.</p>
        <div class="chips">{chips(blank)}</div>
      </div>
    </div>
  </div>
</section>

<section id="table">
  <div class="wrap">
    <h2>The 100, with the page</h2>
    <p class="section-lead">Every Yes or Conditional row has a URL that returned content in this pass. Confidence "partial" means the page loaded and the missing field was not in the text. "Unverified" means we will not fill it.</p>
    <div class="toolbar">
      <label class="visually-hidden" for="q" style="position:absolute;left:-9999px">Search apps</label>
      <input id="q" type="search" placeholder="Search name, auth, blocker" autocomplete="off">
      <div class="filters" id="verdicts">
        <button type="button" data-v="all" aria-pressed="true">All</button>
        <button type="button" data-v="Yes" aria-pressed="false">Yes</button>
        <button type="button" data-v="Conditional" aria-pressed="false">Conditional</button>
        <button type="button" data-v="Could not verify" aria-pressed="false">Unverified</button>
      </div>
      <div class="filters" id="cats">{cat_filters}</div>
      <div class="showing" id="showing">Showing 100</div>
    </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>#</th><th>App</th><th>Auth</th><th>Access</th><th>Surface</th><th>Verdict</th><th>Blocker</th><th>Evidence</th>
          </tr>
        </thead>
        <tbody id="rows">
          {''.join(body_rows)}
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="proof">
  <div class="wrap">
    <h2>Where the agent was wrong</h2>
    <p class="section-lead">Three loops. The first never saw the docs. The second misread gates as a green light. The third is the table above. The sample below is computed by <code>research_agent/build_site.py</code> from saved page text, not typed in by hand.</p>
    <div class="proof-grid">
      <div class="callout">
        <div class="kicker" style="color:#e7b2a8">Loop 0 · direct HTTP</div>
        <div class="big">{transport['tls']} / {transport['pages']}</div>
        <h3>TLS died before a sentence of docs arrived.</h3>
        <p>The fetch script requested {transport['pages']} seed URLs across {transport['apps']} apps. {transport['ok']} returned a body. {transport['tls']} failed in the TLS handshake. <code>data/pass1.json</code> is a transport log. Quoting it as research accuracy would be the dishonest version of this assignment.</p>
        <p>Loop 1 retrieved official pages with a page fetcher the sandbox TLS path could not replace. Loop 2 is a human read of those pages, written into <code>research_agent/findings.py</code>. If a field was not on the page, the cell says so.</p>
      </div>
      <div>
        <h3 style="font-family:var(--serif);font-weight:560;letter-spacing:-0.02em;margin:0 0 8px">Loop 1 vs the human read, same {sample['n']} pages</h3>
        <p class="section-lead" style="margin-bottom:10px">v1 accuracy {sample['v1_hits']}/{sample['n']} ({int(sample['v1_accuracy']*100)}%). After the gate rule, v2 is {sample['v2_hits']}/{sample['n']} ({int(sample['v2_accuracy']*100)}%). Remaining misses are the point, not a rounding error.</p>
        <table class="misses">
          <thead><tr><th>Page</th><th>v1</th><th>v2</th><th>Human</th><th>What happened</th></tr></thead>
          <tbody>{''.join(miss_rows)}</tbody>
        </table>
      </div>
    </div>
    <div class="lift">
      <strong>Read the score as in-sample.</strong> v2's extra phrases were added after these 12 pages, not before. v1's actual bug was narrower than "it calls everything Yes": it misses the plural "API keys", misses a Bearer header that does not contain the words "bearer token", and treats any "contact sales" as a hard no. v2 fixes those and still gets {still} wrong. {still_names} The rule is not finished, and it was not tested on the other 88.
    </div>
    <h3 style="font-family:var(--serif);margin:28px 0 8px">Corrections a memory-only pass would have gotten wrong</h3>
    <ol class="corrections">
      <li><strong>Ahrefs is not enterprise-only.</strong> Eligible paid plans include units. Other plans get free test queries. Owners and admins create keys.</li>
      <li><strong>Twilio MCP is not a Twilio connector.</strong> It searches public specs, needs no account, and does not execute calls. The REST API is HTTP Basic and is the buildable surface.</li>
      <li><strong>Shopify's fetched auth page is GraphQL Admin.</strong> REST Admin is not documented as current on that page. It is not claimed here.</li>
      <li><strong>Coda's API reference now titles itself Superhuman Docs.</strong> Auth was below the fold of the retrieved chunk, so the row stays unverified.</li>
      <li><strong>Squarespace's old authentication URL 404s.</strong> Custom keys require Commerce Advanced. Extensions use OAuth.</li>
      <li><strong>Zendesk API-token Basic is deprecated.</strong> New work is OAuth Bearer. Airtable's legacy API keys ended 1 Feb 2024.</li>
      <li><strong>monday.com and ClickUp personal tokens are not Bearer</strong> in the documented examples. A client that always prefixes Bearer will fail the happy path.</li>
      <li><strong>higgsfield is <code>Authorization: Key id:secret</code>.</strong> Bearer is explicitly wrong. Pay-as-you-go is self-serve. Invoice billing is the sales path.</li>
      <li><strong>Paygent Connect was not found.</strong> NMI has public API keys. It is a different product and is not used as evidence. iPayX <code>/docs</code> 404'd.</li>
      <li><strong>Consensus's shared API key maps to Enterprise.</strong> Per-user OAuth exists. Confidential clients are a sales request. One tool: search.</li>
      <li><strong>NotebookLM's public API is Gemini Notebook Enterprise on Google Cloud.</strong> It requires licenses. Consumer NotebookLM is not that API.</li>
      <li><strong>Stripe's API authentication reference hit an hCaptcha wall.</strong> The MCP page, which did load, is the evidence for API keys plus OAuth and <code>https://mcp.stripe.com</code>. The secret-key header format is not quoted.</li>
      <li><strong>Telegram's Bot API URL returned HTTP 403.</strong> Datadog's auth URL returned navigation, not a scheme. Neo4j and Smartsheet auth URLs 404'd. Freshdesk returned a table of contents. Those rows are blank.</li>
      <li><strong>Salesforce new connected apps are restricted as of Spring '26.</strong> External client apps remain the documented path. A free developer-edition page was not the page retrieved.</li>
    </ol>
  </div>
</section>

<section id="rerun">
  <div class="wrap">
    <h2>How to rerun it</h2>
    <div class="rerun">
      <div>
        <p>No Composio key was available, so the pipeline does not pretend to call the Composio SDK. It is a local agent: a catalog of the 100 apps, a fetcher, a deliberately dumb extractor, and an adjudicated snapshot.</p>
        <p>On a network that can complete TLS to docs hosts, the fetch writes <code>data/fetched.json</code> and a pass-1 file. In this sandbox that step is a transport failure, already saved. Do not treat a re-run here as new research.</p>
        <p>The page you are reading is generated. Edit a finding, run the renderer, and the counts, chips, and sample score move with the data. A Yes or Conditional row without a URL fails the build.</p>
      </div>
      <pre>python -m research_agent.fetch_docs
python -m research_agent.build_site

# fetch_docs  catalog → HTTP → heuristic pass 1
# build_site  findings.py → verified.json + this page
#             plus v1/v2 accuracy on sample_pages.py</pre>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    Composio AI Product Ops research brief. Official docs only. {counts['Yes']} yes · {counts['Conditional']} conditional · {counts['Could not verify']} not verified · {counts['No']} no.
    Category Yes counts:
    {", ".join(f"{short[c['id']]} {by_cat[c['id']]['Yes']}/{sum(by_cat[c['id']].values())}" for c in CATEGORIES)}.
  </div>
</footer>
<script id="payload" type="application/json">{json.dumps(payload)}</script>
<script>
const rows = Array.from(document.querySelectorAll("#rows tr"));
const q = document.getElementById("q");
const showing = document.getElementById("showing");
let verdict = "all";
let cat = "all";
function apply() {{
  const query = q.value.trim().toLowerCase();
  let n = 0;
  for (const row of rows) {{
    const okV = verdict === "all" || row.dataset.v === verdict;
    const okC = cat === "all" || row.dataset.c === cat;
    const okQ = !query || row.dataset.q.includes(query);
    const show = okV && okC && okQ;
    row.classList.toggle("hide", !show);
    if (show) n += 1;
  }}
  showing.textContent = "Showing " + n + " of " + rows.length;
}}
q.addEventListener("input", apply);
document.getElementById("verdicts").addEventListener("click", (event) => {{
  const button = event.target.closest("button");
  if (!button) return;
  verdict = button.dataset.v;
  for (const el of event.currentTarget.querySelectorAll("button")) el.setAttribute("aria-pressed", String(el === button));
  apply();
}});
document.getElementById("cats").addEventListener("click", (event) => {{
  const button = event.target.closest("button");
  if (!button) return;
  const next = button.dataset.cat;
  cat = cat === next ? "all" : next;
  for (const el of event.currentTarget.querySelectorAll("button")) {{
    el.setAttribute("aria-pressed", String(cat !== "all" && el === button));
  }}
  apply();
}});
</script>
</body>
</html>
"""


def main() -> None:
    rows = records()
    sample = score_sample()
    transport = transport_stats()
    verified = {
        "method": "Official pages retrieved, then human adjudication. Heuristic pass is a baseline, not the finding.",
        "apps": rows,
    }
    DATA.mkdir(exist_ok=True)
    (DATA / "verified.json").write_text(json.dumps(verified, indent=2) + "\n")
    (DATA / "verification.json").write_text(json.dumps({"transport": transport, "sample": sample}, indent=2) + "\n")
    page = render(rows, sample, transport)
    WEB.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    (WEB / "index.html").write_text(page)
    (WEB / "verified.json").write_text(json.dumps(verified, indent=2) + "\n")
    (DOCS / "index.html").write_text(page)
    counts = Counter(r["buildability_verdict"] for r in rows)
    print("apps", len(rows), dict(counts))
    print(
        f"sample v1 {sample['v1_hits']}/{sample['n']}  v2 {sample['v2_hits']}/{sample['n']}"
    )
    for row in sample["rows"]:
        mark = "ok" if row["v2_hit"] else "MISS"
        print(f"  {mark:4} {row['app_name']:16} v1={row['v1']:20} v2={row['v2']:20} human={row['human']}")
    print("wrote web/index.html", len(page))


if __name__ == "__main__":
    main()
