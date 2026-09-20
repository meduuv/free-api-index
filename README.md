# Free API Index

A source-aware API catalog for developers and AI agents.

## What is indexed

The repository combines the local catalog, imported Ultimate API List records, live machine-readable sources, and collected API-directory repositories.

The local catalog contains 2,001 records. The imported Ultimate dataset contains 16,654 records after URL deduplication. The runtime server merges these datasets and registered live sources into one deduplicated discovery index.

The complete runtime catalog is available through the server and the machine-readable files below.

## Quick integration

Start the API index server:

    python server.py

Default address:

    http://localhost:8787

### Search for an API

    curl "http://localhost:8787/search?q=weather&limit=10"

### Let an AI agent choose an API

    curl "http://localhost:8787/select?task=find%20a%20free%20weather%20forecast%20API&limit=5"

### Get recommendations

    curl "http://localhost:8787/recommend?task=send%20transactional%20email&limit=5"

### Resolve an API

    curl "http://localhost:8787/resolve?q=github"

### Get one API record

    curl "http://localhost:8787/api/GitHub"

### Browse the complete machine-readable index

    curl "http://localhost:8787/index?page=1&size=100"

Use pagination to walk through the complete catalog:

    /index?page=1&size=100
    /index?page=2&size=100
    /index?page=3&size=100

### Python integration

    import requests

    BASE = "http://localhost:8787"

    result = requests.get(
        f"{BASE}/select",
        params={"task": "free weather forecast", "limit": 5},
        timeout=15
    ).json()

    for api in result["results"]:
        print(api["name"], api["api_url"])

### JavaScript integration

    const params = new URLSearchParams({
      task: "free weather forecast",
      limit: "5"
    });

    const response = await fetch(
      "http://localhost:8787/select?" + params
    );

    const data = await response.json();

    for (const api of data.results) {
      console.log(api.name, api.api_url);
    }

### AI agent integration

Use the index as a discovery layer rather than giving an agent thousands of raw API records at once.

1. Convert the user's task into a short intent.
2. Call /select or /recommend.
3. Inspect the returned API metadata.
4. Call /resolve or /api/{name-or-url} for the selected record.
5. Read the provider documentation returned by the record.
6. Check authentication, rate limits, permissions and current availability.
7. Execute the provider API from the agent's controlled runtime.
8. Call /related/{name} if the provider is unavailable.

Example:

    /select?task=convert%20currency%20between%20USD%20and%20INR&limit=10

The index discovers APIs. It does not store provider credentials or blindly execute arbitrary third-party requests.

## Complete API index

There are two layers of API records.

### Local human-readable index

[APIs.md](APIs.md) contains the human-readable local catalog with:

- API name
- endpoint or documentation URL
- description
- authentication
- HTTPS
- CORS
- category
- source repository

### Imported API catalog

The imported Ultimate records are split into machine-readable category files. Together these files contain all 16,654 imported records.

| Category | Complete API data |
|---|---|
| AI | [AI.json](data/ultimate/AI.json) |
| Agents | [Agents.json](data/ultimate/Agents.json) |
| Automation | [Automation.json](data/ultimate/Automation.json) |
| Developer tools | [Developer_tools.json](data/ultimate/Developer_tools.json) |
| Ecommerce | [Ecommerce.json](data/ultimate/Ecommerce.json) |
| Integrations | [Integrations.json](data/ultimate/Integrations.json) |
| Jobs | [Jobs.json](data/ultimate/Jobs.json) |
| Lead generation | [Lead_generation.json](data/ultimate/Lead_generation.json) |
| MCP servers | [MCP_servers.json](data/ultimate/MCP_servers.json) |
| News | [News.json](data/ultimate/News.json) |
| Open source | [Open_source.json](data/ultimate/Open_source.json) |
| Other | [Other.json](data/ultimate/Other.json) |
| Real estate | [Real_estate.json](data/ultimate/Real_estate.json) |
| SEO tools | [SEO_tools.json](data/ultimate/SEO_tools.json) |
| Social media | [Social_media.json](data/ultimate/Social_media.json) |
| Travel | [Travel.json](data/ultimate/Travel.json) |
| Videos | [Videos.json](data/ultimate/Videos.json) |

