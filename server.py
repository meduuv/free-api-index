import json
import os
import random
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "apis.json"
SOURCE_FILE = ROOT / "data" / "sources.json"
CACHE_TTL = int(os.getenv("API_INDEX_CACHE_TTL", "21600"))
PORT = int(os.getenv("PORT", "8787"))

REMOTE_JSON = [
    {"name": "public-api-lists/public-api-lists", "url": "https://raw.githubusercontent.com/public-api-lists/public-api-lists/master/api/all.json"},
    {"name": "Manavarya09/public-apis-live", "url": "https://raw.githubusercontent.com/Manavarya09/public-apis-live/main/data/apis.json"}
]

ULTIMATE_CATEGORIES = ["AI","Agents","Automation","Developer_tools","Ecommerce","Integrations","Jobs","Lead_generation","MCP_servers","News","Open_source","Other","Real_estate","SEO_tools","Social_media","Travel","Videos"]
ULTIMATE_BASE = "https://raw.githubusercontent.com/kawsarlog/Ultimate-API-List/main"

DOMAINS = ["AI","Agents","Automation","Analytics","Animals","Anime","Anti Malware","Art","Authentication","Blockchain","Books","Business","Calendar","Cloud","Commerce","Communication","Crypto","Currency","Data","Databases","Development","Documents","Education","Email","Entertainment","Environment","Events","Finance","Food","Games","Geocoding","Government","Health","Images","Jobs","Maps","Marketing","Media","Machine Learning","Messaging","Music","News","Open Data","Open Source","Payments","Productivity","Programming","Science","Search","Security","Social","Space","Sports","Storage","Testing","Text","Translation","Transportation","Travel","Video","Voice","Weather"]
MODES = ["lookup","search","generation","conversion","validation","analysis","monitoring","automation"]
TARGETS = ["agent","application","website","developer","data","workflow","research","security"]

cache = {"items": None, "loaded": 0.0}

def normalize(value):
    value = str(value or "").strip()
    value = re.sub(r"!\[[^]]*\]\([^)]*\)", "", value)
    value = re.sub(r"[*_~]", "", value)
    value = value.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", value).strip(" -|")

def canonical_url(value):
    return re.sub(r"^https?://", "", normalize(value).lower().rstrip("/"))

def normalize_item(item, source, category=None):
    if not isinstance(item, dict):
        return None
    name = normalize(item.get("name") or item.get("title") or item.get("API") or item.get("api") or item.get("service"))
    url = normalize(item.get("api_url") or item.get("url") or item.get("endpoint") or item.get("link"))
    if not name or not url or not url.startswith(("http://", "https://")):
        return None
    return {
        "name": name,
        "api_url": url,
        "description": normalize(item.get("description") or item.get("Description") or item.get("desc")),
        "auth": normalize(item.get("auth") or item.get("Auth") or "unknown"),
        "https": normalize(item.get("https") or item.get("HTTPS") or "unknown"),
        "cors": normalize(item.get("cors") or item.get("CORS") or "unknown"),
        "category": normalize(category or item.get("category") or item.get("Category") or "Other"),
        "source": source
    }

def parse_json_payload(payload, source):
    if isinstance(payload, dict):
        for key in ("apis", "entries", "data", "items", "results"):
            if isinstance(payload.get(key), list):
                return [x for x in (normalize_item(v, source) for v in payload[key]) if x]
        item = normalize_item(payload, source)
        return [item] if item else []
    if isinstance(payload, list):
        return [x for x in (normalize_item(v, source) for v in payload) if x]
    return []

def parse_markdown(text, source, category="Other"):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.count("|") < 3:
            continue
        cells = [normalize(x) for x in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"api", "name", "service", "api name"}:
            continue
        if re.fullmatch(r"[-: ]+", cells[0]):
            continue
        urls = re.findall(r"https?://[^\s|)]+", line)
        if urls:
            item = normalize_item({"name": cells[0], "api_url": urls[0], "description": cells[1]}, source, category)
            if item:
                rows.append(item)
    return rows

def fetch_url(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "free-api-index-agent/3.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")

