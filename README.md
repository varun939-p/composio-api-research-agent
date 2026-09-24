# Composio API research agent

Which of 100 apps a developer can actually connect, read from official docs. The case study is [`web/index.html`](web/index.html). The same page is copied to [`docs/index.html`](docs/index.html) for static hosting.

Gated is a finding. A blank is a blank. The page says where the agent was wrong.

## What it concluded

Of the 100 apps: **58 yes**, **23 conditional**, **19 could not verify**, **0 no**.

Yes means a public REST, GraphQL, or action MCP, and a credential a developer can create without a partnership (free, trial, or self-serve paid). Conditional means the API is documented and the credential is paid, reviewed, admin-only, or tied to an existing customer instance. Could not verify means the official page did not return the field. Those rows are not filled from memory.

No Composio API key was available, so this does not call the Composio SDK. The pipeline is the local agent below.

## Run it

```bash
python -m research_agent.fetch_docs
python -m research_agent.build_site
```

`fetch_docs` walks `research_agent/catalog.py` (the 100 apps and their doc seeds), fetches with the stdlib HTTP client, and writes:

- `data/fetched.json` — what each URL actually returned
- `data/pass1.json` — a rules-only first pass over that text
- `data/raw/` — per-app dumps, gitignored

`build_site` does not fetch. It renders `research_agent/findings.py` into `data/verified.json` and the HTML page, then scores the heuristic against `research_agent/sample_pages.py`.

Open `web/index.html`. A Yes or Conditional row without an evidence URL fails the build.

## What happened in this sandbox

The first loop is not a research result. Direct TLS to docs hosts dies in the handshake (`SSL_ERROR_SYSCALL` / EOF). Of 275 seed URLs, 271 failed that way. Three GitHub pages returned a body, and that body was mostly GitHub chrome. `data/pass1.json` is the log of that failure. Do not quote it as the agent's judgment.

The findings on the page come from a second retrieval pass (official pages that did return text) and a human read of those pages. If the authentication section was not in the retrieved text, the cell says so. Telegram's Bot API URL returned HTTP 403. Neo4j, Smartsheet, and an old Squarespace auth URL 404'd. Datadog's auth URL returned navigation, not a scheme. Freshdesk returned a table of contents. Paygent Connect was not found; NMI was not substituted for it.

## The verification loop

`research_agent/extract.py` is intentionally dumb. On 12 saved pages it agreed with a human read **4/12** times.

The misses were specific:

- It does not match the plural "API keys".
- It does not match a Bearer header unless the words "bearer token" appear.
- Any "contact sales" becomes a hard no, including when the same page tells you to create an account.
- An MCP page with no "REST" and no "sign up" becomes "could not verify", even when it documents an action server.

`extract_v2` in `research_agent/build_site.py` adds those rules **after** reading the 12 pages. In-sample, that lifts the score to **11/12**. The remaining miss is higgsfield: pay-as-you-go is self-serve, and "contact sales" is only the invoice path. v2 still calls that Conditional. The rule was not tested on the other 88. That limit is printed on the page.

## Layout

```
research_agent/catalog.py       100 apps and seed URLs
research_agent/fetch_docs.py    loop 0, HTTP
research_agent/extract.py       loop 1, rules
research_agent/sample_pages.py  12 retrieved pages, with the human read
research_agent/findings.py      adjudicated rows
research_agent/build_site.py    verified.json, verification.json, HTML
web/index.html                  the brief
```
