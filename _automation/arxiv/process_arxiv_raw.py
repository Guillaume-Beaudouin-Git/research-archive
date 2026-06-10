"""process_arxiv_raw.py — distill _raw/<date>.xml (Atom) into _staging/<date>.json.

VPS-side, stdlib only (mirrors alpha_hunt/process_raw_filter.py pattern).
Only NEW entries are staged: ids already present in _seen/ (monthly buckets +
legacy _seen.json) or in existing _staging files are skipped. The cloud arxiv
routine remains the sole WRITER of _seen/ — this script reads it only.
Raw XMLs stay VPS-local (gitignored since 2026-06-10, purged >7d by fetch_arxiv.sh).
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(__file__)
RAW_DIR = os.path.join(ROOT, "_raw")
SEEN_DIR = os.path.join(ROOT, "_seen")
STAGING_DIR = os.path.join(ROOT, "_staging")
NS = {"atom": "http://www.w3.org/2005/Atom"}


def short_id(atom_id: str) -> str:
    """http://arxiv.org/abs/2606.01234v2 -> 2606.01234"""
    m = re.search(r"abs/([0-9.]+?)(v\d+)?$", atom_id)
    return m.group(1) if m else atom_id


def load_seen_ids() -> set:
    ids: set = set()
    candidates = [os.path.join(ROOT, "_seen.json")]
    candidates += sorted(glob.glob(os.path.join(SEEN_DIR, "*.json")))
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                ids.update(json.load(f).keys())
        except Exception as e:
            print(f"WARN seen {path}: {e}", file=sys.stderr)
    return ids


def staged_ids() -> set:
    ids: set = set()
    for path in glob.glob(os.path.join(STAGING_DIR, "*.json")):
        try:
            with open(path) as f:
                ids.update(e["id"] for e in json.load(f))
        except Exception as e:
            print(f"WARN staging {path}: {e}", file=sys.stderr)
    return ids


def main() -> None:
    os.makedirs(STAGING_DIR, exist_ok=True)
    xmls = sorted(glob.glob(os.path.join(RAW_DIR, "*.xml")))
    if not xmls:
        print("no raw xml files")
        return
    skip = load_seen_ids() | staged_ids()

    for fx in xmls:
        date = os.path.basename(fx)[:-4]
        out_path = os.path.join(STAGING_DIR, f"{date}.json")
        if os.path.exists(out_path):
            continue
        try:
            root = ET.parse(fx).getroot()
        except Exception as e:
            print(f"WARN parse {fx}: {e}", file=sys.stderr)
            continue
        entries = []
        for e in root.findall("atom:entry", NS):
            sid = short_id((e.findtext("atom:id", "", NS) or "").strip())
            if not sid or sid in skip:
                continue
            skip.add(sid)
            entries.append({
                "id": sid,
                "title": re.sub(r"\s+", " ", e.findtext("atom:title", "", NS) or "").strip(),
                "summary": re.sub(r"\s+", " ",
                                  e.findtext("atom:summary", "", NS) or "").strip()[:1500],
                "authors": [a.findtext("atom:name", "", NS)
                            for a in e.findall("atom:author", NS)][:8],
                "categories": [c.get("term") for c in e.findall("atom:category", NS)],
                "published": e.findtext("atom:published", "", NS),
                "updated": e.findtext("atom:updated", "", NS),
            })
        if entries:
            tmp = out_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(entries, f, indent=1, ensure_ascii=False)
            os.replace(tmp, out_path)
            print(f"{date}: {len(entries)} new entries -> _staging/{date}.json")
        else:
            print(f"{date}: 0 new entries (all seen/staged)")


if __name__ == "__main__":
    main()
