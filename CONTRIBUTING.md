# Contributing

## Adding an API source

1. Add the repository to `data/sources.json`.
2. Set the source mode to `readme`, `json`, or another supported mode.
3. Keep source attribution.
4. Prefer official provider URLs or documentation URLs.
5. Keep descriptions factual and concise.

## Data quality

Check:

- API URL is present
- URL uses HTTP or HTTPS
- name is useful to a developer
- description identifies the service
- authentication is preserved when known
- HTTPS and CORS are preserved when known
- source repository is recorded

## Duplicate handling

The runtime index canonicalizes URLs and falls back to normalized API names. Do not add a second record for the same API just because it appears in another catalog.

## Documentation

After data changes, run:

    python scripts/rebuild_docs.py

The generated manual index is `APIs.md`.

## Agent server

The server is discovery-only. Do not add arbitrary request execution, credential forwarding, proxying, or URL fetching routes without explicit validation, timeouts, SSRF protections, and an allowlist strategy.
