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
PORT = int(os.getenv("PORT", "8787"))
CACHE_TTL = int(os.getenv("API_INDEX_CACHE_TTL", "21600"))
MAX_RESULTS = int(os.getenv("API_INDEX_MAX_RESULTS", "500"))
MAX_SCHEMA_OPERATIONS = int(os.getenv("API_INDEX_MAX_SCHEMA_OPERATIONS", "1000"))
REMOTE_JSON = [
    ("public-api-lists/public-api-lists", "https://raw.githubusercontent.com/public-api-lists/public-api-lists/master/api/all.json"),
    ("Manavarya09/public-apis-live", "https://raw.githubusercontent.com/Manavarya09/public-apis-live/main/data/apis.json")
]
ULTIMATE_BASE = "https://raw.githubusercontent.com/kawsarlog/Ultimate-API-List/main"
ULTIMATE_CATEGORIES = ["AI","Agents","Automation","Developer_tools","Ecommerce","Integrations","Jobs","Lead_generation","MCP_servers","News","Open_source","Other","Real_estate","SEO_tools","Social_media","Travel","Videos"]
JENTIC_BASE = "https://raw.githubusercontent.com/jentic/jentic-public-apis/main/index/apis/openapi"
JENTIC_BUCKETS = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["~rest"]
APIS_GURU_URL = "https://api.apis.guru/v2/list.json"
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

def item(name, url, description="", category="Other", source="unknown", auth="unknown", spec_url="", provider=""):
    if not name or not url:
        return None
    return {
        "name": normalize(name),
        "api_url": normalize(url),
        "description": normalize(description),
        "auth": normalize(auth or "unknown"),
        "https": "yes" if str(url).startswith("https://") else "no",
        "cors": "unknown",
        "category": normalize(category or "Other"),
        "source": source,
        "spec_url": normalize(spec_url),
        "provider": normalize(provider)
    }

def normalize_item(value, source, category="Other"):
    if not isinstance(value, dict):
        return None
    name = normalize(value.get("name") or value.get("title") or value.get("API") or value.get("api") or value.get("service"))
    url = normalize(value.get("api_url") or value.get("url") or value.get("endpoint") or value.get("link"))
    if not name or not url or not url.startswith(("http://", "https://")):
        return None
    return item(
        name,
        url,
        value.get("description") or value.get("Description") or value.get("desc"),
        category or value.get("category") or value.get("Category") or "Other",
        source,
        value.get("auth") or value.get("Auth") or "unknown",
        value.get("spec_url") or "",
        value.get("provider") or ""
    )

def parse_json_payload(payload, source):
    if isinstance(payload, dict):
        for key in ("apis", "entries", "data", "items", "results"):
            if isinstance(payload.get(key), list):
                return [x for x in (normalize_item(v, source) for v in payload[key]) if x]
        value = normalize_item(payload, source)
        return [value] if value else []
    if isinstance(payload, list):
        return [x for x in (normalize_item(v, source) for v in payload) if x]
    return []

def fetch_url(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "free-api-index/4.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")

def fetch_json(url, source):
    try:
        return parse_json_payload(json.loads(fetch_url(url)), source)
    except Exception:
        return []

def parse_markdown(text, source, category="Other"):
    rows = []
    for line in text.splitlines():
        if not line.strip().startswith("|") or line.count("|") < 3:
            continue
        cells = [normalize(x) for x in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"api","name","service","api name"}:
            continue
        if re.fullmatch(r"[-: ]+", cells[0]):
            continue
        urls = re.findall(r"https?://[^\s|)]+", line)
        if urls:
            value = normalize_item({"name": cells[0], "api_url": urls[0], "description": cells[1]}, source, category)
            if value:
                rows.append(value)
    return rows

def fetch_readme(repo):
    try:
        return parse_markdown(fetch_url(f"https://raw.githubusercontent.com/{repo}/HEAD/README.md"), repo)
    except Exception:
        return []

def fetch_ultimate(category):
    try:
        return parse_markdown(fetch_url(f"{ULTIMATE_BASE}/{urllib.parse.quote(category)}/README.md"), f"kawsarlog/Ultimate-API-List:{category}", category)
    except Exception:
        return []

