"""
Alpha Hunt – raw filter pipeline (filtering only, no md generation).

Parses all _raw/* files, applies L0/L1/L2 filters, dedupes via _seen.json.
For each accepted item, writes _staging/<hash>.json containing the raw data +
filter results. The LLM in the routine takes over for markdown generation.
"""

import json, glob, hashlib, re, os, sys
from datetime import datetime, timezone
from html import unescape
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error

ROOT_DIR    = os.path.dirname(__file__)
RAW_DIR     = os.path.join(ROOT_DIR, "_raw")
SEEN_FILE   = os.path.join(ROOT_DIR, "_seen.json")
STAGING_DIR = os.path.join(ROOT_DIR, "_staging")
NOW         = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
NOW_SLUG    = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

os.makedirs(STAGING_DIR, exist_ok=True)

# ── helpers ───────────────────────────────────────────────────────────────────

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

def slug(s: str, maxlen: int = 50) -> str:
    s = unescape(s).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:maxlen]

def clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", unescape(s)).strip()

# ── _seen.json ────────────────────────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            d = json.load(f)
        d.setdefault("items_seen", {})
        return d
    return {"last_run": None, "items_seen": {}}

# ── parsers ───────────────────────────────────────────────────────────────────

def parse_hn_json(files, source_tag):
    items = {}
    for fpath in sorted(files):
        try:
            with open(fpath) as f:
                data = json.load(f)
            for hit in data.get("hits", []):
                oid = hit.get("objectID", "")
                if oid and oid not in items:
                    items[oid] = {
                        "source": source_tag,
                        "canonical_id": oid,
                        "title": hit.get("title", ""),
                        "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={oid}",
                        "description": clean_html(hit.get("story_text") or ""),
                        "points": hit.get("points", 0),
                        "created_at": hit.get("created_at", ""),
                    }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(items.values())

def parse_rss_xml(files, source_tag):
    items = {}
    for fpath in sorted(files):
        try:
            tree = ET.parse(fpath)
            channel = tree.getroot().find("channel")
            if channel is None:
                continue
            for item in channel.findall("item"):
                link = (item.findtext("link") or "").strip()
                if not link or link in items:
                    continue
                title = (item.findtext("title") or "").strip()
                desc = clean_html(item.findtext("description") or "")
                items[link] = {
                    "source": source_tag,
                    "canonical_id": link,
                    "title": unescape(title),
                    "url": link,
                    "description": desc,
                    "points": None,
                }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(items.values())

def parse_quantocracy_digests(files):
    """Quantocracy publishes digests; each digest links to ~15 individual articles."""
    articles = {}
    digest_urls_seen = set()
    for fpath in sorted(files):
        try:
            tree = ET.parse(fpath)
            channel = tree.getroot().find("channel")
            if channel is None:
                continue
            for digest in channel.findall("item"):
                content = digest.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "") or ""
                # Patterns observed: <a class="qo-title" href="..."> or <a href="..." target="_blank">
                matches = re.findall(
                    r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
                    content
                )
                for url, title in matches:
                    title = unescape(title.strip())
                    if not title or len(title) < 10:
                        continue
                    if url in articles:
                        continue
                    # Extract surrounding context (50-200 chars before/after the link)
                    pos = content.find(url)
                    context = ""
                    if pos > 0:
                        start = max(0, pos - 50)
                        end = min(len(content), pos + len(url) + 300)
                        context = clean_html(content[start:end])
                    articles[url] = {
                        "source": "quantocracy",
                        "canonical_id": url,
                        "title": title,
                        "url": url,
                        "description": context,
                        "points": None,
                    }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(articles.values())

def parse_github_trending(files):
    items = {}
    for fpath in sorted(files):
        try:
            with open(fpath) as f:
                html = f.read()
            # Match <h2 class="h3 lh-condensed"><a href="/owner/repo">
            repos = re.findall(
                r'<h2 class="h3 lh-condensed">\s*<a[^>]+href="(/[^"]+)"',
                html
            )
            for repo_path in repos:
                if repo_path in items:
                    continue
                # Extract description (the <p> following the h2)
                desc_match = re.search(
                    rf'href="{re.escape(repo_path)}".*?<p[^>]*>(.*?)</p>',
                    html, re.S
                )
                desc = clean_html(desc_match.group(1)) if desc_match else ""
                items[repo_path] = {
                    "source": "github_python",
                    "canonical_id": repo_path,
                    "title": repo_path.lstrip("/"),
                    "url": f"https://github.com{repo_path}",
                    "description": desc,
                    "points": None,
                }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(items.values())

def parse_arxiv(files):
    items = {}
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for fpath in sorted(files):
        try:
            tree = ET.parse(fpath)
            for entry in tree.getroot().findall("atom:entry", ns):
                arxiv_id = entry.findtext("atom:id", "", ns).strip()
                if not arxiv_id or arxiv_id in items:
                    continue
                title = (entry.findtext("atom:title", "", ns) or "").strip()
                summary = (entry.findtext("atom:summary", "", ns) or "").strip()
                summary = re.sub(r"\s+", " ", summary)
                items[arxiv_id] = {
                    "source": "arxiv_econ_em",
                    "canonical_id": arxiv_id,
                    "title": unescape(title),
                    "url": arxiv_id,
                    "description": unescape(summary),
                    "points": None,
                }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(items.values())

