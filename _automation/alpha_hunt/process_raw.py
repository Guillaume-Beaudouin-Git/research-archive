"""
Alpha Hunt – raw filter pipeline.
Parses all _raw/* files, applies L0/L1/L2 filters, writes promising .md files,
updates _seen.json.
"""

import json, glob, hashlib, re, os, sys
from datetime import datetime, timezone
from html import unescape
import xml.etree.ElementTree as ET

RAW_DIR   = os.path.join(os.path.dirname(__file__), "_raw")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "_seen.json")
PROM_DIR  = os.path.join(os.path.dirname(__file__), "promising")
RUNS_DIR  = os.path.join(os.path.dirname(__file__), "runs")
NOW       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
NOW_SLUG  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

os.makedirs(PROM_DIR, exist_ok=True)
os.makedirs(RUNS_DIR, exist_ok=True)

# ── helpers ───────────────────────────────────────────────────────────────────

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

def slug(s: str, maxlen: int = 50) -> str:
    s = unescape(s).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s[:maxlen]

def clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    return re.sub(r"\s+", " ", s).strip()

# ── load _seen.json ────────────────────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            d = json.load(f)
        if "items_seen" not in d:
            d["items_seen"] = {}
        return d
    return {"last_run": None, "items_seen": {}}

# ── source parsers ─────────────────────────────────────────────────────────────

def parse_hn_json(files, source_tag):
    """Collect unique HN hits across all timestamps."""
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
                        "url": hit.get("url", ""),
                        "description": clean_html(hit.get("story_text") or ""),
                        "points": hit.get("points", 0),
                        "created_at": hit.get("created_at", ""),
                    }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(items.values())


def parse_rss_xml(files, source_tag):
    """Generic RSS parser for quantpedia, quantinsti, quantconnect."""
    items = {}
    for fpath in sorted(files):
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                continue
            for item in channel.findall("item"):
                link = item.findtext("link", "").strip()
                title = item.findtext("title", "").strip()
                desc = clean_html(item.findtext("description", "") or "")
                if link and link not in items:
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
    """Extract individual articles from Quantocracy digest content fields."""
    articles = {}
    for fpath in sorted(files):
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                continue
            digest_items = channel.findall("item")
            for digest in digest_items:
                content = digest.findtext(
                    "{http://purl.org/rss/1.0/modules/content/}encoded", ""
                )
                title_matches = re.findall(
                    r'<a class="qo-title" href="([^"]+)"[^>]*>([^<]+)</a>', content
                )
                desc_matches = re.findall(
                    r'<div class="qo-description">(.*?)</div>', content, re.DOTALL
                )
                for i, (url, title) in enumerate(title_matches):
                    title = unescape(title.strip())
                    desc_raw = desc_matches[i] if i < len(desc_matches) else ""
                    desc = clean_html(desc_raw)
                    key = title.lower().strip()
                    if key not in articles:
                        articles[key] = {
                            "source": "quantocracy",
                            "canonical_id": key,
                            "title": title,
                            "url": unescape(url),
                            "description": desc,
                            "points": None,
                        }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(articles.values())


def parse_github_trending(files):
    """Extract repos from GitHub trending HTML."""
    repos = {}
    for fpath in sorted(files):
        try:
            with open(fpath) as f:
                html = f.read()
            articles = re.findall(
                r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>',
                html,
                re.DOTALL,
            )
            for art in articles:
                # owner/repo from h2 > a
                href_m = re.search(
                    r'<h2[^>]*lh-condensed[^>]*>.*?href="/([^"]+)"[^>]*>.*?</h2>',
                    art,
                    re.DOTALL,
                )
                if not href_m:
                    continue
                href = href_m.group(1).strip()
                # description
                desc_m = re.search(
                    r'<p[^>]*col-9[^>]*>\s*(.*?)\s*</p>', art, re.DOTALL
                )
                desc = clean_html(desc_m.group(1)) if desc_m else ""
                repo_name = href.split("/")[-1] if "/" in href else href
                if href not in repos:
                    repos[href] = {
                        "source": "github_python",
                        "canonical_id": href,
                        "title": href,
                        "url": f"https://github.com/{href}",
                        "description": desc,
                        "points": None,
                    }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(repos.values())


