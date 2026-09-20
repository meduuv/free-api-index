import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = {
    "—": "-",
    "–": "-",
    "the ultimate": "the",
    "seamlessly": "",
    "cutting-edge": "",
    "comprehensive": "",
    "powerful": "",
    "robust": "",
    "unlock": "",
    "revolutionary": "",
    "in today's world": "",
    "whether you're": "for",
    "designed to": "built to",
    "allows you to": "lets you"
}

def clean_text(text):
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

def main():
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(clean_text(text), encoding="utf-8")

if __name__ == "__main__":
    main()