# ── filters L0/L1/L2 ──────────────────────────────────────────────────────────

L0_TITLE_PATTERNS = [
    r"what indicator should",
    r"is my system overfitted",
    r"how to start algo trading",
    r"best broker",
    r"review my strategy",
    r"made \d+%.{0,15}month",
    r"\b(course|signal seller|discord|telegram group|VIP|premium subscription)\b",
    r"join my (discord|telegram)",
]

QUANT_KEYWORDS = [
    r"\btrading\b", r"\bquant\b", r"\bfinance\b", r"\bforecast\b",
    r"\btime.series\b", r"\bportfolio\b", r"\bbacktest\b", r"\balpha\b",
    r"\bmarket\b", r"\bsignal\b", r"\bstrategy\b",
]

HN_FINANCE_KEYWORDS = QUANT_KEYWORDS + [
    r"\boptions?\b", r"\bderivatives?\b", r"\bcrypto\b", r"\bbtc\b", r"\beth\b",
    r"\bfutures?\b", r"\bvolatility\b", r"\bmomentum\b", r"\barbitrage\b",
]

ARXIV_FINANCE_KEYWORDS = [
    r"forecast", r"predict", r"regime", r"volatility", r"trading",
    r"portfolio", r"momentum", r"factor model", r"asset pric", r"market",
    r"return", r"risk premium", r"hedg", r"sharpe", r"deflated",
]

ARXIV_OFFTOPIC_PATTERNS = [
    r"\bfilm\b", r"\bnightlight", r"\bquantum game\b", r"\bhealthcare\b",
    r"\bschool\b", r"\beducation\b", r"\bnutrition\b", r"\bgender\b",
    r"\bclimate model\b", r"\bfertility\b",
]

L1_PATTERNS = {
    "metrics": r"sharpe|maxdd|max.?drawdown|profit.factor|win.rate|calmar|sortino|cagr|drawdown",
    "code_quant": r"vectorbt|zipline|qlib|nautilus.?trader|backtrader|python.*backtest|backtest.*python|github\.com/.+strateg",
    "methodology": r"lopez.de.prado|bailey|politis.romano|newey.west|HAC|AMTP|deflated.sharpe|walk.forward|walk-forward|block.bootstrap|DSR|fama.french|markowitz|adf.test|cointegrat|regime.detect|markov.switching|expanding.window|out.of.sample|out-of-sample|EGARCH|GARCH|cross.sectional|information.coefficient|multiple.testing|stress.test.*trading",
    "macro_trading": r"FOMC|yield.curve|funding.rate|basis.spread|carry.trade|term.spread|credit.spread|VIX.*strateg|macroeconomic.*signal",
    "quant_tool": r"nautilustrader|vectorbt|zipline|qlib|backtrader",
}

L1_TRADING_TOPIC = r"trad|strateg|momentum|regime|backtest|signal|alpha|portfolio|risk|hedg|volatility|return|carry|basis|drawdown|sharpe|forecast"

L2_REJECT_PATTERNS = [
    r"refinitiv|factset|bloomberg terminal|quandl premium|ICE data",
    r"prime broker|dark pool|market maker relationship",
    r"level.?2 data|level.?3 data|coloc|FPGA|sub.millisecond|tick.by.tick HFT|ultra.low.latency",
    r"RavenPack|sentiment score.*proprietary|closed.source signal",
    r"capital.*\$[1-9]\d{5,}",
]