def fetch_jentic_bucket(bucket):
    try:
        return fetch_url(f"{JENTIC_BASE}/{urllib.parse.quote(bucket)}/README.md")
    except Exception:
        return ""

def parse_jentic(text):
    rows = []
    pattern = r"\[([^\]]+)\]\(\.\./\.\./\.\./\.\./apis/openapi/([^)/]+)(?:/([^)/]+))?\)"
    for line in text.splitlines():
        if not line.startswith("| ["):
            continue
        matches = re.findall(pattern, line)
        if not matches:
            continue
        vendor = matches[0][1]
        subs = sorted({x[2] for x in matches[1:] if x[1] == vendor and x[2]})
        if not subs:
            subs = [""]
        for sub in subs:
            path = f"{vendor}/{sub}" if sub else vendor
            directory = f"https://github.com/jentic/jentic-public-apis/tree/main/apis/openapi/{urllib.parse.quote(path, safe='/')}"
            name = f"{vendor} {sub}".strip()
            rows.append(item(name, directory, f"Machine-readable OpenAPI catalog entry for {name}", "Jentic", "jentic/jentic-public-apis", "unknown", "", vendor))
    return rows

def fetch_jentic():
    result = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(fetch_jentic_bucket, x) for x in JENTIC_BUCKETS]
        for future in as_completed(futures):
            try:
                result.extend(parse_jentic(future.result()))
            except Exception:
                pass
    return result

def fetch_apis_guru():
    try:
        payload = json.loads(fetch_url(APIS_GURU_URL))
    except Exception:
        return []
    result = []
    for provider, api in payload.items():
        if not isinstance(api, dict):
            continue
        versions = api.get("versions") or {}
        preferred = api.get("preferred")
        version = versions.get(preferred) if preferred else None
        if not isinstance(version, dict):
            version = next(iter(versions.values()), None)
        if not isinstance(version, dict):
            continue
        info = version.get("info") or {}
        title = normalize(info.get("title") or provider)
        spec = normalize(version.get("swaggerUrl") or version.get("swaggerYamlUrl"))
        if not title or not spec:
            continue
        result.append(item(title, spec, info.get("description") or f"OpenAPI specification for {title}", "APIs.guru", "APIs-guru/openapi-directory", "unknown", spec, provider))
    return result

def dedupe(values):
    result = {}
    for value in values:
        key = canonical_url(value.get("api_url")) or normalize(value.get("name")).lower()
        if key not in result:
            result[key] = value
            continue
        current = result[key]
        if len(value.get("description","")) > len(current.get("description","")):
            current["description"] = value["description"]
        if value.get("spec_url") and not current.get("spec_url"):
            current["spec_url"] = value["spec_url"]
        sources = current.get("source")
        other = value.get("source")
        source_set = set(sources if isinstance(sources, list) else [sources])
        source_set.update(other if isinstance(other, list) else [other])
        current["source"] = sorted(x for x in source_set if x)
    return list(result.values())

def load_sources():
    try:
        return json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def build_items(force=False):
    if not force and cache["items"] is not None and time.time() - cache["loaded"] < CACHE_TTL:
        return cache["items"]
    values = []
    try:
        values.extend(json.loads(DATA_FILE.read_text(encoding="utf-8")).get("apis", []))
    except Exception:
        pass
    for path in sorted((ROOT / "data" / "ultimate").glob("*.json")):
        try:
            values.extend(json.loads(path.read_text(encoding="utf-8")).get("apis", []))
        except Exception:
            pass
    sources = load_sources()
    repos = [x["repo"] for x in sources if x.get("mode") == "readme" and x.get("repo")]
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(fetch_json, url, name) for name, url in REMOTE_JSON]
        futures += [pool.submit(fetch_readme, repo) for repo in repos]
        futures += [pool.submit(fetch_ultimate, category) for category in ULTIMATE_CATEGORIES]
        futures.append(pool.submit(fetch_jentic))
        futures.append(pool.submit(fetch_apis_guru))
        for future in as_completed(futures):
            try:
                values.extend(future.result())
            except Exception:
                pass
    cache["items"] = dedupe(values)
    cache["loaded"] = time.time()
    return cache["items"]

