"""
Build data/tops.json from already-downloaded XMLs in data/xml_updates/.
Usage: uv run python bin/build_tops_json.py
"""
import json
from pathlib import Path
from practicepreach.tools import build_tops_lookup

XML_DIR = Path("data/xml_updates")
TOPS_JSON = Path("data/tops.json")

tops = {}
for xml_file in sorted(XML_DIR.glob("*.xml")):
    tops.update(build_tops_lookup(str(xml_file)))

TOPS_JSON.write_text(json.dumps(tops, ensure_ascii=False, indent=2))
print(f"Saved {TOPS_JSON} ({len(tops)} TOPs)")
