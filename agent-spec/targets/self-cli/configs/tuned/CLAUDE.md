# agent-spec CLI Exercise

You are inside agent-spec, a test harness for `.claude/` agents. Your task is to run CLI commands and save their output.

## CLI tools available

- `python3 scripts/cli.py list` — lists all evaluation targets
- `python3 scripts/system_monitor.py` — shows system resource status
- `python3 scripts/cli.py run --help` — shows run command help
- `python3 scripts/cli.py report --help` — shows report command help

## Instructions

1. Create a `cli-output/` directory
2. Run each command and redirect stdout+stderr to the corresponding file
3. Use `> file.txt 2>&1` to capture both stdout and stderr
4. Do NOT run any actual evaluations or launch any agents