def virtual_categories():
    return [f"{d} {m} for {t}" for d in DOMAINS for m in MODES for t in TARGETS]

def categories_for(values):
    return sorted({normalize(x.get("category")) for x in values if normalize(x.get("category"))})

def providers_for(values):
    result = set()
    for x in values:
        source = x.get("source", [])
        result.update(source if isinstance(source, list) else [source])
    return sorted(x for x in result if x)

def tokens(value):
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))

def score(value, query):
    wanted = tokens(query)
    if not wanted:
        return 1
    fields = [
        (tokens(value.get("name")), 12),
        (tokens(value.get("provider")), 9),
        (tokens(value.get("category")), 8),
        (tokens(value.get("source")), 5),
        (tokens(value.get("description")), 3),
        (tokens(value.get("spec_url")), 2)
    ]
    total = 0
    for token in wanted:
        best = 0
        for field, weight in fields:
            if token in field:
                best = max(best, weight)
        total += best
    return total

def filter_items(values, params):
    result = values
    for key in ("category","auth","https","source","provider"):
        wanted = params.get(key, [""])[0].lower()
        if wanted:
            result = [x for x in result if wanted in str(x.get(key,"")).lower()]
    return result

def limit_value(params, key, default, maximum):
    try:
        return min(max(int(params.get(key,[str(default)])[0]), 1), maximum)
    except Exception:
        return default

def expand_query(query):
    q = normalize(query).lower()
    aliases = {
        "weather": "forecast climate meteorological", "email": "mail smtp transactional messaging",
        "image": "photo picture vision media", "payments": "payment billing checkout",
        "currency": "forex exchange money rates", "maps": "geocoding geolocation directions places",
        "auth": "authentication authorization oauth login", "security": "cybersecurity vulnerability threat scanning",
        "translate": "translation language localization", "video": "media streaming",
        "database": "db storage sql nosql", "automation": "workflow jobs triggers integration",
        "ai": "artificial intelligence llm machine learning inference"
    }
    return " ".join([q] + [v for k, v in aliases.items() if k in q]).strip()

def rank(values, query, limit):
    query = expand_query(query)
    candidates = [(score(x, query), x) for x in values]
    candidates = [x for x in candidates if x[0] > 0]
    candidates.sort(key=lambda x: (-x[0], x[1].get("name","").lower()))
    return [x[1] for x in candidates[:limit]], len(candidates)

def resolve(values, query):
    wanted = normalize(query).lower()
    exact = [x for x in values if normalize(x.get("name")).lower() == wanted or canonical_url(x.get("api_url")) == canonical_url(wanted)]
    if exact:
        return exact[0]
    ranked, _ = rank(values, query, 1)
    return ranked[0] if ranked else None

def related(values, target, limit):
    base = tokens(target.get("name")) | tokens(target.get("category")) | tokens(target.get("description"))
    ranked = []
    for value in values:
        if value is target:
            continue
        overlap = len(base & (tokens(value.get("name")) | tokens(value.get("category")) | tokens(value.get("description"))))
        if overlap:
            ranked.append((overlap, value))
    ranked.sort(key=lambda x: (-x[0], x[1].get("name","").lower()))
    return [x[1] for x in ranked[:limit]]

def load_spec(url):
    try:
        return json.loads(fetch_url(url, 20))
    except Exception:
        return None

