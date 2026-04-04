#!/bin/bash
# Ensure venv and install
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null

# Run the test suite
.venv/bin/python3 -m pytest tests/test_validate.py -x -q 2>&1

# Reproduction check: IDN emails must be accepted
OUTPUT=$(.venv/bin/python3 -c "
from marshmallow.validate import Email
v = Email()
cases = ['user@münchen.de', 'user@例え.jp', 'user@üñîçödé.com']
passed = 0
for addr in cases:
    try:
        v(addr)
        passed += 1
    except Exception as e:
        print(f'REJECTED: {addr} -> {e}')

# Invalid IDN should still be rejected
invalid_rejected = False
try:
    v('user@-münchen.de')
    print('ACCEPTED invalid: user@-münchen.de (should reject)')
except:
    invalid_rejected = True

if passed == len(cases) and invalid_rejected:
    print('Reproduction checks passed')
else:
    print(f'Reproduction failed: {passed}/{len(cases)} valid accepted, invalid_rejected={invalid_rejected}')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
