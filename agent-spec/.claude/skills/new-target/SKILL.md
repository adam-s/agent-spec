---
name: new-target
description: Scaffold a new evaluation target
argument-hint: <name>
---

# /new-target — Create a new evaluation target

Scaffolds a target directory with template files.

See @.claude/reference/target-definition.md for the full target schema and conventions.

## Steps

Create these files in `targets/$1/`:

**target.yaml**:
```yaml
name: $1
source: ../../path-to-source-repo
verify: verify.sh
delete_before_run: []
setup: []
agent:
  model: claude-sonnet-4-6
  budget: 2.00
```

**prompt.md**:
```
Describe the task for the agent here.

Run the test command to verify your work passes all tests.
```

**verify.sh**:
```bash
#!/usr/bin/env bash
set -euo pipefail
OUTPUT=$(echo "replace with test command" 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "tests passed"; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
```

**configs/baseline/CLAUDE.md**:
```
A coding project.
```

Make verify.sh executable: `chmod +x targets/$1/verify.sh`

Print: "Target '$1' created. Edit targets/$1/target.yaml to set the source repo path, then run /run-eval $1"
