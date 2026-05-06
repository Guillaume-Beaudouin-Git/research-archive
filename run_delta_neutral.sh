#!/bin/bash
# run_delta_neutral.sh — Delta-Neutral funding arb cron wrapper
# Runs all viable assets (TST, WLD, STX, BIO, TRUMP, HMSTR) in one invocation.
#
# Crontab entry (8-hourly, 10 min past settlement):
#   10 0,8,16 * * * /home/algo/run_delta_neutral.sh >> /home/algo/logs/delta_neutral.log 2>&1
#
# Note: midnight slot at 00:10 UTC staggers 5 min after TSMOM cron at 00:05 UTC.
#
# Dry-run test:
#   /home/algo/run_delta_neutral.sh --dry-run
#
# Live:
#   /home/algo/run_delta_neutral.sh --live \
#       --bn-key  $BINANCE_TESTNET_API_KEY \
#       --bn-secret $BINANCE_TESTNET_SECRET_KEY \
#       --hl-key  $HYPERLIQUID_TESTNET_KEY
set -e
source ~/venv/bin/activate
cd ~/projects/Algo_claude
python -m strategies.delta_neutral.live_trader "$@"
