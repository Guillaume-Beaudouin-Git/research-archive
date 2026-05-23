#!/usr/bin/env bash
# Monitor VPS Dukascopy M5 download progress.
# Usage: bash check_download.sh

VPS="algo@<VPS_IP>"
KEY="$HOME/.ssh/hetzner_algo_claude"
REMOTE_DIR="~/projects/Algo_claude/Forex/data/cache/dukascopy_m5"
SESSION="duka_full"
EXPECTED=60  # 6 pairs × 10 years

echo "=== Dukascopy M5 Download Monitor ==="
printf "Checked: %s\n\n" "$(date)"

# tmux liveness
echo "[tmux] Session '$SESSION':"
ALIVE=$(ssh -i "$KEY" "$VPS" "tmux ls 2>/dev/null | grep '$SESSION' || echo 'DEAD'")
echo "  $ALIVE"

# parquet count + size
echo ""
echo "[cache] Progress:"
ssh -i "$KEY" "$VPS" "
  COUNT=\$(ls $REMOTE_DIR/*.parquet 2>/dev/null | wc -l | tr -d ' ')
  SIZE=\$(du -sh $REMOTE_DIR 2>/dev/null | cut -f1)
  echo \"  Parquets: \$COUNT / $EXPECTED\"
  echo \"  Total size: \$SIZE\"
  echo \"  Files:\"
  ls -lh $REMOTE_DIR/*.parquet 2>/dev/null | awk '{print \"    \" \$5 \"  \" \$9}' | sed 's|.*/||' || echo '    (none yet)'
"

# last tmux output
echo ""
echo "[log] Last 5 lines from '$SESSION':"
ssh -i "$KEY" "$VPS" "tmux capture-pane -t '$SESSION' -p 2>/dev/null | grep -v '^$' | tail -5 | sed 's/^/  /'" || echo "  (session not running)"
echo ""
