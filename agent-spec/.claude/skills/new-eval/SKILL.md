---
name: new-eval
description: Scaffold a new evaluation
argument-hint: <name>
---

# /new-eval — Create a new evaluation

Scaffolds an eval directory with template files.

See @.claude/reference/eval-definition.md for the full EVAL.md schema and conventions.

## Steps

Create these files in `evals/$1/`:

**EVAL.md**:
```markdown
---
name: $1
description: Describe what this eval tests
source: ../../../path-to-source
model: claude-haiku-4-5-20251001
budget: 1.00
delete: []
setup: []
reference:
  type: test-file
  file: test.js
  pass_pattern: "tests passed"
---

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

**configs/baseline/settings.json**:
```json
{
  "permissions": {
    "deny": []
  }
}
```

Make verify.sh executable: `chmod +x evals/$1/verify.sh`

Print: "Eval '$1' created. Edit evals/$1/EVAL.md to set the source path and reference, then run /run-eval $1"
