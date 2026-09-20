# Free API Index

A source-aware API catalog for developers and AI agents.

## What is indexed

The repository combines the local catalog, imported Ultimate API List records, live machine-readable sources, and collected API-directory repositories.

The local catalog contains 2,001 records. The imported Ultimate dataset contains 16,654 records after URL deduplication. Runtime federation adds registered source repositories and live catalogs.

Jentic Public APIs is also registered as an external CC0 source for agent-oriented OpenAPI and Arazzo discovery. Jentic documents its public catalog as 10,000+ APIs and machine-readable agent tooling.

The source registry is in `data/sources.json`.

## Human developer index

`APIs.md` is the manual index.

Use it to browse:

- API name
- endpoint or documentation URL
- description
- authentication
- HTTPS
- CORS
- category
- source repository

The source list is in `sources/REPOSITORIES.md`.

The server also exposes a paginated machine-readable index at `/index`.

## Agent server

Start it with:

    python server.py

Default port: 8787.

### Core routes

| Route | Purpose |
|---|---|
| `/index` | paginated developer and agent index |
| `/health` | health and catalog counts |
| `/stats` | counts and top categories |
| `/sources` | registered source repositories |
| `/source/{name}` | inspect a source and its records |
| `/categories` | real and virtual categories |
| `/category/{name}` | category filter |
| `/providers` | provider/source names |
| `/provider/{name}` | provider or source filter |
| `/tags` | searchable domain and category tags |
| `/capabilities` | generated capability routes |
| `/search?q=weather` | keyword search |
| `/select?task=weather forecast` | task-oriented selection |
| `/recommend?task=send email` | ranked recommendations |
| `/related/{name}` | related API discovery |
| `/resolve?q=GitHub` | exact or fuzzy API resolution |
| `/auth/{type}` | authentication filter |
| `/random?limit=5` | random API selection |
| `/api/{name-or-url}` | exact or fuzzy API lookup |
| `/export?format=json` | filtered JSON export |
| `/export?format=ndjson` | filtered NDJSON export |
| `/reload` | rebuild the runtime catalog |
| `/developer` | developer integration examples |

## Index examples

    /index?page=1&size=100
    /index?sort=category&size=100
    /index?q=weather&size=50
    /index?category=Security&auth=none
    /index?source=jentic

Common filters work with `/index`, `/search`, `/select`, `/recommend`, and `/export`:

    ?category=Weather
    ?auth=none
    ?https=yes
    ?source=public-apis

## Agent workflow

Use `/select` when an agent has a task instead of a known API name.

    /select?task=find a free weather forecast API&limit=10

Use `/recommend` when the agent wants ranked candidates.

    /recommend?task=send transactional email&limit=5

Use `/resolve` when the agent has an uncertain API name.

    /resolve?q=github

Use `/related` after selecting an API to discover alternatives.

    /related/GitHub?limit=10

The server only discovers and ranks metadata. It does not blindly execute third-party APIs.

## Data rules

- Deduplicate by canonical URL, then normalized name.
- Preserve source attribution.
- Keep provider URLs and documentation URLs as supplied by source catalogs.
- Normalize descriptions and categories.
- Treat authentication, rate limits, CORS and availability as metadata that can become stale.
- Verify provider documentation before production use.

## Machine-readable data

Local records live in `data/apis.json`.

Imported Ultimate records live in `data/ultimate/*.json`.

The runtime server merges these datasets with registered live sources and deduplicates them before serving routes.

## Developer integration

A client can treat the server as a discovery layer:

1. Send a natural-language task to `/select` or `/recommend`.
2. Inspect returned API metadata.
3. Resolve a specific candidate with `/api/{name-or-url}`.
4. Read the provider documentation and authentication requirements.
5. Execute the provider API from the agent's own controlled runtime.
6. Use `/related` to recover when an API is unavailable.

Credentials are not stored or returned by this index.

## Regenerating documentation

The repository keeps machine-readable data separate from the human index.

When the catalog changes, regenerate the manual API documentation with the repository documentation tooling.

## License and attribution

This repository contains catalog metadata and source attribution. Listed APIs, services, names, documentation and endpoints remain controlled by their respective providers.

Check each source repository before redistributing source-specific data.