The runtime server merges these files with [data/apis.json](data/apis.json) and registered source catalogs, then deduplicates the result.

### Complete source index

- [sources/REPOSITORIES.md](sources/REPOSITORIES.md) lists API discovery repositories.
- [sources/SOURCES.md](sources/SOURCES.md) contains source and provider details.
- [data/sources.json](data/sources.json) contains machine-readable source registrations.
- [data/categories.json](data/categories.json) contains generated routing categories.

## Server routes

| Route | Purpose |
|---|---|
| / | server overview |
| /index | paginated complete API index |
| /health | health and catalog counts |
| /stats | catalog statistics |
| /sources | registered sources |
| /source/{name} | source records |
| /categories | categories |
| /category/{name} | category filter |
| /providers | providers and sources |
| /provider/{name} | provider filter |
| /tags | searchable tags |
| /capabilities | generated capabilities |
| /search?q=weather | keyword search |
| /select?task=weather%20forecast | task-based API selection |
| /recommend?task=send%20email | recommendations |
| /related/{name} | related APIs |
| /resolve?q=github | exact or fuzzy resolution |
| /auth/{type} | authentication filter |
| /random?limit=5 | random API records |
| /export?format=json | JSON export |
| /export?format=ndjson | NDJSON export |
| /reload | rebuild runtime catalog |
| /developer | integration examples |
| /api/{name-or-url} | API lookup |

## Filters

Common filters work with /index, /search, /select, /recommend and /export:

    ?category=Weather
    ?auth=none
    ?https=yes
    ?source=public-apis
    ?provider=github
    ?limit=20

Examples:

    /index?category=Security&auth=none&https=yes
    /search?q=machine%20learning&https=yes
    /select?task=free%20image%20generation&category=AI
    /export?category=Weather&format=ndjson

## Developer documentation

- [Developer integration manual](docs/DEVELOPERS.md)
- [Manual developer workflow](docs/MANUAL_DEVS.md)
- [Route reference](docs/ROUTES.md)
- [Source documentation](docs/SOURCES.md)
- [OpenAPI specification](openapi.json)
- [Markdown file index](docs/INDEX.md)
- [Contribution rules](CONTRIBUTING.md)

## Data rules

- Deduplicate by canonical URL, then normalized name.
- Preserve source attribution.
- Keep provider URLs and documentation URLs supplied by source catalogs.
- Normalize descriptions and categories.
- Treat authentication, rate limits, CORS and availability as metadata that can become stale.
- Verify provider documentation before production use.

## Machine-readable data

Local records:

[data/apis.json](data/apis.json)

Imported records:

[data/ultimate/](data/ultimate/)

Source registry:

[data/sources.json](data/sources.json)

Category registry:

[data/categories.json](data/categories.json)

The server merges these sources at runtime and exposes one discovery interface for applications and AI agents.

## Markdown index

Every Markdown file in the repository is listed here:

| File | Purpose |
|---|---|
| [README.md](README.md) | project overview, integration, complete API index and routes |
| [APIs.md](APIs.md) | human-readable API catalog |
| [CONTRIBUTING.md](CONTRIBUTING.md) | contribution and data-quality rules |
| [docs/INDEX.md](docs/INDEX.md) | complete Markdown file index |
| [docs/DEVELOPERS.md](docs/DEVELOPERS.md) | developer integration manual |
| [docs/MANUAL_DEVS.md](docs/MANUAL_DEVS.md) | manual developer workflow |
| [docs/ROUTES.md](docs/ROUTES.md) | unified server route reference |
| [docs/SOURCES.md](docs/SOURCES.md) | source and attribution reference |
| [sources/REPOSITORIES.md](sources/REPOSITORIES.md) | registered API source repositories |
| [sources/SOURCES.md](sources/SOURCES.md) | source details and attribution |
