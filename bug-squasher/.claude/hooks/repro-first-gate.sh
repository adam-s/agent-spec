#!/bin/bash
# PreToolUse hook: enforce reproduce-first debugging strategy.
# Blocks reading source files until a reproduction script exists.
# Returns additionalContext reminding the agent to reproduce first.

INPUT=$(cat)

# Check if a repro file already exists in the workspace
if ls "$CLAUDE_PROJECT_DIR"/repro.* "$CLAUDE_PROJECT_DIR"/repro_*.* 2>/dev/null | head -1 > /dev/null 2>&1; then
    exit 0
fi

TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)

# For Read/Grep/Glob: remind but don't block
# The agent might need to read non-source files (README, config, etc.)
if [ "$TOOL_NAME" = "Read" ] || [ "$TOOL_NAME" = "Grep" ] || [ "$TOOL_NAME" = "Glob" ]; then
    echo '{"additionalContext": "REMINDER: Write and run a reproduction script (repro.py) BEFORE reading source files. The reproduction output tells you where to look. See step 1 of the debugging strategy."}'
    exit 0
fi

# For Bash: check if it's find/ls/grep (exploration)
if [ "$TOOL_NAME" = "Bash" ]; then
    COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
    case "$COMMAND" in
        find*|ls*|grep*|rg*)
            echo '{"additionalContext": "REMINDER: Write and run a reproduction script (repro.py) BEFORE exploring the codebase. See step 1 of the debugging strategy."}'
            ;;
    esac
fi

exit 0
