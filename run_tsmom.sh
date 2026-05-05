#!/bin/bash
# run_tsmom.sh — TSMOM daily cron wrapper
# Runs all 3 assets (BTC-USD, ETH-USD, SOL-USD) in a single invocation.
#
# Crontab entry (00:05 UTC daily, after daily bar closes):
#   5 0 * * * /home/algo/run_tsmom.sh --live --private-key <KEY> >> /home/algo/logs/tsmom.log 2>&1
#
# Dry-run test:
#   /home/algo/run_tsmom.sh --dry-run
set -e
source ~/venv/bin/activate
cd ~/projects/Algo_claude
python tsmom_live.py "$@"
