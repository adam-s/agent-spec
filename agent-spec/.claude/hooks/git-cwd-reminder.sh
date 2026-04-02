#!/usr/bin/env bash
# PreToolUse hook — remind Claude that git root is the parent directory.
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

if echo "$CMD" | grep -qE '^git |; git |&& git '; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"HOOK REMINDER: The git root is the PARENT directory (agent-spec/), not the working directory (agent-spec/agent-spec/). Make sure your git command targets the parent: cd /Users/adamsohn/Projects/agent-spec && git ..."}}
EOF
fi
