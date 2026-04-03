---
name: new-eval
description: Scaffold a new evaluation
argument-hint: <name>
---

# /new-eval — Create a new evaluation

Scaffolds an eval directory with template files. Uses the multi-challenge format by default.

See @.claude/reference/eval-definition.md for the full schema, environment setup conventions, and verify.sh contract.

## Steps

Ask the user what language the eval targets (Python, TypeScript, or other) to select the right environment pattern.

Create these files in `evals/$1/`:

**EVAL.md**:

```markdown
---
name: $1
description: Describe what this eval tests
model: claude-sonnet-4-6
budget: 2.00
---
```

**challenges/challenge-1/prompt.md**: Describe the task. Include the environment hint for the language:
- Python: "A Python virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code."
- TypeScript: "Dependencies are pre-installed in `node_modules/`."

**challenges/challenge-1/seeds/**: Place seed files here (source code, test scripts, data files, and dependency manifests like requirements.txt or package.json).

**challenges/challenge-1/setup.sh** — create the environment and install deps:

Python:

```bash
#!/bin/bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt --quiet
```

TypeScript:

```bash
#!/bin/bash
npm install --silent
```

**challenges/challenge-1/verify.sh** — run tests and print RESULT. Only verify.sh prints `RESULT:`, not the test script.

Python:

```bash
#!/bin/bash
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -r requirements.txt --quiet 2>/dev/null

.venv/bin/python3 test.py 2>&1
EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
```

TypeScript:

```bash
#!/bin/bash
[ -d node_modules ] || npm install --silent 2>/dev/null

node test.js 2>&1
EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
```

**configs/baseline/CLAUDE.md**:

```markdown
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

Make scripts executable: `chmod +x evals/$1/challenges/challenge-1/verify.sh evals/$1/challenges/challenge-1/setup.sh`

Print: "Eval '$1' created. Edit the challenge prompt and seeds, then run /run-eval $1"
