#!/bin/bash
# run_with_env.sh — load project venv + .env, then exec the given command.
#
# Goal: keep all secrets in ~/projects/Algo_claude/.env, never in `crontab -l`
# or `ps aux`. Cron lines stay short and readable:
#   5 0 * * * /home/algo/projects/Algo_claude/scripts/run_with_env.sh \
#       /home/algo/run_tsmom.sh --live --private-key "$HYPERLIQUID_TESTNET_KEY"
#
# IMPORTANT: cron does not expand $VAR inside the command unless wrapped in a
# subshell that has sourced .env first. This script does exactly that, so the
# downstream command sees the env vars resolved.
#
# Usage: run_with_env.sh <command> [args...]
#   $@ is exec'd verbatim AFTER .env is sourced. Quote with care if args
#   contain $VAR references — let THIS shell expand them, not cron.
#
# Refs: _audit/security_cleanup_2026-05-30.md S1; _audit/lot7_crontab_diff_2026-05-30.txt

set -euo pipefail

PROJECT_DIR="${ALGO_CLAUDE_HOME:-$HOME/projects/Algo_claude}"
VENV_ACTIVATE="${ALGO_CLAUDE_VENV:-$HOME/venv/bin/activate}"

cd "$PROJECT_DIR"

# Source venv first (so PATH includes venv python before .env overrides).
# shellcheck disable=SC1090
[ -f "$VENV_ACTIVATE" ] && . "$VENV_ACTIVATE"

# Source .env if present. set -a exports all variables defined therein.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . .env
    set +a
fi

# Exec the requested command. exec replaces this shell so the child inherits
# the env vars and uses one fewer process.
exec "$@"