def parse_arxiv(files):
    """Parse Atom arxiv feeds."""
    entries = {}
    for fpath in sorted(files):
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            for e in root.findall("{http://www.w3.org/2005/Atom}entry"):
                eid = e.findtext("{http://www.w3.org/2005/Atom}id", "").strip()
                title = (
                    e.findtext("{http://www.w3.org/2005/Atom}title", "")
                    .strip()
                    .replace("\n", " ")
                )
                summary = (
                    e.findtext("{http://www.w3.org/2005/Atom}summary", "")
                    .strip()
                    .replace("\n", " ")
                )
                if eid and eid not in entries:
                    entries[eid] = {
                        "source": "arxiv_econ_em",
                        "canonical_id": eid,
                        "title": title,
                        "url": eid,
                        "description": summary,
                        "points": None,
                    }
        except Exception as e:
            print(f"WARN parse {fpath}: {e}", file=sys.stderr)
    return list(entries.values())


# ── filter logic ──────────────────────────────────────────────────────────────

L0_TITLE_PATTERNS = [
    r"what indicator should",
    r"is my system overfitted",
    r"how to start algo trading",
    r"best broker",
    r"review my strategy",
    r"made \w+ in a month",
    r"\bcourse\b(?! correction)",  # "course" but not "course correction"
    r"signal seller",
    r"join my discord",
    r"telegram group",
    r"\bVIP\b",
    r"premium subscription",
    r"quantinsti in \d{4}",      # newsletter annual summaries
    r"quantpedia in \w+ \d{4}",  # monthly summary posts
    r"quantpedia premium update",
]

# Finance/trading topic check required for HN items (prevents off-topic pass-through)
HN_FINANCE_KEYWORDS = [
    r"sharpe", r"backtest", r"\balpha\b", r"systematic(ally)?",
    r"quantitative trad", r"\bquant\b", r"portfolio.*strateg",
    r"algo(rithmic)? trad", r"momentum.*strat", r"factor.*model",
    r"volatility.*model", r"risk.return", r"asset.alloc",
    r"market regime", r"time.series.*forecast", r"financial.machine.learning",
    r"vectorbt|zipline|nautilus.*trader|quantconnect|lean\b",
    r"mean reversion.*trad", r"stat.*arb", r"pairs.trad",
    r"crypto.*strateg", r"futures.*strateg", r"signal.*trad",
    r"walk.forward", r"walk-forward", r"out.of.sample",
    r"maxdd|max.?drawdown", r"profit.factor", r"sortino",
    r"nautilus.*trad", r"NautilusTrader",
    r"execution.*cost", r"slippage", r"transaction.*cost",
    r"kelly.*criterion", r"CAPM|Fama.French",
]

# Arxiv relevance: paper must touch forecasting/trading/finance topics
ARXIV_FINANCE_KEYWORDS = [
    r"forecast", r"predict.*return", r"portfolio.*optim", r"\btrading\b",
    r"volatility.*model", r"momentum", r"factor.*model", r"asset.*pric",
    r"market.regime", r"risk.premium", r"equity.premium", r"yield.curve",
    r"macroeconomic.*forecast", r"financial.*machine.learning",
    r"price.*predict", r"stock.*return", r"bond.*return",
    r"regime.switch", r"time.series.*forecast", r"nowcast",
    r"predictive.abilit", r"conformal.*predict",
    r"heavy.tail.*predict", r"benign.overfit.*forecast",
]

# Arxiv negative: clearly off-topic despite matching a finance keyword
ARXIV_OFFTOPIC_PATTERNS = [
    r"movie|film.industr|box.office",
    r"nightlight|nighttime.light|satellite.*light",
    r"quantum.game.circuit|EWL.quantum|qubit.*hamiltonian",
    r"hepatitis|hiv|hcv|medical|clinical.trial",
    r"divorce|forensic.account",
    r"middle.income.trap|engineering.economy.*paradigm",
    r"procurement.*heterogeneit",
    r"municipal.*income.*nightlight",
    r"energy.*infrastructure.*datacenter|hyperscale.ai.datacenter",
]

