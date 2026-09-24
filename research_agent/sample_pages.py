"""Pages actually retrieved, trimmed, for the heuristic-vs-human check.

Each excerpt is text returned by the retrieval pass. The human label is the
reading of that same text, not a memory of the product.
"""

from __future__ import annotations

SAMPLES = [
    {
        "id": 53,
        "label": "Ahrefs introduction",
        "human_verdict": "Conditional",
        "human_note": "Eligible paid plans for real queries. Free test queries exist. Not a sales partnership.",
        "text": """
Introduction. With Ahrefs API, you can use data from your Ahrefs workspace to create custom integrations.
Eligibility. Ahrefs API is available on eligible paid plans. On all other plans, you'll still have access
to a limited set of free test queries. All requests besides free test queries consume API units. The minimum
cost for any request is 50 units. Eligible paid plans include a monthly API unit allowance.
API keys. To send requests to Ahrefs API, you'll need an API key. Only workspace owners and admins can
create and manage API keys. This can be done in Account settings / API keys. The reference contains an
OpenAPI-compatible specification of each endpoint. Ahrefs API is limited to 60 requests per minute.
Full OpenAPI spec is published. This is a REST API for Site Explorer, Keywords Explorer, and Rank Tracker.
""",
    },
    {
        "id": 46,
        "label": "Squarespace authentication",
        "human_verdict": "Conditional",
        "human_note": "Custom API keys require Commerce Advanced. OAuth is the extension path. The word 'paid plan' never appears.",
        "text": """
Authentication and permissions. Every request to Commerce APIs must be authenticated.
Depending on your development needs, authenticate requests by using an API key or OAuth access token.
Custom applications. With Squarespace's Commerce Advanced plan, you can develop a custom application
for a Squarespace merchant site. Log in to a Squarespace site. Click Settings, Advanced, Developer API Keys.
Click the GENERATE KEY button. API keys will never expire as long as the merchant site remains active.
Commercial development. Squarespace Extensions allow customers on any plan to expand their site.
If you'd like to develop a new Extension, start the OAuth client process. Once you've obtained OAuth
credentials, you can use our OAuth 2.0 Guide. All Commerce APIs are built on HTTPS and designed with REST principles.
""",
    },
    {
        "id": 22,
        "label": "Twilio MCP page only",
        "human_verdict": "Conditional",
        "human_note": "This page is a docs search server. It says it does not execute API calls and needs no key. Not an action connector.",
        "text": """
Twilio MCP server. Public Beta. The Twilio Model Context Protocol (MCP) server gives AI coding agents
direct, structured access to Twilio's full API surface — over 1,800 endpoints — without leaving your IDE.
No authentication required. The MCP server indexes public API specifications only. No Twilio account or API keys needed.
No installation required. The server is hosted by Twilio at mcp.twilio.com/docs.
Limitations. Read-only. The server provides API search and documentation retrieval. It does not execute API calls
on your behalf. Public specs only. Planned additions include execute-ready, OAuth-authenticated MCP tools that
let agents call Twilio APIs directly. Connect your AI coding agent to the Twilio MCP server.
""",
    },
    {
        "id": 35,
        "label": "Mailchimp quick start",
        "human_verdict": "Yes",
        "human_note": "Free account, API key via HTTP Basic, OAuth for other users.",
        "text": """
Marketing API Quick Start. If you don't have a Mailchimp account already, you'll need to create one
in order to use the API. The simplest way to authenticate a request to the Marketing API is using an API key.
Navigate to the API Keys section of your Mailchimp account. Click Create New Key. Your Mailchimp API key
provides full account access. If you're creating integrations that require access to Mailchimp on behalf of
other Mailchimp users, you'll want to set up authentication via Oauth 2 instead.
curl "https://${dc}.api.mailchimp.com/3.0/ping" --user "anystring:${apikey}"
The Marketing API is a REST API. Sign up is self-serve.
""",
    },
    {
        "id": 76,
        "label": "monday.com authentication",
        "human_verdict": "Yes",
        "human_note": "Free developer account. Personal token. The curl example does not use the word Bearer.",
        "text": """
The monday.com platform API utilizes personal V2 API tokens to authenticate requests.
If you don't have a monday.com account yet, create a free developer account to get an API token and start testing.
Personal tokens allow you to interact with the API using your own user account.
All users with API access can open the Developer Center and click API token, Show.
Once you have your token, pass the token in the Authorization header.
curl -X POST https://api.monday.com/v2 -H "Authorization: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
App tokens have an additional set of permission scopes. This is a GraphQL API.
OAuth is documented for apps that other users install.
""",
    },
    {
        "id": 91,
        "label": "NotebookLM Enterprise API",
        "human_verdict": "Conditional",
        "human_note": "Licenses and a GCP project are required. The nav says Start free, which is Google Cloud, not this product.",
        "text": """
Create and manage notebooks (API). Gemini Notebook Enterprise. Start free.
Before you begin. Set up Gemini Notebook Enterprise. Get licenses for Gemini Notebook Enterprise.
To create a new notebook, use the notebooks.create method.
curl -X POST -H "Authorization:Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json"
"https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks"
This is a REST method. A Google Cloud project is required. Consumer NotebookLM is not described on this page.
""",
    },
    {
        "id": 94,
        "label": "Consensus connection reference",
        "human_verdict": "Conditional",
        "human_note": "Documented MCP. Shared API key is Enterprise. Contact sales is for confidential OAuth clients, not for the existence of the API.",
        "text": """
Connection reference. MCP endpoint https://mcp.consensus.app/mcp. Transport Streamable HTTP.
Authentication. Two options. For a shared, server-side gateway credential, use an API key.
Authorization: Bearer ak_live_... It maps to your Enterprise tier. Generate one from your Consensus account:
profile icon, API and MCP Dashboard, Keys and clients, New key.
OAuth 2.0 is per-user. There is no client-credentials grant. Dynamic Client Registration issues public clients.
If your gateway needs a confidential client and can't do DCR, contact sales and we'll set one up.
What Enterprise unlocks: custom rate limit, up to 1,000 papers per call. Paid plans are lower.
The server exposes one tool, search. This is an MCP server, not a REST resource API.
""",
    },
    {
        "id": 88,
        "label": "Brex developer authentication",
        "human_verdict": "Conditional",
        "human_note": "A token can be created in the dashboard, but only by an account admin, and only after a company agreement. Production only.",
        "text": """
To start making calls to Brex APIs, generate a user token from your Brex dashboard and pass it along in your API call headers.
Sign in to dashboard.brex.com as an account admin or card admin. Go to Developer, Settings.
If your company has not accepted the developer API agreement, please review the terms and conditions.
These must be accepted to use the developer API. Click Create Token. Choose scopes. Copy and store the token.
Authorization: Bearer {{your user_token here}}
Brex currently only offers a production API server at https://api.brex.com. This is the base URL for all API calls.
There is no sandbox described on this page. The API is REST.
""",
    },
    {
        "id": 56,
        "label": "Firecrawl introduction",
        "human_verdict": "Yes",
        "human_note": "Bearer API key, public REST, self-serve. 402 means the plan limit, not a sales gate.",
        "text": """
Firecrawl API reference. Base URL https://api.firecrawl.dev.
For authentication, it's required to include an Authorization header. The header should contain
Bearer fc-123456789, where fc-123456789 represents your API Key.
Endpoints include scrape, crawl, map, and search. This is a REST API.
402 Payment required. 401 The API key was not provided. 429 The rate limit has been surpassed.
Create an API key from the dashboard to start. Sign up is available. No partnership is required.
""",
    },
    {
        "id": 95,
        "label": "Reducto agent guide",
        "human_verdict": "Yes",
        "human_note": "Free studio account, Bearer key, REST and MCP.",
        "text": """
Reducto is the agentic document platform. It provides a toolkit via a REST API.
Base URL https://platform.reducto.ai. Auth: Authorization: Bearer $REDUCTO_API_KEY.
Create a free account at studio.reducto.ai. In the Studio sidebar, click API Keys, then Create API Key.
You can also call the MCP server. POST https://platform.reducto.ai/parse.
No sales conversation is required to get a key. SDKs exist for Python and Node.
""",
    },
    {
        "id": 73,
        "label": "Linear MCP",
        "human_verdict": "Yes",
        "human_note": "Hosted action MCP. OAuth or an API key. Self-serve.",
        "text": """
The Model Context Protocol (MCP) server provides a standardized interface that allows any compatible
AI model or agent to access your Linear data. Our MCP server uses Streamable HTTP.
Read-write access is provided through https://mcp.linear.app/mcp by default.
The interactive setup flow uses OAuth 2.1 with dynamic client registration.
You can also authenticate directly with a bearer token or Linear API key.
Tools are available for finding, creating, and updating issues, projects, and comments.
Sign in to your Linear account to connect. A free Linear workspace is enough to start.
""",
    },
    {
        "id": 97,
        "label": "higgsfield FAQ",
        "human_verdict": "Yes",
        "human_note": "Console signup and pay-as-you-go. Contact sales is only for invoice contracts, not for a key.",
        "text": """
What base URL and authentication header should I use?
Send requests to https://api.higgsfield.ai and authenticate server-side with
Authorization: Key YOUR_KEY_ID:YOUR_KEY_SECRET. Do not use a Bearer token.
How do I get started with the API? Create an account at console.higgsfield.ai.
Generate your API credentials from the dashboard. The API runs on pay-as-you-go by default:
you top up a balance and pay per generation. Invoice-based billing is available for customers
on a committed-use contract. To discuss one, contact sales.
This is a REST API. Failed generation requests are not charged.
""",
    },
]
