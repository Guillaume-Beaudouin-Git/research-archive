#!/bin/bash
# Fetch arxiv q-fin papers daily, commit to repo for downstream Claude routine.
# Designed to run on Hetzner VPS via cron, weekdays.

set -euo pipefail

REPO_DIR="$HOME/projects/Algo_claude"
LOG_FILE="$REPO_DIR/logs/arxiv_fetch.log"
DATE=$(date -u +%F)
RAW_DIR="$REPO_DIR/_automation/arxiv/_raw"
OUT_FILE="$RAW_DIR/${DATE}.xml"

mkdir -p "$RAW_DIR" "$(dirname "$LOG_FILE")"

log() {
  echo "[$(date -u +'%F %T UTC')] $*" >> "$LOG_FILE"
}

log "=== Fetch start for $DATE ==="

# Serialize repo git operations across fetch crons. 2026-06-09 postmortem: arxiv
# (30 6) and alpha_hunt (*/30) both pulled at 06:30:01 → polluted FETCH_HEAD →
# 'fatal: Cannot rebase onto multiple branches', chain dead since. Shared lock
# with fetch_alpha_sources.sh.
exec 9>"$HOME/.algo_git.lock"
if ! flock -w 180 9; then
  log "ERROR: git lock timeout (another fetch cron holds it)"
  exit 1
fi

cd "$REPO_DIR"

if ! git pull --rebase --autostash origin main >> "$LOG_FILE" 2>&1; then
  log "ERROR: git pull failed, aborting"
  exit 1
fi

URL="https://export.arxiv.org/api/query?search_query=cat:q-fin.ST+OR+cat:q-fin.PM+OR+cat:q-fin.TR+OR+cat:q-fin.RM+OR+cat:q-fin.MF+OR+cat:q-fin.CP&sortBy=submittedDate&sortOrder=descending&max_results=100"

if ! curl -fsSL --max-time 60 "$URL" > "$OUT_FILE"; then
  log "ERROR: arxiv fetch failed"
  rm -f "$OUT_FILE"
  exit 1
fi

SIZE=$(stat -c%s "$OUT_FILE")
ENTRIES=$(grep -c "<entry>" "$OUT_FILE" || true)
if [ "$SIZE" -lt 1000 ] || [ "$ENTRIES" -lt 1 ]; then
  log "ERROR: arxiv response invalid (size=$SIZE, entries=$ENTRIES)"
  rm -f "$OUT_FILE"
  exit 1
fi

log "Fetched OK: $SIZE bytes, $ENTRIES entries"

# Distill: XML → _staging/<date>.json (new entries only — cloud routine owns _seen)
python3 "$REPO_DIR/_automation/arxiv/process_arxiv_raw.py" >> "$LOG_FILE" 2>&1 \
  || log "WARN process_arxiv_raw.py failed"

# Raw XMLs stay VPS-local (gitignored since 2026-06-10), purge old ones
find "$RAW_DIR" -name '*.xml' -mtime +7 -delete 2>/dev/null || true

git add _automation/arxiv/_staging
if git diff --cached --quiet; then
  log "No new distilled entries, nothing to commit"
  exit 0
fi

git -c user.email="vps@algo-claude" -c user.name="VPS arxiv fetcher" \
  commit -m "data: arxiv distilled fetch ${DATE}" >> "$LOG_FILE" 2>&1

if git push origin main >> "$LOG_FILE" 2>&1; then
  log "Pushed to GitHub successfully"
else
  log "ERROR: git push failed"
  exit 1
fi

log "=== Fetch end OK ==="
