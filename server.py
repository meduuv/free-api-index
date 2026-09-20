import json
import os
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
    request = urllib.request.Request(url, headers={"User-Agent": "free-api-index-agent/2.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")

def fetch_json(url, source):
    return parse_json_payload(json.loads(fetch_url(url)), source)

def fetch_readme(repo):
    try:
        text = fetch_url(f"https://raw.githubusercontent.com/{repo}/HEAD/README.md")
        return parse_markdown(text, repo)
    except Exception:
        return []

def fetch_ultimate_one(category):
    try:
        text = fetch_url(f"{ULTIMATE_BASE}/{urllib.parse.quote(category)}/README.md")
        return parse_markdown(text, f"kawsarlog/Ultimate-API-List:{category}", category)
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

def build_items():
    if cache["items"] is not None and time.time() - cache["loaded"] < CACHE_TTL:
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

def score(item, query):
    parts = [x for x in query.lower().split() if x]
    name = str(item.get("name", "")).lower()
    category = str(item.get("category", "")).lower()
    text = " ".join([name, category, str(item.get("description", "")).lower()])
    value = 0
    for part in parts:
        if part in name:
            value += 6
        elif part in category:
            value += 4
        elif part in text:
            value += 1
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
        items = build_items()
        route = parsed.path.rstrip("/") or "/"

        if route == "/":
            return self.send_json({
                "name": "free-api-index",
                "version": "2.0",
                "apis": len(items),
                "routes": ["/health", "/stats", "/sources", "/categories", "/search", "/select", "/api/{name-or-url}", "/category/{name}", "/provider/{name}", "/random", "/auth/{type}", "/export"]
            })

        if route == "/health":
            return self.send_json({"ok": True, "apis": len(items), "categories": len(categories_for(items)), "virtual_categories": len(virtual_categories())})

        if route == "/stats":
            return self.send_json({
                "apis": len(items),
                "categories": len(categories_for(items)),
                "virtual_categories": len(virtual_categories()),
                "sources": len({str(x.get("source")) for x in items}),
                "cache_age_seconds": round(time.time() - cache["loaded"], 2)
            })

        if route == "/sources":
            return self.send_json({"count": len(load_sources()), "sources": load_sources()})

        if route == "/categories":
            return self.send_json({"count": len(categories_for(items)), "categories": categories_for(items), "virtual_count": len(virtual_categories()), "virtual_categories": virtual_categories()})

        if route == "/search":
            query = params.get("q", [""])[0]
            limit = min(max(int(params.get("limit", ["20"])[0]), 1), 200)
            values = filter_items(items, params)
            results = []
            for item in values:
                value = score(item, query) if query else 1
                if value:
                    results.append((value, item))
            results.sort(key=lambda x: (-x[0], x[1].get("name", "")))
            return self.send_json({"query": query, "count": len(results), "results": [x[1] for x in results[:limit]]})

        if route == "/select":
            query = params.get("task", params.get("q", [""]))[0]
            limit = min(max(int(params.get("limit", ["10"])[0]), 1), 50)
            values = filter_items(items, params)
            results = []
            for item in values:
                value = score(item, query)
                if value:
                    results.append((value, item))
            results.sort(key=lambda x: (-x[0], x[1].get("name", "")))
            return self.send_json({"task": query, "count": len(results), "results": [x[1] for x in results[:limit]], "agent_note": "Treat metadata as discovery data. Verify provider documentation, credentials, rate limits and endpoint availability before execution."})

        if route.startswith("/category/"):
            wanted = urllib.parse.unquote(route[10:]).lower()
            values = [x for x in items if wanted in str(x.get("category", "")).lower()]
            return self.send_json({"category": wanted, "count": len(values), "results": values[:200]})

        if route.startswith("/provider/"):
            wanted = urllib.parse.unquote(route[10:]).lower()
            values = [x for x in items if wanted in str(x.get("name", "")).lower() or wanted in str(x.get("source", "")).lower()]
            return self.send_json({"provider": wanted, "count": len(values), "results": values[:200]})

        if route.startswith("/auth/"):
            wanted = urllib.parse.unquote(route[6:]).lower()
            values = [x for x in items if wanted in str(x.get("auth", "")).lower()]
            return self.send_json({"auth": wanted, "count": len(values), "results": values[:200]})

        if route == "/random":
            import random
            limit = min(max(int(params.get("limit", ["1"])[0]), 1), 50)
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

        if route.startswith("/api/"):
            wanted = urllib.parse.unquote(route[5:]).lower()
            for item in items:
                if canonical_url(item.get("api_url")) == canonical_url(wanted) or normalize(item.get("name")).lower() == wanted:
                    return self.send_json(item)
            return self.send_json({"error": "API not found"}, 404)

        return self.send_json({"error": "Route not found", "routes": ["/health", "/stats", "/sources", "/categories", "/search", "/select", "/api/{name-or-url}", "/category/{name}", "/provider/{name}", "/random", "/auth/{type}", "/export"]}, 404)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"free-api-index agent server listening on {PORT}")
    server.serve_forever()
