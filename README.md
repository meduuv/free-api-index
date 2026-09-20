# Free API Index

A source-aware API catalog for developers and AI agents.

## What is indexed

The repository combines the local catalog, imported Ultimate API List records, live machine-readable sources, and the previously collected API-directory repositories.

The local catalog contains 2,001 records. The imported Ultimate dataset contains 16,654 records after URL deduplication. Runtime federation adds the registered source repositories and live catalogs.

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

## Agent server

Start it with:

    python server.py

Default port: 8787.

### Discovery routes

| Route | Purpose |
|---|---|
| `/` | server metadata and route list |
| `/health` | health and catalog counts |
| `/stats` | counts, sources and cache state |
| `/sources` | registered source repositories |
| `/categories` | real and virtual categories |
| `/search?q=weather` | keyword search |
| `/select?task=weather forecast` | task-oriented API selection |
| `/category/{name}` | category filter |
| `/provider/{name}` | provider or source filter |
| `/auth/{type}` | authentication filter |
| `/random?limit=5` | random API selection |
| `/api/{name-or-url}` | exact API lookup |
| `/export?format=json` | filtered JSON export |
| `/export?format=ndjson` | filtered NDJSON export |

Common filters work with search and export:

    ?category=Weather
    ?auth=none
    ?https=yes
    ?source=public-apis

## Agent selection

Use `/select` when an agent has a task instead of a known API name.

Example:

    /select?task=find a free weather forecast API&limit=10

The server only discovers and ranks metadata. It does not blindly execute third-party APIs.

## Data rules

- Deduplicate by canonical URL, then normalized name.
- Preserve source attribution.
- Keep provider URLs and documentation URLs as supplied by source catalogs.
- Normalize descriptions and categories.
- Treat authentication, rate limits, CORS and availability as metadata that can become stale.
- Verify provider documentation before production use.

## Regenerating documentation

The repository keeps machine-readable data separate from the human index.

Use the rebuild script when the catalog changes:

    python scripts/rebuild_docs.py

It regenerates the manual API index and developer documentation from the current data files.

## License and attribution

This repository contains catalog metadata and source attribution. Listed APIs, services, names, documentation and endpoints remain controlled by their respective providers.

Check each source repository before redistributing source-specific data.
