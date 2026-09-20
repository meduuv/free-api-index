# Source Registry

The repository tracks the API-directory repositories used for discovery.

The registry is machine-readable in data/sources.json.

## Source modes

### readme

The server reads a source README and extracts Markdown table rows containing HTTP or HTTPS URLs.

### local-and-runtime

The source has local imported records and can also be queried at runtime.

### external-openapi

The source provides structured OpenAPI or Arazzo data intended for external agent-oriented discovery. Its full specification set is not copied into the metadata catalog.

## Attribution

Every indexed record keeps its source repository.

Provider ownership, API terms, authentication requirements, rate limits and availability remain with the API provider.

## Refresh

The runtime cache can be controlled with:

    API_INDEX_CACHE_TTL=3600 python server.py

The default cache lifetime is six hours.
