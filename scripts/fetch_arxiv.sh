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

git add "$OUT_FILE"
if git diff --cached --quiet; then
  log "No changes to commit"
  exit 0
fi

git -c user.email="vps@algo-claude" -c user.name="VPS arxiv fetcher" \
  commit -m "data: arxiv q-fin raw fetch ${DATE} (${ENTRIES} entries)" >> "$LOG_FILE" 2>&1

if git push origin main >> "$LOG_FILE" 2>&1; then
  log "Pushed to GitHub successfully"
else
  log "ERROR: git push failed"
  exit 1
fi

log "=== Fetch end OK ==="
