#!/usr/bin/env bash
# Background launcher for Dukascopy P2 pull (excludes symbols already in MT5 panel).
# Output: Forex/data/cache/dukascopy_m5/<SYM>_<YEAR>_M5.parquet
# Log:    _downloads_logs/dukascopy_p2.log
set -uo pipefail

PROJ="<HOME>/Desktop/Algo_claude"
PY="/usr/bin/python3"
SCRIPT="$PROJ/Forex/data/dukascopy_downloader_m5.py"
LOG="$PROJ/_downloads_logs/dukascopy_p2.log"

# Skip what's already exported from MT5 (in data/panels/m5_indices/)
SKIP=( EURUSD GBPUSD US500 US100 US30 US2000 GER40 XAUUSD )

# Full FTMO-relevant universe (subset of SYMBOLS in dukascopy_downloader_m5.py)
SYMBOLS=(
  # FX additions
  USDJPY USDCHF AUDUSD USDCAD NZDUSD
  EURJPY GBPJPY EURGBP EURCHF AUDJPY CADJPY
  # Metals
  XAGUSD XPTUSD XPDUSD
  # Energies (codes best-guess: LIGHTCMDUSD/BRENTCMDUSD/GASCMDUSD)
  USOIL UKOIL NGAS
  # Indices ex-US/GER (codes best-guess; check log if 0 rows)
  UK100 FRA40 JP225 AUS200 EU50 HK50
  # Crypto via Dukascopy (cross-source vs Binance)
  BTCUSD ETHUSD LTCUSD BCHUSD XRPUSD
)

skip() {
  local s="$1"
  for sk in "${SKIP[@]}"; do [[ "$sk" == "$s" ]] && return 0; done
  return 1
}

echo "===== Dukascopy P2 pull started $(date -u +%FT%TZ) =====" >> "$LOG"
for sym in "${SYMBOLS[@]}"; do
  if skip "$sym"; then
    echo "[$(date -u +%H:%M:%S)] SKIP $sym (already in MT5 panel)" >> "$LOG"
    continue
  fi
  echo "[$(date -u +%H:%M:%S)] START $sym" >> "$LOG"
  cd "$PROJ" && "$PY" "$SCRIPT" --symbol "$sym" --year 0 --threads 4 >> "$LOG" 2>&1
  echo "[$(date -u +%H:%M:%S)] DONE  $sym (exit $?)" >> "$LOG"
done
echo "===== Dukascopy P2 pull finished $(date -u +%FT%TZ) =====" >> "$LOG"