def fetch_json(url, source):
    return parse_json_payload(json.loads(fetch_url(url)), source)

def fetch_readme(repo):
    try:
        return parse_markdown(fetch_url(f"https://raw.githubusercontent.com/{repo}/HEAD/README.md"), repo)
    except Exception:
        return []

def fetch_ultimate_one(category):
    try:
        return parse_markdown(fetch_url(f"{ULTIMATE_BASE}/{urllib.parse.quote(category)}/README.md"), f"kawsarlog/Ultimate-API-List:{category}", category)
    except Exception:
        return []

def dedupe(items):
    result = {}
    for item in items:
        key = canonical_url(item.get("api_url")) or normalize(item.get("name")).lower()
        if key not in result:
            result[key] = item
            continue
        current = result[key]
        if len(item.get("description", "")) > len(current.get("description", "")):
            current["description"] = item["description"]
        sources = set(current.get("source", []) if isinstance(current.get("source"), list) else [current.get("source")])
        sources.update(item.get("source", []) if isinstance(item.get("source"), list) else [item.get("source")])
        current["source"] = sorted(x for x in sources if x)
    return list(result.values())

def load_sources():
    try:
        with SOURCE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def build_items(force=False):
    if not force and cache["items"] is not None and time.time() - cache["loaded"] < CACHE_TTL:
        return cache["items"]
    items = []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            items.extend(json.load(f).get("apis", []))
    except Exception:
        pass
    for path in sorted((ROOT / "data" / "ultimate").glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                items.extend(json.load(f).get("apis", []))
        except Exception:
            pass
    sources = load_sources()
    readme_repos = [x["repo"] for x in sources if x.get("mode") == "readme"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_json, x["url"], x["name"]) for x in REMOTE_JSON]
        futures.extend(pool.submit(fetch_readme, repo) for repo in readme_repos)
        futures.extend(pool.submit(fetch_ultimate_one, category) for category in ULTIMATE_CATEGORIES)
        for future in as_completed(futures):
            try:
                items.extend(future.result())
            except Exception:
                pass
    cache["items"] = dedupe(items)
    cache["loaded"] = time.time()
    return cache["items"]

def virtual_categories():
    return [f"{domain} {mode} for {target}" for domain in DOMAINS for mode in MODES for target in TARGETS]

def categories_for(items):
    return sorted({normalize(x.get("category")) for x in items if normalize(x.get("category"))})

def providers_for(items):
    values = set()
    for item in items:
        source = item.get("source", [])
        values.update(source if isinstance(source, list) else [source])
    return sorted(x for x in values if x)

def tokens(value):
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))

def score(item, query):
    parts = tokens(query)
    if not parts:
        return 1
    name = tokens(item.get("name"))
    category = tokens(item.get("category"))
    description = tokens(item.get("description"))
    source = tokens(item.get("source"))
    value = 0
    for part in parts:
        if part in name:
            value += 10
        elif part in category:
            value += 7
        elif part in source:
            value += 5
        elif part in description:
            value += 2
        else:
            return 0
    return value

def filter_items(items, params):
    category = params.get("category", [""])[0].lower()
    auth = params.get("auth", [""])[0].lower()
    https = params.get("https", [""])[0].lower()
    source = params.get("source", [""])[0].lower()
    values = items
    if category:
        values = [x for x in values if category in str(x.get("category", "")).lower()]
    if auth:
        values = [x for x in values if auth in str(x.get("auth", "")).lower()]
    if https:
        values = [x for x in values if https in str(x.get("https", "")).lower()]
    if source:
        values = [x for x in values if source in str(x.get("source", "")).lower()]
    return values

def limit_value(params, key, default, maximum):
    try:
        return min(max(int(params.get(key, [str(default)])[0]), 1), maximum)
    except Exception:
        return default

