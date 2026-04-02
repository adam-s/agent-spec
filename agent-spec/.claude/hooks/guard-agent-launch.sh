#!/usr/bin/env bash
# PreToolUse hook — remind Claude to confirm with user before launching agents.
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

if echo "$CMD" | grep -qE 'invoke\.py|parallel\.py|run_eval\.py|/run-eval|/iterate'; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"HOOK REMINDER: You are about to launch an agent process. Before proceeding, confirm with the user: state what you are launching (target, config, instance count) and wait for approval. Use run_in_background: true."}}
EOF
fi
