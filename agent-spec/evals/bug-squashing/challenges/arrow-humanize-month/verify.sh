#!/bin/bash
# Ensure environment exists
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[test]" --quiet 2>/dev/null

# Run the full test suite
.venv/bin/python3 -m pytest tests/ -x -q 2>&1
TESTS_EXIT=$?

# Run the specific reproduction case
REPRO=$(.venv/bin/python3 -c "
import arrow

# 16 days in the future within the same month should NOT be 'a month'
base = arrow.Arrow(2026, 1, 9)
future = arrow.Arrow(2026, 1, 25)  # 16 days later
result = base.humanize(future)
print(f'16 days: {result}')

# Actual month boundary should still work
feb = arrow.Arrow(2026, 2, 8)
mar = arrow.Arrow(2026, 3, 8)
month_result = feb.humanize(mar)
print(f'month boundary: {month_result}')

# Check: 16 days should say 'weeks' not 'month'
if 'month' in result:
    print('BUG: 16 days reported as a month')
    exit(1)
if 'month' not in month_result:
    print('BUG: actual month boundary not reported as a month')
    exit(1)
print('Reproduction checks passed')
" 2>&1)
REPRO_EXIT=$?

echo "$REPRO"

if [ $TESTS_EXIT -eq 0 ] && [ $REPRO_EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
