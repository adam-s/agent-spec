#!/usr/bin/env bash
# PostToolUse hook — remind Claude to verify agent processes are running and producing output.
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

if echo "$CMD" | grep -qE 'invoke\.py|parallel\.py|run_eval\.py|/run-eval|/iterate'; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"HOOK REMINDER: You just launched an agent run. Verify it is producing output. Check: ps aux | grep 'claude.*-p' | grep -v grep. Check latest run: python3 scripts/dashboard.py --latest. Do NOT silently wait — confirm the process is alive and producing results."}}
EOF
fi
