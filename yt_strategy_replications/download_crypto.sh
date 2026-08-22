#!/bin/bash
# Resumable parallel downloader for Binance spot 5m klines from data.binance.vision.
# Skips existing zips and silently skips months that 404 (pair not yet listed).
set -u
ROOT="/sessions/elegant-intelligent-lovelace/mnt/Algo_claude/yt_strategy_replications"
ZIPDIR="$ROOT/data_cache/crypto_5m/_zips"
URLS="$ROOT/data_cache/crypto_5m/_urls.txt"
mkdir -p "$ZIPDIR"

PAIRS="BTCUSDT ETHUSDT BNBUSDT XRPUSDT ADAUSDT SOLUSDT DOGEUSDT LTCUSDT LINKUSDT UNIUSDT DOTUSDT AVAXUSDT TRXUSDT ATOMUSDT ETCUSDT BCHUSDT XLMUSDT FILUSDT"

> "$URLS"
for p in $PAIRS; do
  for y in 2021 2022 2023 2024 2025 2026; do
    for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
      if [ "$y" = "2026" ]; then
        case "$m" in 06|07|08|09|10|11|12) continue;; esac
      fi
      echo "https://data.binance.vision/data/spot/monthly/klines/${p}/5m/${p}-5m-${y}-${m}.zip" >> "$URLS"
    done
  done
done
echo "$(date +%H:%M:%S) total_urls=$(wc -l < "$URLS")"

cat "$URLS" | xargs -P 12 -I{} bash -c '
  f="$1"; out="'"$ZIPDIR"'/$(basename "$f")"
  if [ -s "$out" ]; then exit 0; fi
  code=$(curl -s -m 60 -w "%{http_code}" -o "$out" "$f")
  if [ "$code" != "200" ]; then rm -f "$out"; fi
' _ {}

echo "$(date +%H:%M:%S) DOWNLOAD_DONE zips=$(ls "$ZIPDIR" 2>/dev/null | wc -l)"
