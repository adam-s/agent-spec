#!/bin/bash
# Ensure venv and install
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e . --quiet 2>/dev/null
.venv/bin/pip install pytest --quiet 2>/dev/null

# Run the relevant test files
.venv/bin/python3 -m pytest tests/test_options.py tests/test_basic.py -x -q 2>&1

# Reproduction check: boolean envvar must parse "false" as False
OUTPUT=$(.venv/bin/python3 -c "
import click
from click.testing import CliRunner

@click.command()
@click.option('--dry-run/--no-dry-run', default=False, envvar='DRY_RUN')
def main(dry_run):
    click.echo(f'dry_run={dry_run}')

runner = CliRunner(env={'DRY_RUN': 'false'})
result = runner.invoke(main, [])
output = result.output.strip()
print(output)

if 'dry_run=False' in output:
    print('Reproduction checks passed')
else:
    print(f'BUG: DRY_RUN=false was parsed as True')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
