#!/bin/bash
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null

# Run the relevant test file
.venv/bin/python3 -m pytest tests/test_cells.py -x -q 2>&1
TESTS_EXIT=$?

# Reproduction check — must complete within 5 seconds (was hanging before)
REPRO=$(timeout 5 .venv/bin/python3 -c "
from rich.console import Console
import io

# This should not hang
output = io.StringIO()
console = Console(file=output, highlight=False)
console.print('\x1b[38;5;249mi\x1b[0m')
result = output.getvalue()
print(f'Output: {repr(result)}')
print('Reproduction checks passed')
" 2>&1)
REPRO_EXIT=$?

echo "$REPRO"

if [ $REPRO_EXIT -eq 124 ]; then
    echo "BUG: Console.print() still hangs (timeout)"
    echo "RESULT: FAIL"
elif [ $TESTS_EXIT -eq 0 ] && [ $REPRO_EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
