#!/usr/bin/env bash
# PostToolUse hook — remind Claude to show monitoring commands after launching agents.
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

if echo "$CMD" | grep -qE 'invoke\.py|parallel\.py|run_eval\.py|/run-eval|/iterate'; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"HOOK REMINDER: You just launched an agent run. Tell the user the monitoring command: tail -f /tmp/agent-spec-parallel-out-*.log or python3 scripts/dashboard.py --latest"}}
EOF
fi
