# Composio API research agent

Which of 100 apps a developer can actually connect, read from official docs. The case study is [`web/index.html`](web/index.html). The same page is copied to [`docs/index.html`](docs/index.html) for static hosting.

Gated is a finding. A blank is a blank. The page says where the extractor was wrong.

## What it concluded

Of the 100 apps: **58 yes**, **23 conditional**, **19 could not verify**, **0 no**.

Yes means a public REST, GraphQL, or action MCP, and a credential a developer can create without a partnership (free, trial, or self-serve paid). Conditional means the API is documented and the credential is paid, reviewed, admin-only, or tied to an existing customer instance. Could not verify means the official page did not return the field. Those rows are not filled from memory.

## Run it

The fetch goes through the Composio SDK. Composio Search needs no second vendor key. `COMPOSIO_SEARCH_FETCH_URL_CONTENT` reads the official URL on Composio's side and returns markdown. A thin page is retried with `COMPOSIO_SEARCH_WEB`, then fetched again.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# put your project key in .env — do not commit that file
.venv/bin/python -m research_agent.fetch_docs
.venv/bin/python -m research_agent.build_site
```

`.env`:

```
COMPOSIO_API_KEY=your_key_here
```

`research_agent/composio_client.py` loads that file if the variable is not already exported, then calls `Composio(api_key=...)` and `composio.tools.execute`. The key is never written into the HTML or the JSON artifacts.

`fetch_docs` writes:

- `data/fetched.json` — what each official URL returned
- `data/pass1.json` — a rules-only first pass over that text
- `data/raw/` — per-app dumps, gitignored

`build_site` does not fetch. It renders `research_agent/findings.py` into `data/verified.json` and the HTML page, then scores the heuristic against `research_agent/sample_pages.py`.

Open `web/index.html`. A Yes or Conditional row without an evidence URL fails the build.

## The verification loop

`research_agent/extract.py` is intentionally dumb. On 12 saved official pages it agreed with a human read **4/12** times.

The misses were specific:

- It does not match the plural "API keys".
- It does not match a Bearer header unless the words "bearer token" appear.
- Any "contact sales" becomes a hard no, including when the same page tells you to create an account.
- An MCP page with no "REST" and no "sign up" becomes "could not verify", even when it documents an action server.

`extract_v2` in `research_agent/build_site.py` adds those rules **after** reading the 12 pages. In-sample, that lifts the score to **11/12**. The remaining miss is higgsfield: pay-as-you-go is self-serve, and "contact sales" is only the invoice path. v2 still calls that Conditional. The rule was not tested on the other 88. That limit is printed on the page.

## Layout

```
research_agent/composio_client.py   Composio SDK: fetch URL + web search
research_agent/fetch_docs.py        catalog → SDK → pass 1
research_agent/extract.py           rules-only reader
research_agent/sample_pages.py      12 retrieved pages, with the human read
research_agent/findings.py          adjudicated rows
research_agent/build_site.py        verified.json, verification.json, HTML
web/index.html                      the brief
```