# L1 for curated quant sources (Quantocracy, QuantInsti): trading topic suffices
L1_TRADING_TOPIC = (
    r"trend.follow|trend.*trad|momentum.strat|momentum.invest|volatility.model|EGARCH|GARCH\b"
    r"|regime.detect|carry.trad|intraday.*trad|intraday.*strateg|backtest|walk.forward|walk-forward"
    r"|out.of.sample|out-of-sample|sharpe|drawdown|factor.model|mean.reversion"
    r"|arbitrage|tactical.asset|equity.curve|risk.parity|dual.momentum|GTAA"
    r"|market.breadth|hidden.markov|Markov.switching|donchian|breakout.strat"
    r"|conformal.predict|prediction.market|overfitt.*strat|stress.test.*signal"
    r"|skips?.month|skip.month|momentum.*skip|cointegrat.*strat|pairs.trad"
    r"|LLM.*regime|regime.*LLM|volatility.risk.premium|intraday.vol|vol.*cluster"
    r"|curve.trade|macroeconomic.signal|yield.curve.*trad"
    r"|implementation.*detail.*performance|systematic.*multiasset"
)

QUANT_KEYWORDS = [
    "trading", "quant", "finance", "forecast", "time.series",
    "portfolio", "backtest", "strategy", "alpha", "momentum",
    "arbitrage", "signal", "volatility", "sharpe", "factor",
    "regime", "risk", "return", "asset", "equity", "futures",
    "crypto", "currency", "yield", "market", "invest",
]

L1_PATTERNS = {
    "metrics": r"sharpe|maxdd|max.?drawdown|profit.factor|win.rate|calmar|sortino|cagr|drawdown",
    "code_quant": r"vectorbt|zipline|qlib|nautilus.?trader|backtrader|quantconnect|lean\b.*trad|python.*backtest|backtest.*python",
    "methodology": r"lopez.de.prado|bailey|politis.romano|newey.west|HAC|AMTP|deflated.sharpe|walk.forward|walk-forward|block.bootstrap|DSR|fama.french|markowitz|adf.test|cointegrat|regime.detect|Markov.switching|expanding.window|out.of.sample|out-of-sample|EGARCH|GARCH|cross.sectional|information.coefficient|deflated.sharpe|multiple.testing|overfitt.*strateg|stress.test.*trading",
    "macro_trading": r"FOMC|yield.curve|funding.rate|basis.spread|carry.trade|term.spread|credit.spread|VIX.*strateg|macroeconomic.*signal",
    "quant_tool": r"nautilustrader|vectorbt|zipline|qlib|lean.*trad|backtrader|quantconnect",
}

L2_REJECT_PATTERNS = [
    r"refinitiv|factset|bloomberg terminal|quandl premium|ICE data",
    r"prime broker|dark pool|market maker relationship",
    r"level.?2 data|level.?3 data|coloc|FPGA|sub.millisecond|tick.by.tick HFT|ultra.low.latency",
    r"RavenPack|sentiment score.*proprietary|closed.source signal",
    r"capital.*\$[1-9]\d{5,}",  # explicit capital > $100k requirement
]

