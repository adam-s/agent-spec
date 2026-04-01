There is a sample Python project at /tmp/agent-spec-sample-app with:
- app.py — a word counter CLI
- test.py — tests that print "N/N tests passed"
- sample.txt — test data

Your task: create a new agent-spec evaluation target for this project.

1. Create the target directory at targets/sample-app/ with:
   - target.yaml pointing to /tmp/agent-spec-sample-app as the source
   - prompt.md describing a task for an agent (delete app.py, have the agent recreate it)
   - verify.sh that runs test.py and checks for "4/4 tests passed"
   - configs/baseline/CLAUDE.md with minimal instructions

2. Make verify.sh executable.

3. Verify your work by running: python3 scripts/cli.py list
   The output should include "sample-app" as a target.

Use the existing targets (like csv-reporter) as examples of the expected structure.
Do NOT run an actual evaluation — just create the target files.
