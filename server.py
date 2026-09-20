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
CACHE_TTL = int(os.getenv("API_INDEX_CACHE_TTL", "21600"))
PORT = int(os.getenv("PORT", "8787"))
REMOTE_SOURCES = [
    {"name": "public-api-lists", "url": "https://raw.githubusercontent.com/public-api-lists/public-api-lists/master/api/all.json"},
    {"name": "public-apis-live", "url": "https://raw.githubusercontent.com/Manavarya09/public-apis-live/main/data/apis.json"}
]
ULTIMATE_CATEGORIES = ["AI","Agents","Automation","Developer_tools","Ecommerce","Integrations","Jobs","Lead_generation","MCP_servers","News","Open_source","Other","Real_estate","SEO_tools","Social_media","Travel","Videos"]
ULTIMATE_BASE = "https://raw.githubusercontent.com/kawsarlog/Ultimate-API-List/main"
DOMAINS = ["AI","Agents","Automation","Analytics","Animals","Anime","Anti Malware","Art","Authentication","Blockchain","Books","Business","Calendar","Cloud","Commerce","Communication","Crypto","Currency","Data","Databases","Development","Documents","Education","Email","Entertainment","Environment","Events","Finance","Food","Games","Geocoding","Government","Health","Images","Jobs","Maps","Marketing","Media","Machine Learning","Messaging","Music","News","Open Data","Open Source","Payments","Productivity","Programming","Science","Search","Security","Social","Space","Sports","Storage","Testing","Text","Translation","Transportation","Travel","Video","Voice","Weather"]
MODES = ["lookup","search","generation","conversion","validation","analysis","monitoring","automation"]
TARGETS = ["agent","application","website","developer","data","workflow","research","security"]
cache = {"items": None, "loaded": 0.0}

def normalize(value):
    value = str(value or "").strip()
    value = re.sub(r"!\\[[^]]*\\]\\([^)]*\\)", "", value)
    value = re.sub(r"[*_~", "", value)
    value = value.replace("—", "-").replace("–", "-")
    return re.sub(r"\\s+", " ", value).strip(" -|")

def canonical_url(value):
    return re.sub(r"^https?://", "", normalize(value).lower().rstrip("/"))

def normalize_item(item, source):
    if not isinstance(item, dict):
        return None
    name = normalize(item.get("name") or item.get("title") or item.get("API") or item.get("api"))
    url = normalize(item.get("api_url") or item.get("url") or item.get("endpoint") or item.get("link"))
    if not name or not url or not url.startswith(("http://", "https://")):
        return None
    return {"name": name, "api_url": url, "description": normalize(item.get("description") or item.get("Description")), "auth": normalize(item.get("auth") or item.get("Auth") or "unknown"), "https": normalize(item.get("https") or item.get("HTTPS") or "unknown"), "cors": normalize(item.get("cors") or item.get("CORS") or "unknown"), "category": normalize(item.get("category") or item.get("Category") or "Other"), "source": source}

def parse_json_payload(payload, source):
    if isinstance(payload, dict):
        for key in ("apis", "entries", "data", "items", "results"):
            if isinstance(payload.get(key), list):
                return [normalize_item(x, source) for x in payload[key]]
        return [normalize_item(payload, source)]
    if isinstance(payload, list):
        return [normalize_item(x, source) for x in payload]
    return []