def summarize_spec(spec):
    if not isinstance(spec, dict):
        return {}
    info = spec.get("info") or {}
    paths = spec.get("paths") or {}
    operations = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in {"get","post","put","patch","delete","head","options","trace"} or not isinstance(op, dict):
                continue
            operations.append({
                "method": method.upper(),
                "path": path,
                "operation_id": normalize(op.get("operationId")),
                "summary": normalize(op.get("summary") or op.get("description"))
            })
    return {
        "title": normalize(info.get("title")),
        "description": normalize(info.get("description")),
        "version": normalize(info.get("version")),
        "servers": spec.get("servers") or [],
        "security": spec.get("security") or [],
        "operation_count": len(operations),
        "operations": operations[:MAX_SCHEMA_OPERATIONS]
    }

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
        values = build_items()

        if route == "/":
            return self.send_json({"name":"free-api-index","version":"4.0","apis":len(values),"sources":len(providers_for(values)),"routes":["/index","/search","/select","/recommend","/resolve","/related/{name}","/inspect","/operations","/api/{name-or-url}","/category/{name}","/provider/{name}","/source/{name}","/categories","/providers","/tags","/capabilities","/auth/{type}","/random","/export","/health","/stats","/sources","/reload","/developer"]})

        if route == "/health":
            return self.send_json({"ok":True,"apis":len(values),"categories":len(categories_for(values)),"providers":len(providers_for(values)),"virtual_categories":len(virtual_categories()),"cache_age_seconds":round(time.time()-cache["loaded"],2)})

        if route == "/stats":
            counts = {}
            for x in values:
                key = x.get("category") or "Other"
                counts[key] = counts.get(key,0) + 1
            return self.send_json({"apis":len(values),"categories":len(counts),"providers":len(providers_for(values)),"top_categories":sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:50]})

        if route == "/index":
            filtered = filter_items(values, params)
            query = params.get("q",[""])[0]
            if query:
                result,total = rank(filtered,query,limit_value(params,"size",50,500))
                page = limit_value(params,"page",1,1000000)
                size = limit_value(params,"size",50,500)
                return self.send_json({"page":page,"size":size,"total":total,"pages":(total+size-1)//size,"results":result})
            sort_key = params.get("sort",["name"])[0]
            filtered.sort(key=lambda x:(str(x.get(sort_key,"")).lower(),x.get("name","").lower()))
            size = limit_value(params,"size",50,500)
            page = limit_value(params,"page",1,1000000)
            start = (page-1)*size
            return self.send_json({"page":page,"size":size,"total":len(filtered),"pages":(len(filtered)+size-1)//size,"results":filtered[start:start+size]})

        if route in {"/search","/select","/recommend"}:
            query = params.get("task",params.get("q",[""]))[0]
            limit = limit_value(params,"limit",20 if route=="/search" else 10,MAX_RESULTS)
            result,total = rank(filter_items(values,params),query,limit)
            payload = {"query":query,"count":total,"results":result}
            if route != "/search":
                payload["agent_note"] = "Select candidates by task fit, then inspect the chosen OpenAPI schema before execution."
            if route == "/recommend":
                payload["selection_basis"] = ["name","provider","category","description","spec metadata"]
            return self.send_json(payload)

        if route == "/resolve":
            query = params.get("q",[""])[0]
            target = resolve(values,query)
            return self.send_json({"query":query,"match":target} if target else {"query":query,"error":"API not found"}, 200 if target else 404)

        if route.startswith("/related/"):
            target = resolve(values,urllib.parse.unquote(route[9:]))
            if not target:
                return self.send_json({"error":"API not found"},404)
            limit = limit_value(params,"limit",10,100)
            return self.send_json({"api":target,"results":related(values,target,limit)})

        if route == "/inspect":
            query = params.get("q",params.get("name",[""]))[0]
            target = resolve(values,query)
            if not target:
                return self.send_json({"error":"API not found"},404)
            spec_url = target.get("spec_url")
            if not spec_url and target.get("api_url","").lower().endswith(".json"):
                spec_url = target["api_url"]
            if not spec_url:
                return self.send_json({"api":target,"schema":None,"message":"This catalog entry has no direct OpenAPI document. Use its api_url or directory_url for provider discovery."})
            spec = load_spec(spec_url)
            if not spec:
                return self.send_json({"api":target,"schema":None,"error":"OpenAPI document unavailable"},502)
            return self.send_json({"api":target,"schema":summarize_spec(spec)})

        if route == "/operations":
            query = params.get("q",params.get("task",[""]))[0]
            limit = limit_value(params,"limit",10,100)
            ranked,total = rank(filter_items(values,params),query,limit)
            results = []
            for target in ranked:
                spec_url = target.get("spec_url")
                if not spec_url and target.get("api_url","").lower().endswith(".json"):
                    spec_url = target["api_url"]
                if not spec_url:
                    continue
                spec = load_spec(spec_url)
                if spec:
                    results.append({"api":target,"schema":summarize_spec(spec)})
            return self.send_json({"query":query,"count":len(results),"candidates":total,"results":results})

        if route.startswith("/api/"):
            target = resolve(values,urllib.parse.unquote(route[5:]))
            return self.send_json(target if target else {"error":"API not found"},200 if target else 404)

        if route == "/categories":
            return self.send_json({"count":len(categories_for(values)),"categories":categories_for(values),"virtual_count":len(virtual_categories()),"virtual_categories":virtual_categories()})

        if route.startswith("/category/"):
            wanted = urllib.parse.unquote(route[10:]).lower()
            result = [x for x in values if wanted in str(x.get("category","")).lower()]
            result.sort(key=lambda x:x.get("name","").lower())
            return self.send_json({"category":wanted,"count":len(result),"results":result[:500]})

        if route == "/providers":
            return self.send_json({"count":len(providers_for(values)),"providers":providers_for(values)})

        if route.startswith("/provider/"):
            wanted = urllib.parse.unquote(route[10:]).lower()
            result = [x for x in values if wanted in str(x.get("provider","")).lower() or wanted in str(x.get("source","")).lower() or wanted in x.get("name","").lower()]
            return self.send_json({"provider":wanted,"count":len(result),"results":result[:500]})

        if route.startswith("/source/"):
            wanted = urllib.parse.unquote(route[8:]).lower()
            result = [x for x in values if wanted in str(x.get("source","")).lower()]
            return self.send_json({"source":wanted,"count":len(result),"results":result[:500]})

        if route == "/tags":
            tags = sorted(set(DOMAINS + MODES + TARGETS + categories_for(values)))
            return self.send_json({"count":len(tags),"tags":tags})

        if route == "/capabilities":
            query = params.get("q",[""])[0]
            caps = virtual_categories()
            if query:
                wanted = tokens(query)
                caps = [x for x in caps if wanted.issubset(tokens(x))]
            return self.send_json({"query":query,"count":len(caps),"capabilities":caps})

        if route.startswith("/auth/"):
            wanted = urllib.parse.unquote(route[6:]).lower()
            result = [x for x in values if wanted in str(x.get("auth","")).lower()]
            return self.send_json({"auth":wanted,"count":len(result),"results":result[:500]})

        if route == "/random":
            limit = limit_value(params,"limit",1,50)
            return self.send_json({"count":limit,"results":random.sample(values,min(limit,len(values)))})

        if route == "/export":
            result = filter_items(values,params)
            if params.get("format",["json"])[0].lower() == "ndjson":
                body = "".join(json.dumps(x,ensure_ascii=False)+"\n" for x in result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type","application/x-ndjson; charset=utf-8")
                self.send_header("Content-Length",str(len(body)))
                self.send_header("Access-Control-Allow-Origin","*")
                self.end_headers()
                self.wfile.write(body)
                return
            return self.send_json({"count":len(result),"apis":result})

        if route == "/reload":
            result = build_items(True)
            return self.send_json({"ok":True,"apis":len(result)})

        if route == "/sources":
            return self.send_json({"count":len(load_sources()),"sources":load_sources()})

        if route == "/developer":
            return self.send_json({"name":"free-api-index developer interface","base":f"http://localhost:{PORT}","examples":{"search":"/search?q=weather","select":"/select?task=free+weather+forecast","inspect":"/inspect?q=GitHub","operations":"/operations?task=send+email","index":"/index?page=1&size=50","export":"/export?format=ndjson"},"rules":["Discovery metadata only","Credentials are never returned","Verify provider documentation and limits","Inspect schemas before execution","Use the best matching API for the task instead of loading the whole catalog into the agent context"]})

        return self.send_json({"error":"Route not found"},404)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = ThreadingHTTPServer((os.getenv("HOST", "0.0.0.0"),PORT),Handler)
    print(f"free-api-index agent server listening on {PORT}")
    server.serve_forever()