def filter_item(item):
    title = item["title"].lower()
    body = item.get("description", "").lower()
    combined = title + " " + body
    source = item["source"]

    # L0
    for pat in L0_TITLE_PATTERNS:
        if re.search(pat, title, re.I):
            return "rejected_L0", []

    if item["points"] is not None and item["points"] < 5:
        return "rejected_L0", []

    if len(item.get("description", "").strip()) < 100 and source not in ("arxiv_econ_em", "quantpedia"):
        return "rejected_L0", []

    if source == "github_python":
        text = (item["title"] + " " + item.get("description", "")).lower()
        if not any(re.search(kw, text, re.I) for kw in QUANT_KEYWORDS):
            return "rejected_L0", []

    if source in ("hn_quant", "hn_algotrading"):
        if not any(re.search(pat, combined, re.I) for pat in HN_FINANCE_KEYWORDS):
            return "rejected_L0", []

    if source == "arxiv_econ_em":
        if not any(re.search(pat, combined, re.I) for pat in ARXIV_FINANCE_KEYWORDS):
            return "rejected_L0", []
        for offtopic in ARXIV_OFFTOPIC_PATTERNS:
            if re.search(offtopic, combined, re.I):
                return "rejected_L0", []

    # L1
    matched = []
    if source == "quantpedia":
        matched.append("academic_curated")
    elif source == "arxiv_econ_em":
        for label, pat in L1_PATTERNS.items():
            if re.search(pat, combined, re.I):
                matched.append(label)
        if not matched and re.search(r"forecast|predict|regime|volatility|trading|portfolio", combined, re.I):
            matched.append("topic_relevance")
    elif source in ("quantocracy", "quantinsti"):
        if re.search(L1_TRADING_TOPIC, combined, re.I):
            matched.append("trading_topic")
        for label, pat in L1_PATTERNS.items():
            if re.search(pat, combined, re.I) and label not in matched:
                matched.append(label)
    else:
        for label, pat in L1_PATTERNS.items():
            if re.search(pat, combined, re.I):
                matched.append(label)

    if not matched:
        return "rejected_L1_no_signal", []

    # L2
    for pat in L2_REJECT_PATTERNS:
        if re.search(pat, combined, re.I):
            return "rejected_L2_not_accessible", matched

    return "accepted", matched

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    seen = load_seen()
    items_seen = seen.get("items_seen", {})

    # Purge entries > 30 days
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    to_delete = []
    for h, v in items_seen.items():
        try:
            first = datetime.strptime(v.get("first_seen", "2000-01-01 00:00"), "%Y-%m-%d %H:%M")
            if (cutoff - first).days > 30:
                to_delete.append(h)
        except Exception:
            pass
    for h in to_delete:
        del items_seen[h]

    # Collect items by source
    all_items = []
    source_stats = {}

    def add(items, label):
        source_stats[label] = {"total": len(items), "new": 0,
                                "accepted": 0, "rej_l0": 0, "rej_l1": 0, "rej_l2": 0}
        all_items.extend(items)

    parsers = [
        ("hn_quant_*.json", parse_hn_json, "hn_quant", "hn_quant"),
        ("hn_algotrading_*.json", parse_hn_json, "hn_algotrading", "hn_algotrading"),
        ("quantocracy_*.xml", parse_quantocracy_digests, None, "quantocracy"),
        ("quantinsti_*.xml", parse_rss_xml, "quantinsti", "quantinsti"),
        ("quantpedia_*.xml", parse_rss_xml, "quantpedia", "quantpedia"),
        ("github_trending_python_*.html", parse_github_trending, None, "github_python"),
        ("arxiv_econ_em_*.xml", parse_arxiv, None, "arxiv_econ_em"),
    ]
    for pattern, fn, src_arg, label in parsers:
        files = sorted(glob.glob(os.path.join(RAW_DIR, pattern)))
        if not files:
            print(f"no files for {label}", file=sys.stderr)
            continue
        if src_arg is None:
            items = fn(files)
        else:
            items = fn(files, src_arg)
        add(items, label)

    # Filter + write staging
    accepted_count = 0
    for item in all_items:
        source = item["source"]
        h = md5(source + item["canonical_id"] + item["title"])
        stat = source_stats.get(source)
        if stat is None:
            continue

        if h in items_seen:
            continue

        stat["new"] += 1
        decision, l1_matches = filter_item(item)

        if decision == "accepted":
            stat["accepted"] += 1
            # Write staging JSON for LLM consumption
            staging = {
                "hash": h,
                "source": source,
                "canonical_id": item["canonical_id"],
                "title": item["title"],
                "url": item["url"],
                "description": item.get("description", ""),
                "points": item.get("points"),
                "created_at": item.get("created_at"),
                "l1_matches": l1_matches,
                "captured": NOW,
            }
            staging_path = os.path.join(STAGING_DIR, f"{h}.json")
            with open(staging_path, "w") as f:
                json.dump(staging, f, indent=2, ensure_ascii=False)
            accepted_count += 1
        elif decision == "rejected_L0":
            stat["rej_l0"] += 1
        elif decision == "rejected_L1_no_signal":
            stat["rej_l1"] += 1
        elif decision == "rejected_L2_not_accessible":
            stat["rej_l2"] += 1

        items_seen[h] = {
            "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "source": source,
            "title": item["title"][:80],
            "decision": decision,
            "promising_file": None,  # to be filled by LLM after md generation
        }

    # Save _seen.json
    seen["last_run"] = NOW
    seen["items_seen"] = items_seen
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

    # Save stats
    stats_summary = {
        "run_time": NOW,
        "accepted_count": accepted_count,
        "by_source": source_stats,
    }
    with open(os.path.join(STAGING_DIR, "_stats.json"), "w") as f:
        json.dump(stats_summary, f, indent=2)

    print(f"=== Alpha hunt filter {NOW} ===")
    print(f"Total accepted (staged): {accepted_count}")
    for src, s in source_stats.items():
        print(f"  {src}: total={s['total']} new={s['new']} "
              f"accepted={s['accepted']} rej_L0={s['rej_l0']} "
              f"rej_L1={s['rej_l1']} rej_L2={s['rej_l2']}")

if __name__ == "__main__":
    main()