def fetch_json(url, source):
    request = urllib.request.Request(url, headers={"User-Agent": "free-api-index-agent/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    return [x for x in parse_json_payload(payload, source) if x]

def parse_markdown(text, source, category):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.count("|") < 3:
            continue
        cells = [normalize(x) for x in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"api", "name", "service"}:
            continue
        if all(ch == "-" for ch in cells[0]):
            continue
        urls = re.findall(r"https?://[^\\s|)]+", line)
        if urls:
            rows.append(normalize_item({"name": cells[0], "api_url": urls[0], "description": cells[1], "category": category}, source))
    return [x for x in rows if x]

def fetch_ultimate_one(category):
    try:
        request = urllib.request.Request(f"{ULTIMATE_BASE}/{urllib.parse.quote(category)}/README.md", headers={"User-Agent": "free-api-index-agent/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8", "replace")
        return parse_markdown(text, f"kawsarlog/Ultimate-API-List:{category}", category)
    except Exception:
        return []

def fetch_ultimate():
    items = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_ultimate_one, category) for category in ULTIMATE_CATEGORIES]
        for future in as_completed(futures):
            items.extend(future.result())
    return items

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
        values = set()
        for value in (current.get("source"), item.get("source")):
            values.update(value if isinstance(value, list) else [value])
        current["source"] = sorted(x for x in values if x)
    return list(result.values())

def build_items():
    if cache["items"] is not None and time.time() - cache["loaded"] < CACHE_TTL:
        return cache["items"]
    with DATA_FILE.open("r", encoding="utf-8") as f:
        items = list(json.load(f).get("apis", []))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fetch_json, source["url"], source["name"]) for source in REMOTE_SOURCES]
        for future in as_completed(futures):
            try:
                items.extend(future.result())
            except Exception:
                pass
    items.extend(fetch_ultimate())
    cache["items"] = dedupe(items)
    cache["loaded"] = time.time()
    return cache["items"]

def virtual_categories():
    return [f"{domain} {mode} for {target}" for domain in DOMAINS for mode in MODES for target in TARGETS]

def score(item, query):
    parts = query.lower().split()
    name = str(item.get("name", "")).lower()
    category = str(item.get("category", "")).lower()
    text = " ".join([name, category, str(item.get("description", "")).lower()])
    value = 0
    for part in parts:
        if part in name:
            value += 5
        elif part in category:
            value += 3
        elif part in text:
            value += 1
        else:
            return 0
    return value

class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
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
        if parsed.path == "/health":
            return self.send_json({"ok": True, "apis": len(items), "categories": len(virtual_categories())})
        if parsed.path == "/stats":
            return self.send_json({"apis": len(items), "categories": len(virtual_categories()), "sources": len({str(x.get("source")) for x in items}), "cache_age_seconds": round(time.time() - cache["loaded"], 2)})
        if parsed.path == "/categories":
            values = virtual_categories()
            return self.send_json({"count": len(values), "categories": values})
        if parsed.path in {"/search", "/select"}:
            query = params.get("q", params.get("task", [""]))[0]
            category = params.get("category", [""])[0].lower()
            auth = params.get("auth", [""])[0].lower()
            limit = min(max(int(params.get("limit", ["20"])[0]), 1), 200)
            results = []
            for item in items:
                if category and category not in str(item.get("category", "")).lower():
                    continue
                if auth and auth != str(item.get("auth", "")).lower():
                    continue
                value = score(item, query) if query else 1
                if value:
                    results.append((value, item))
            results.sort(key=lambda x: (-x[0], x[1].get("name", "")))
            payload = {"query": query, "count": len(results), "results": [x[1] for x in results[:limit]]}
            if parsed.path == "/select":
                payload["agent_note"] = "Choose using task fit, authentication, HTTPS, CORS, source and documentation. Verify availability before use."
            return self.send_json(payload)
        if parsed.path.startswith("/api/"):
            wanted = urllib.parse.unquote(parsed.path[5:]).lower()
            for item in items:
                if canonical_url(item.get("api_url")) == canonical_url(wanted) or normalize(item.get("name")).lower() == wanted:
                    return self.send_json(item)
            return self.send_json({"error": "API not found"}, 404)
        return self.send_json({"name": "free-api-index-agent-server", "endpoints": ["/health", "/stats", "/categories", "/search?q=weather", "/select?task=weather forecast", "/api/{name-or-url}"]})

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"free-api-index agent server listening on {PORT}")
    server.serve_forever()