def filter_item(item):
    """
    Returns (decision, l1_matches).
    decision: 'accepted' | 'rejected_L0' | 'rejected_L1_no_signal' | 'rejected_L2_not_accessible'
    """
    title = item["title"].lower()
    body  = item.get("description", "").lower()
    combined = title + " " + body
    source = item["source"]

    # ── L0 checks ─────────────────────────────────────────────────────────────
    for pat in L0_TITLE_PATTERNS:
        if re.search(pat, title, re.I):
            return "rejected_L0", []

    if item["points"] is not None and item["points"] < 5:
        return "rejected_L0", []

    if len(item.get("description", "").strip()) < 100 and source not in ("arxiv_econ_em", "quantpedia"):
        return "rejected_L0", []

    # GitHub: must mention quant/finance keywords
    if source == "github_python":
        repo_name = item["title"].lower()
        full_text = repo_name + " " + item.get("description", "").lower()
        if not any(re.search(kw, full_text, re.I) for kw in QUANT_KEYWORDS):
            return "rejected_L0", []

    # HN: must contain finance/trading keywords (prevents off-topic pass-through)
    if source in ("hn_quant", "hn_algotrading"):
        if not any(re.search(pat, combined, re.I) for pat in HN_FINANCE_KEYWORDS):
            return "rejected_L0", []

    # arxiv: must touch forecasting/trading topics (not pure econometrics)
    if source == "arxiv_econ_em":
        if not any(re.search(pat, combined, re.I) for pat in ARXIV_FINANCE_KEYWORDS):
            return "rejected_L0", []
        # Also reject clearly off-topic papers that matched via broad keywords
        for offtopic in ARXIV_OFFTOPIC_PATTERNS:
            if re.search(offtopic, combined, re.I):
                return "rejected_L0", []

    # ── L1 checks ─────────────────────────────────────────────────────────────
    matched = []

    # quantpedia: presumption of L1 relevance (curated quant research)
    if source == "quantpedia":
        matched.append("academic_presumption")
    elif source == "arxiv_econ_em":
        # arxiv: must show explicit quant/forecasting signal in title+summary
        for label, pat in L1_PATTERNS.items():
            if re.search(pat, combined, re.I):
                matched.append(label)
        if not matched:
            if re.search(r"forecast|predict|regime|volatility|trading|portfolio", combined, re.I):
                matched.append("topic_relevance")
    elif source in ("quantocracy", "quantinsti"):
        # Curated quant sources: trading topic in title/desc suffices for L1
        if re.search(L1_TRADING_TOPIC, combined, re.I):
            matched.append("trading_topic")
        else:
            for label, pat in L1_PATTERNS.items():
                if re.search(pat, combined, re.I):
                    matched.append(label)
    else:
        for label, pat in L1_PATTERNS.items():
            if re.search(pat, combined, re.I):
                matched.append(label)

    if not matched:
        return "rejected_L1_no_signal", []

    # ── L2 checks ─────────────────────────────────────────────────────────────
    for pat in L2_REJECT_PATTERNS:
        if re.search(pat, combined, re.I):
            return "rejected_L2_not_accessible", matched

    return "accepted", matched


# ── action classification (heuristic, can be overridden) ──────────────────────

def classify_action(item, l1_matches):
    """
    Returns 'TEST_NOW' | 'TEST_LATER' | 'REFERENCE'
    """
    combined = (item["title"] + " " + item.get("description", "")).lower()

    # Strong signals for TEST_NOW: intraday + strategy C relevant
    if any(kw in combined for kw in [
        "intraday trend trade",
        "intraday trend",
    ]):
        return "TEST_NOW"

    # TEST_LATER: has code or clear method + fits active strategies
    test_later_signals = [
        r"donchian.*strateg", r"regime.detect", r"market.breadth.*regime",
        r"random.forest.*regime", r"markov.switching", r"hidden.markov.*model",
        r"regime.dependent.*alloc", r"skip.?month.*momentum", r"momentum.*skip.?month",
        r"momentum.*struggling.*volatility", r"volatility.*momentum.*struggling",
        r"volatility.risk.premium.*intraday", r"intraday.*vol.*cluster",
        r"rolling.origin.conformal", r"risk.return.*tradeoff.*forecast",
        r"dual.momentum", r"crypto.*public.equity", r"\bGTAA\b",
        r"llm.*regime.*label", r"regime.*llm.*label",
        r"conformal.*prediction.*time.series",
        r"risk.return.tradeoff.*forecast",
        r"markov.switching.*time.varying",
    ]
    for pat in test_later_signals:
        if re.search(pat, combined, re.I):
            return "TEST_LATER"

    if "code_quant" in l1_matches and any(
        re.search(kw, combined, re.I)
        for kw in [r"backtest", r"strateg", r"signal", r"regime", r"momentum"]
    ):
        return "TEST_LATER"

    return "REFERENCE"


