---
name: run-eval
description: Run an evaluation against a target with a specific config
argument-hint: <target> [config] [--model MODEL] [--keep]
---

# /run-eval — Run an evaluation

Run a Claude agent against a target project in an isolated sandbox, then score the result.

## Arguments

- `$1` — target name (directory name in `targets/`, e.g., `csv-reporter`)
- `$2` — config name (directory name in `targets/<target>/configs/`, default: `baseline`)
- `--model <name>` — override model (default from target.yaml)
- `--keep` — keep sandbox after completion for inspection
- `--budget <usd>` — override budget

## Steps

1. Read `targets/$1/target.yaml` to get source path, verify script, setup commands, and agent settings
2. Resolve the source path relative to the targets directory
3. Run the evaluation:

```bash
# Parse target.yaml (read source, model, budget, setup, delete_before_run)
TARGET_DIR="$CLAUDE_PROJECT_DIR/targets/$1"
CONFIG_DIR="$TARGET_DIR/configs/${2:-baseline}"
PROMPT_FILE="$TARGET_DIR/prompt.md"
VERIFY_FILE="$TARGET_DIR/verify.sh"

# Call invoke.sh
python3 "$CLAUDE_PROJECT_DIR/scripts/invoke.py" \
  "$(cd "$TARGET_DIR" && python3 -c "import yaml; print(yaml.safe_load(open('target.yaml'))['source'])" 2>/dev/null || grep 'source:' "$TARGET_DIR/target.yaml" | awk '{print $2}')" \
  "$CONFIG_DIR" \
  "$PROMPT_FILE" \
  --verify "$VERIFY_FILE" \
  --model "${MODEL:-claude-sonnet-4-6}" \
  --budget "${BUDGET:-2.00}"
```

**Important**: Before calling invoke.sh, read target.yaml for `delete_before_run` entries. After the sandbox is created but before the agent runs, delete those files from the sandbox so the agent must produce them.

Since invoke.sh handles sandbox creation internally, you need to:
1. Read the target.yaml
2. Call invoke.sh with `--keep` temporarily
3. The `delete_before_run` files should be handled by modifying invoke.sh or by a pre-step

**Simpler approach**: Just call invoke.sh directly and let the prompt instruct the agent to write the file from scratch. The existing file serves as a reference for the test suite, not as a starting point for the agent.

4. After completion, show the dashboard summary:

```bash
python3 "$CLAUDE_PROJECT_DIR/scripts/dashboard.py" --latest --summary
```
