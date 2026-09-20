# Free API Index

A source-aware API catalog built for developers and AI agents.

## Local index

2001 deduplicated API records are stored in data/apis.json.

The live federation layer in server.py adds the current public-api-lists JSON catalog, the MIT licensed public-apis-live dataset, and the category catalogs from kawsarlog/Ultimate-API-List at runtime.

The Ultimate API List advertises 50,371 records across 17 categories. Its repository currently has no detected open-source license, so this project does not copy that dataset into the repository.

## Imported Ultimate API data

The repository includes 16,654 Ultimate API records after URL deduplication against the local catalog. They are stored by category under `data/ultimate/`.

## Agent server

Run:

    python server.py

Default port: 8787

Routes:

    /health
    /stats
    /categories
    /search?q=weather
    /select?task=find a weather forecast API
    /api/{name-or-url}

The /select route is intended for agents. It returns API records with source, authentication, HTTPS, CORS and description fields.

## Categories

The source data keeps its original categories. The agent layer also exposes 512 virtual routing categories built from domain, operation and target combinations.

## Quality rules

Duplicates are keyed by canonical API URL and fall back to normalized API name.

Descriptions and categories are normalized before runtime indexing.

Non HTTP records are excluded by the runtime normalizer.

Agents should verify documentation, authentication, rate limits and availability before use.

## Files

| Path | Purpose |
|---|---|
| data/apis.json | Local deduplicated catalog |
| server.py | Agent discovery server |
| scripts/clean_markdown.py | Markdown cleanup pass |
| sources/REPOSITORIES.md | Validated discovery sources |
| APIs.md | Human readable local API index |