# ── md generation ─────────────────────────────────────────────────────────────

STRATEGY_NOTES = {
    "intraday": "Strategy C (NQ opening momentum — intraday execution, entry at 09:46 ET)",
    "momentum": "Strategy A (TSMOM v3 — tanh-based crypto momentum signal)",
    "crypto": "Strategy A (TSMOM v3) / Strategy B (HL delta-neutral carry)",
    "carry": "Strategy B (HL delta-neutral carry, mainnet pending)",
    "regime": "Strategy C regime filtering (VWAP + gap filters)",
    "volatility": "vol targeting methodology (28-bar log returns)",
    "walk.forward": "CLAUDE.md walk-forward requirement (≥5 folds)",
    "overfitting": "CLAUDE.md methodology: max 3 modifications per hypothesis",
    "amtp": "CLAUDE.md AMTP (n_tests=134+, multiple-testing correction mandatory)",
    "markov": "Strategy C regime detection",
}

def build_md(item, l1_matches, action, hash_val):
    title = unescape(item["title"])
    source = item["source"]
    url = item["url"]
    desc = item.get("description", "")

    # paraphrase title for clarity if needed
    display_title = title

    # relevance bullet
    combined_lower = (title + " " + desc).lower()
    relevance_bullets = []
    for kw, note in STRATEGY_NOTES.items():
        if re.search(kw, combined_lower, re.I):
            bullet = f"- {note}"
            if bullet not in relevance_bullets:
                relevance_bullets.append(bullet)

    if not relevance_bullets:
        relevance_bullets = ["- General methodology / background research"]

    relevance_str = "\n".join(relevance_bullets[:3])

    # summary (2-3 sentences, not verbatim)
    # Use first 400 chars of description as base, rewrite
    desc_short = desc[:500].rstrip()

    # extracted content (keep claims as-is with attribution)
    # Find any numeric claims
    num_claims = re.findall(
        r"\d[\d.,]* ?%|\bSharpe\b[^.]{0,80}|\bMaxDD\b[^.]{0,80}|"
        r"\bCGAR\b[^.]{0,80}|\bCAGR\b[^.]{0,80}",
        desc[:1000],
        re.I,
    )
    extracted = ""
    if num_claims:
        extracted = "\n".join(f'- "{c.strip()}" — source claim' for c in num_claims[:5])
    else:
        extracted = "No explicit numeric claims in excerpt."

    l1_str = ", ".join(l1_matches)

    md = f"""# {display_title}

**Source**: {source}
**URL**: {url}
**Captured**: {NOW}
**Filters passed**: L1=[{l1_str}], L2_OK
**Hash**: {hash_val}

## Summary
{desc_short[:400]}

## Why it might be useful
{relevance_str}

## Extracted content
{extracted}

## Action proposed
{action}
"""
    return md


# ── main pipeline ─────────────────────────────────────────────────────────────