def index_page(items, params):
    values = filter_items(items, params)
    query = params.get("q", [""])[0]
    if query:
        values = [x for x in values if score(x, query)]
        values.sort(key=lambda x: (-score(x, query), x.get("name", "").lower()))
    else:
        sort_key = params.get("sort", ["name"])[0]
        if sort_key == "category":
            values.sort(key=lambda x: (x.get("category", "").lower(), x.get("name", "").lower()))
        elif sort_key == "source":
            values.sort(key=lambda x: (str(x.get("source", "")).lower(), x.get("name", "").lower()))
        else:
            values.sort(key=lambda x: x.get("name", "").lower())
    size = limit_value(params, "size", 50, 500)
    page = limit_value(params, "page", 1, 1000000)
    start = (page - 1) * size
    return values[start:start + size], len(values), page, size

def exact_or_fuzzy(items, query):
    wanted = normalize(query).lower()
    exact = [x for x in items if normalize(x.get("name")).lower() == wanted or canonical_url(x.get("api_url")) == canonical_url(wanted)]
    if exact:
        return exact[0]
    ranked = sorted(((score(x, wanted), x) for x in items), key=lambda x: (-x[0], x[1].get("name", "").lower()))
    return ranked[0][1] if ranked and ranked[0][0] else None

def related(items, target, limit):
    base = tokens(target.get("name")) | tokens(target.get("category")) | tokens(target.get("description"))
    ranked = []
    for item in items:
        if item is target:
            continue
        overlap = len(base & (tokens(item.get("name")) | tokens(item.get("category")) | tokens(item.get("description"))))
        if overlap:
            ranked.append((overlap, item))
    ranked.sort(key=lambda x: (-x[0], x[1].get("name", "").lower()))
    return [x[1] for x in ranked[:limit]]

