#!/bin/bash
# Fetch multi-source alpha hunting raw data.
# Runs every 30 min on VPS cron. Each source isolated (one fails, others continue).
# Output: _automation/alpha_hunt/_raw/<source>_<timestamp>.<ext>

set -uo pipefail  # NOT -e: we want partial failures to be non-fatal

REPO_DIR="$HOME/projects/Algo_claude"
LOG_FILE="$REPO_DIR/logs/alpha_hunt_fetch.log"
RAW_DIR="$REPO_DIR/_automation/alpha_hunt/_raw"
TS=$(date -u +"%Y%m%dT%H%M%SZ")
DATE=$(date -u +%F)

mkdir -p "$RAW_DIR" "$(dirname "$LOG_FILE")"

log() { echo "[$(date -u +'%F %T UTC')] $*" >> "$LOG_FILE"; }

log "=== Alpha hunt fetch start (TS=$TS) ==="

# Fetch wrapper: tries each source, logs result, never fails the whole script
fetch_source() {
  local name="$1"
  local url="$2"
  local outfile="$3"
  local user_agent="${4:-AlgoClaudeBot/0.1}"

  if curl -fsSL --max-time 30 -A "$user_agent" "$url" > "$outfile.tmp" 2>>"$LOG_FILE"; then
    local size=$(stat -c%s "$outfile.tmp" 2>/dev/null || echo 0)
    if [ "$size" -gt 200 ]; then
      mv "$outfile.tmp" "$outfile"
      log "OK $name ($size bytes) -> $outfile"
      return 0
    else
      log "WARN $name: response too small ($size bytes), skipping"
      rm -f "$outfile.tmp"
      return 1
    fi
  else
    log "FAIL $name: curl failed"
    rm -f "$outfile.tmp"
    return 1
  fi
}

cd "$REPO_DIR" || { log "FATAL cd failed"; exit 1; }
# Load secrets from .env (FRED_API_KEY, etc.)
if [ -f "$REPO_DIR/.env" ]; then
  set -a
  source "$REPO_DIR/.env"
  set +a
  log "Loaded .env"
else
  log "WARN .env not found, some sources may fail"
fi

# Pull latest (other commits may have happened)
git pull --rebase --autostash origin main >> "$LOG_FILE" 2>&1 || log "WARN git pull failed"

# === REDDIT ===
# Reddit blocks default UA. Custom UA required.
REDDIT_UA="AlgoClaudeBot/0.1 (research aggregator; +https://github.com/Guillaume-Beaudouin-Git/Algo_claude)"

fetch_source "reddit_algotrading" \
  "https://www.reddit.com/r/algotrading/new.json?limit=100" \
  "$RAW_DIR/reddit_algotrading_${TS}.json" \
  "$REDDIT_UA"

sleep 2  # politeness

fetch_source "reddit_quant" \
  "https://www.reddit.com/r/quant/new.json?limit=50" \
  "$RAW_DIR/reddit_quant_${TS}.json" \
  "$REDDIT_UA"

sleep 2

fetch_source "reddit_quantfinance" \
  "https://www.reddit.com/r/quantfinance/new.json?limit=50" \
  "$RAW_DIR/reddit_quantfinance_${TS}.json" \
  "$REDDIT_UA"

sleep 2

# === HN (Algolia API) ===

fetch_source "hn_quant" \
  "https://hn.algolia.com/api/v1/search_by_date?tags=story&query=quant+trading&hitsPerPage=50" \
  "$RAW_DIR/hn_quant_${TS}.json"

fetch_source "hn_algotrading" \
  "https://hn.algolia.com/api/v1/search_by_date?tags=story&query=algorithmic+trading&hitsPerPage=50" \
  "$RAW_DIR/hn_algotrading_${TS}.json"

# === QUANTOCRACY (RSS feed — publishes weekly digest posts with link lists) ===
fetch_source "quantocracy" \
  "https://quantocracy.com/feed/" \
  "$RAW_DIR/quantocracy_${TS}.xml"

# === QUANTINSTI BLOG (retail quant tutorials, strategy walkthroughs) ===
fetch_source "quantinsti" \
  "https://blog.quantinsti.com/rss/" \
  "$RAW_DIR/quantinsti_${TS}.xml"

# === QUANTPEDIA ===
fetch_source "quantpedia" \
  "https://quantpedia.com/feed/" \
  "$RAW_DIR/quantpedia_${TS}.xml"

# === GITHUB TRENDING PYTHON ===
fetch_source "github_trending_python" \
  "https://github.com/trending/python?since=daily" \
  "$RAW_DIR/github_trending_python_${TS}.html"

# === ARXIV econ.EM (extension de q-fin déjà couvert) ===
fetch_source "arxiv_econ_em" \
  "https://export.arxiv.org/api/query?search_query=cat:econ.EM&sortBy=submittedDate&sortOrder=descending&max_results=50" \
  "$RAW_DIR/arxiv_econ_em_${TS}.xml"

# === Cleanup old raw files (keep 7 days, alpha-hunt-collector reads recent only) ===
find "$RAW_DIR" -type f -mtime +7 -delete 2>/dev/null
log "Cleaned files older than 7 days"

# === Commit + push if anything new ===
git add "$RAW_DIR"
if git diff --cached --quiet; then
  log "No new raw files, nothing to commit"
else
  N_FILES=$(git diff --cached --name-only | wc -l)
  git -c user.email="vps@algo-claude" -c user.name="VPS alpha hunter" \
    commit -m "data: alpha hunt raw fetch ${TS} (${N_FILES} files)" >> "$LOG_FILE" 2>&1
  
  if git push origin main >> "$LOG_FILE" 2>&1; then
    log "Pushed $N_FILES files"
  else
    log "WARN git push failed (will retry next run)"
  fi
fi

log "=== Alpha hunt fetch end ==="
