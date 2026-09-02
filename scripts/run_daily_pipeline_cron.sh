#!/bin/zsh
set -eu

export HOME="/Users/sungpyo"
export CODEX_HOME="/Users/sungpyo/.codex"
export PATH="/Users/sungpyo/.local/bin:/Users/sungpyo/blog/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "/Users/sungpyo/blog"
mkdir -p "/Users/sungpyo/blog/logs"
exec "/Users/sungpyo/blog/.venv/bin/python" \
  "/Users/sungpyo/blog/scripts/run_daily_pipeline.py" \
  --briefing-only