class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        route = parsed.path.rstrip("/") or "/"
        items = build_items()

        if route == "/":
            return self.send_json({"name": "free-api-index", "version": "3.0", "apis": len(items), "routes": ["/index", "/health", "/stats", "/sources", "/source/{name}", "/categories", "/category/{name}", "/providers", "/provider/{name}", "/tags", "/capabilities", "/search", "/select", "/recommend", "/related/{name}", "/resolve", "/auth/{type}", "/random", "/api/{name-or-url}", "/export", "/reload", "/developer"]})

        if route == "/health":
            return self.send_json({"ok": True, "apis": len(items), "categories": len(categories_for(items)), "providers": len(providers_for(items)), "virtual_categories": len(virtual_categories()), "cache_age_seconds": round(time.time() - cache["loaded"], 2)})

        if route == "/stats":
            counts = {}
            for item in items:
                category = item.get("category") or "Other"
                counts[category] = counts.get(category, 0) + 1
            return self.send_json({"apis": len(items), "categories": len(counts), "providers": len(providers_for(items)), "virtual_categories": len(virtual_categories()), "top_categories": sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:50], "cache_age_seconds": round(time.time() - cache["loaded"], 2)})

        if route == "/index":
            results, total, page, size = index_page(items, params)
            return self.send_json({"page": page, "size": size, "total": total, "pages": (total + size - 1) // size, "results": results})

        if route == "/sources":
            return self.send_json({"count": len(load_sources()), "sources": load_sources()})

        if route.startswith("/source/"):
            wanted = urllib.parse.unquote(route[8:]).lower()
            source = next((x for x in load_sources() if wanted in x.get("repo", "").lower()), None)
            values = [x for x in items if wanted in str(x.get("source", "")).lower()]
            return self.send_json({"source": source, "count": len(values), "results": values[:500]})

        if route == "/categories":
            values = categories_for(items)
            return self.send_json({"count": len(values), "categories": values, "virtual_count": len(virtual_categories()), "virtual_categories": virtual_categories()})

        if route.startswith("/category/"):
            wanted = urllib.parse.unquote(route[10:]).lower()
            values = [x for x in items if wanted in str(x.get("category", "")).lower()]
            values.sort(key=lambda x: x.get("name", "").lower())
            return self.send_json({"category": wanted, "count": len(values), "results": values[:500]})

        if route == "/providers":
            values = providers_for(items)
            return self.send_json({"count": len(values), "providers": values})

        if route.startswith("/provider/"):
            wanted = urllib.parse.unquote(route[10:]).lower()
            values = [x for x in items if wanted in str(x.get("name", "")).lower() or wanted in str(x.get("source", "")).lower()]
            return self.send_json({"provider": wanted, "count": len(values), "results": values[:500]})

        if route == "/tags":
            values = sorted(set(DOMAINS + MODES + TARGETS + categories_for(items)))
            return self.send_json({"count": len(values), "tags": values})

        if route == "/capabilities":
            query = params.get("q", [""])[0]
            values = [f"{domain} {mode} for {target}" for domain in DOMAINS for mode in MODES for target in TARGETS]
            if query:
                values = [x for x in values if all(part in x.lower() for part in tokens(query))]
            return self.send_json({"query": query, "count": len(values), "capabilities": values})

        if route in {"/search", "/select", "/recommend"}:
            query = params.get("task", params.get("q", [""]))[0]
            limit = limit_value(params, "limit", 10 if route != "/search" else 20, 200)
            values = filter_items(items, params)
            ranked = sorted(((score(x, query), x) for x in values if score(x, query)), key=lambda x: (-x[0], x[1].get("name", "").lower()))
            results = [x[1] for x in ranked[:limit]]
            payload = {"query": query, "count": len(ranked), "results": results}
            if route != "/search":
                payload["agent_note"] = "Use results as discovery metadata. Verify provider documentation, credentials, rate limits, permissions and endpoint availability before execution."
            if route == "/recommend":
                payload["selection_basis"] = ["name match", "category match", "provider match", "description match"]
            return self.send_json(payload)

        if route.startswith("/related/"):
            target = exact_or_fuzzy(items, urllib.parse.unquote(route[9:]))
            if not target:
                return self.send_json({"error": "API not found"}, 404)
            return self.send_json({"api": target, "count": limit_value(params, "limit", 10, 100), "results": related(items, target, limit_value(params, "limit", 10, 100))})

        if route == "/resolve":
            query = params.get("q", [""])[0]
            target = exact_or_fuzzy(items, query)
            if not target:
                return self.send_json({"query": query, "error": "API not found"}, 404)
            return self.send_json({"query": query, "match": target})

        if route.startswith("/auth/"):
            wanted = urllib.parse.unquote(route[6:]).lower()
            values = [x for x in items if wanted in str(x.get("auth", "")).lower()]
            return self.send_json({"auth": wanted, "count": len(values), "results": values[:500]})

        if route == "/random":
            limit = limit_value(params, "limit", 1, 50)
            return self.send_json({"count": limit, "results": random.sample(items, min(limit, len(items)))})

        if route == "/export":
            fmt = params.get("format", ["json"])[0].lower()
            values = filter_items(items, params)
            if fmt == "ndjson":
                body = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in values).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
                return
            return self.send_json({"count": len(values), "apis": values})

        if route == "/reload":
            values = build_items(force=True)
            return self.send_json({"ok": True, "apis": len(values), "cache_age_seconds": 0})

        if route == "/developer":
            return self.send_json({"name": "free-api-index developer interface", "base": f"http://localhost:{PORT}", "examples": {"search": "/search?q=weather", "task": "/select?task=free+weather+forecast", "index": "/index?page=1&size=50&sort=category", "filter": "/index?category=Security&auth=none", "resolve": "/resolve?q=GitHub", "related": "/related/GitHub", "export": "/export?category=Weather&format=ndjson", "reload": "/reload"}, "rules": ["API records are discovery metadata", "Credentials are never supplied by this service", "Verify upstream terms and limits", "Do not treat availability metadata as permanent"]})

        if route.startswith("/api/"):
            wanted = urllib.parse.unquote(route[5:])
            target = exact_or_fuzzy(items, wanted)
            if target:
                return self.send_json(target)
            return self.send_json({"error": "API not found"}, 404)

        return self.send_json({"error": "Route not found", "routes": ["/index", "/health", "/stats", "/sources", "/source/{name}", "/categories", "/category/{name}", "/providers", "/provider/{name}", "/tags", "/capabilities", "/search", "/select", "/recommend", "/related/{name}", "/resolve", "/auth/{type}", "/random", "/api/{name-or-url}", "/export", "/reload", "/developer"]}, 404)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"free-api-index agent server listening on {PORT}")
    server.serve_forever()
