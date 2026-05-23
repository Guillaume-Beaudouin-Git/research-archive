#!/usr/bin/env python3
"""Inspect the latest snapshot of each alpha-hunt raw source.
Outputs a digest of titles/links so we can calibrate filters on real content.
"""
import json
import re
import sys
from glob import glob
from pathlib import Path
import xml.etree.ElementTree as ET

RAW_DIR = Path.home() / "projects/Algo_claude/_automation/alpha_hunt/_raw"

def latest(pattern):
    files = sorted(glob(str(RAW_DIR / pattern)))
    return files[-1] if files else None

def section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")

def parse_rss(path, ns=None):
    """Generic RSS/Atom title+link extractor."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        # Strip namespaces from tags for simplicity
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        items = root.findall('.//item') + root.findall('.//entry')
        results = []
        for it in items[:30]:
            title_el = it.find('title')
            link_el = it.find('link')
            title = (title_el.text or "").strip() if title_el is not None else "(no title)"
            link = ""
            if link_el is not None:
                link = link_el.text or link_el.get('href') or ""
            results.append((title, link))
        return results
    except Exception as e:
        return [(f"PARSE ERROR: {e}", "")]

# === HN (date-sorted to get fresh) ===
section("HN quant (note: current fetch is BY RELEVANCE = stale)")
f = latest("hn_quant_*.json")
if f:
    with open(f) as fh:
        data = json.load(fh)
    for h in data.get('hits', [])[:15]:
        ts = h.get('created_at', '')[:10]
        pts = h.get('points', 0)
        print(f"  [{ts} pts={pts}] {h.get('title', '(none)')}")

section("HN algotrading")
f = latest("hn_algotrading_*.json")
if f:
    with open(f) as fh:
        data = json.load(fh)
    for h in data.get('hits', [])[:15]:
        ts = h.get('created_at', '')[:10]
        pts = h.get('points', 0)
        print(f"  [{ts} pts={pts}] {h.get('title', '(none)')}")

# === Quantocracy ===
section("Quantocracy")
f = latest("quantocracy_*.xml")
if f:
    items = parse_rss(f)
    print(f"  ({len(items)} items)")
    for title, link in items[:20]:
        print(f"  - {title[:90]}")

# === QuantInsti ===
section("QuantInsti")
f = latest("quantinsti_*.xml")
if f:
    items = parse_rss(f)
    print(f"  ({len(items)} items)")
    for title, link in items[:15]:
        print(f"  - {title[:90]}")

# === Quantpedia ===
section("Quantpedia")
f = latest("quantpedia_*.xml")
if f:
    items = parse_rss(f)
    print(f"  ({len(items)} items)")
    for title, link in items[:15]:
        print(f"  - {title[:90]}")

# === arxiv econ.EM ===
section("arxiv econ.EM (last 15)")
f = latest("arxiv_econ_em_*.xml")
if f:
    items = parse_rss(f)
    print(f"  ({len(items)} items)")
    for title, link in items[:15]:
        print(f"  - {title[:90]}")

# === GitHub Trending Python ===
section("GitHub Trending Python")
f = latest("github_trending_python_*.html")
if f:
    html = Path(f).read_text()
    # Repo links live in <h2 class="h3 lh-condensed"><a href="/owner/repo">
    matches = re.findall(r'<h2 class="h3 lh-condensed">\s*<a[^>]*href="(/[^"]+)"', html)
    print(f"  ({len(matches)} repos)")
    for m in matches[:15]:
        print(f"  - github.com{m}")

print()
