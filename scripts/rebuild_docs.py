import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "APIs.md"

def clean(value):
    value = str(value or "").replace("|", "\\|").replace("\\n", " ")
    return re.sub(r"\\s+", " ", value).strip()

def load_file(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("apis", []) if isinstance(payload, dict) else []
    except Exception:
        return []

def canonical(value):
    return re.sub(r"^https?://", "", str(value or "").strip().lower().rstrip("/"))

items = []
items.extend(load_file(DATA / "apis.json"))
for path in sorted((DATA / "ultimate").glob("*.json")):
    items.extend(load_file(path))

seen = {}
for item in items:
    url = canonical(item.get("api_url"))
    key = url or clean(item.get("name")).lower()
    if not key:
        continue
    if key not in seen:
        seen[key] = item
    elif len(clean(item.get("description"))) > len(clean(seen[key].get("description"))):
        seen[key] = item

items = sorted(seen.values(), key=lambda x: (clean(x.get("category")).lower(), clean(x.get("name")).lower()))

lines = [
    "# API Index",
    "",
    f"Generated from {len(items):,} deduplicated local records.",
    "",
    "For the agent API, see docs/ROUTES.md.",
    "",
    "| API | Description | Auth | HTTPS | CORS | Category | Source |",
    "|---|---|---|---|---|---|---|"
]

for item in items:
    name = clean(item.get("name"))
    url = clean(item.get("api_url"))
    source = item.get("source")
    if isinstance(source, list):
        source = ", ".join(source)
    source = clean(source)
    if url:
        name = f"[{name}]({url})"
    lines.append("| " + " | ".join([
        name,
        clean(item.get("description")),
        clean(item.get("auth") or "unknown"),
        clean(item.get("https") or "unknown"),
        clean(item.get("cors") or "unknown"),
        clean(item.get("category") or "Other"),
        source
    ]) + " |")

OUT.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print(f"wrote {len(items)} records")