def main():
    seen = load_seen()
    items_seen = seen.get("items_seen", {})

    # Purge entries > 30 days
    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )
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

    # Collect all raw items
    all_items = []

    hn_quant_files     = sorted(glob.glob(os.path.join(RAW_DIR, "hn_quant_*.json")))
    hn_algo_files      = sorted(glob.glob(os.path.join(RAW_DIR, "hn_algotrading_*.json")))
    qo_files           = sorted(glob.glob(os.path.join(RAW_DIR, "quantocracy_*.xml")))
    qi_files           = sorted(glob.glob(os.path.join(RAW_DIR, "quantinsti_*.xml")))
    qp_files           = sorted(glob.glob(os.path.join(RAW_DIR, "quantpedia_*.xml")))
    qc_files           = sorted(glob.glob(os.path.join(RAW_DIR, "quantconnect_*.xml")))
    gh_files           = sorted(glob.glob(os.path.join(RAW_DIR, "github_trending_python_*.html")))
    arxiv_files        = sorted(glob.glob(os.path.join(RAW_DIR, "arxiv_econ_em_*.xml")))

    source_stats = {}

    def add_items(new_items, source_label):
        source_stats[source_label] = {"total": len(new_items), "new": 0,
                                       "accepted": 0, "rej_l0": 0, "rej_l1": 0, "rej_l2": 0}
        all_items.extend(new_items)

    if hn_quant_files:
        add_items(parse_hn_json(hn_quant_files, "hn_quant"), "hn_quant")
    else:
        print("no new items from hn_quant")

    if hn_algo_files:
        add_items(parse_hn_json(hn_algo_files, "hn_algotrading"), "hn_algotrading")
    else:
        print("no new items from hn_algotrading")

    if qo_files:
        add_items(parse_quantocracy_digests(qo_files), "quantocracy")
    else:
        print("no new items from quantocracy")

    if qi_files:
        add_items(parse_rss_xml(qi_files, "quantinsti"), "quantinsti")
    else:
        print("no new items from quantinsti")

    if qp_files:
        add_items(parse_rss_xml(qp_files, "quantpedia"), "quantpedia")
    else:
        print("no new items from quantpedia")

    if qc_files:
        add_items(parse_rss_xml(qc_files, "quantconnect"), "quantconnect")
    else:
        print("no new items from quantconnect")

    if gh_files:
        add_items(parse_github_trending(gh_files), "github_python")
    else:
        print("no new items from github_python")

    if arxiv_files:
        add_items(parse_arxiv(arxiv_files), "arxiv_econ_em")
    else:
        print("no new items from arxiv_econ_em")

    # Process items
    accepted_items = []

    for item in all_items:
        source = item["source"]
        h = md5(source + item["canonical_id"] + item["title"])

        # dedup
        if h in items_seen:
            continue

        decision, l1_matches = filter_item(item)

        stat_key = source
        if stat_key in source_stats:
            source_stats[stat_key]["new"] += 1
            if decision == "accepted":
                source_stats[stat_key]["accepted"] += 1
            elif decision == "rejected_L0":
                source_stats[stat_key]["rej_l0"] += 1
            elif decision == "rejected_L1_no_signal":
                source_stats[stat_key]["rej_l1"] += 1
            elif decision == "rejected_L2_not_accessible":
                source_stats[stat_key]["rej_l2"] += 1

        promising_file = None

        if decision == "accepted":
            action = classify_action(item, l1_matches)
            filename = f"{source}_{slug(item['title'])}_{NOW_SLUG[:8]}.md"
            filepath = os.path.join(PROM_DIR, filename)
            md_content = build_md(item, l1_matches, action, h)
            with open(filepath, "w") as f:
                f.write(md_content)
            promising_file = filename
            accepted_items.append({
                "title": item["title"],
                "source": source,
                "action": action,
                "file": filename,
                "hash": h,
                "l1": l1_matches,
            })

        items_seen[h] = {
            "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "source": source,
            "title": item["title"][:80],
            "decision": decision,
            "promising_file": promising_file,
        }

    # Update _seen.json
    seen["last_run"] = NOW
    seen["items_seen"] = items_seen
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

    # Print stats
    print(f"\n=== Alpha Hunt Run {NOW} ===")
    print(f"Accepted: {len(accepted_items)}")
    print()
    print("Stats by source:")
    for src, s in source_stats.items():
        print(f"  {src}: total={s['total']} new={s['new']} "
              f"accepted={s['accepted']} rej_L0={s['rej_l0']} "
              f"rej_L1={s['rej_l1']} rej_L2={s['rej_l2']}")
    print()

    # Sort accepted: TEST_NOW first, then TEST_LATER, then REFERENCE
    order = {"TEST_NOW": 0, "TEST_LATER": 1, "REFERENCE": 2}
    accepted_items.sort(key=lambda x: (order.get(x["action"], 3), x["source"]))

    print("Accepted items:")
    for a in accepted_items:
        print(f"  [{a['action']}] {a['source']} — {a['title'][:70]}")
        print(f"    file: {a['file']}")

    return accepted_items, source_stats


if __name__ == "__main__":
    main()
