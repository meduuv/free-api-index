# Developer Manual

## Start

    python server.py

The default server is available at `http://localhost:8787`.

## Search

    curl "http://localhost:8787/search?q=weather&limit=10"

## Task selection

    curl "http://localhost:8787/select?task=free%20weather%20forecast&limit=5"

## Recommendations

    curl "http://localhost:8787/recommend?task=send%20transactional%20email&limit=5"

## Resolve

    curl "http://localhost:8787/resolve?q=github"

## Index browsing

    curl "http://localhost:8787/index?page=1&size=100&sort=category"

## Filters

    curl "http://localhost:8787/index?category=Security&auth=none&https=yes"

## Related APIs

    curl "http://localhost:8787/related/GitHub?limit=10"

## Export

    curl "http://localhost:8787/export?category=Weather&format=ndjson"

## Python

    import requests

    base = "http://localhost:8787"
    result = requests.get(f"{base}/select", params={"task": "free weather forecast", "limit": 5}, timeout=15).json()
    for api in result["results"]:
        print(api["name"], api["api_url"])

## JavaScript

    const params = new URLSearchParams({ task: "free weather forecast", limit: "5" });
    const response = await fetch("http://localhost:8787/select?" + params);
    const data = await response.json();
    console.log(data.results);

## Agent pattern

1. Convert the task into a short intent query.
2. Call `/select` or `/recommend`.
3. Compare returned candidates.
4. Resolve the chosen record if needed.
5. Read the provider documentation.
6. Handle authentication in the agent runtime.
7. Execute the provider API outside this index service.
8. Retry with `/related` when a provider is unavailable.

## Runtime behavior

The server loads local JSON records, imported Ultimate records, registered live sources and source README catalogs.

Records are deduplicated by canonical API URL and then normalized name.

The service does not store provider credentials and does not execute arbitrary third-party requests.

## API specification

The machine-readable server specification is in `openapi.json`.
