# API Server Routes

Base URL:

    http://localhost:8787

## Core

### GET /

Returns server name, version, catalog size and route list.

### GET /health

Returns health state and catalog counts.

### GET /stats

Returns catalog count, category count, source count and cache age.

### GET /sources

Returns every registered discovery source.

### GET /categories

Returns source categories and virtual routing categories.

## Search

### GET /search

Parameters:

- q
- limit
- category
- auth
- https
- source

Example:

    /search?q=weather&auth=none&limit=20

### GET /select

Task-oriented search for agents.

Parameters:

- task
- limit
- category
- auth
- https
- source

Example:

    /select?task=find a no-key weather API&limit=10

## Direct filters

### GET /category/{name}

Returns APIs whose category contains the requested text.

### GET /provider/{name}

Matches API names and source repository names.

### GET /auth/{type}

Filters by authentication metadata.

### GET /api/{name-or-url}

Looks up an exact API name or canonical URL.

### GET /random

Returns random records.

Parameter:

    ?limit=5

## Export

### GET /export?format=json

Returns filtered JSON records.

### GET /export?format=ndjson

Returns newline-delimited JSON for streaming tools.

Export supports:

    category
    auth
    https
    source

## Safety

The server does not execute arbitrary third-party API requests. It returns discovery metadata only.
