# Manual Developer Guide

## Finding an API

Start with APIs.md for the local catalog.

Search by:

- name
- provider
- category
- authentication
- source

For current source catalogs, use sources/REPOSITORIES.md and the registered source list.

## API record fields

| Field | Meaning |
|---|---|
| name | Service or API name |
| api_url | Provider API or documentation URL |
| description | Short service description |
| auth | Known authentication requirement |
| https | HTTPS support reported by the source |
| cors | CORS support reported by the source |
| category | Source category |
| source | Catalog that supplied the record |

## Manual workflow

1. Find candidate APIs.
2. Open the provider documentation.
3. Confirm the endpoint and request format.
4. Confirm authentication and free-tier limits.
5. Check rate limits and acceptable-use terms.
6. Test with a small request.
7. Add credentials through environment variables or a secret manager.
8. Keep provider attribution in your project.

## Agent workflow

For NIX or another agent:

    GET /select?task=find a free image search API&limit=10

Then inspect the returned records before using one.

The catalog is a discovery layer. It is not a guarantee that an API is free, available, unrestricted, or suitable for a particular workload.

## Local server

    python server.py

Then use:

    /stats
    /categories
    /search?q=weather
    /select?task=weather forecast
