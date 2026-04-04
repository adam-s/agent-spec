#!/bin/bash
# Ensure venv and install
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e . --quiet 2>/dev/null

# Run the relevant test files
.venv/bin/python3 -m pytest testing/python/collect.py testing/python/metafunc.py -x -q 2>&1

# Reproduction check: indirect=["val"] must not cause "duplicate parametrization" error
cat > /tmp/_repro_indirect.py << 'PYEOF'
import pytest

@pytest.fixture(params=["a", "b"])
def target(request):
    return request.param

@pytest.fixture
def val(request):
    return int(request.param)

@pytest.mark.parametrize(
    "val, target",
    [("1", 1), ("2", 2)],
    indirect=["val"],
)
def test_foo(val, target):
    assert str(val) == str(target)
PYEOF

OUTPUT=$(.venv/bin/python3 -m pytest /tmp/_repro_indirect.py -x -q 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "duplicate parametrization"; then
    echo "RESULT: FAIL"
elif echo "$OUTPUT" | grep -q "2 passed"; then
    echo "Reproduction checks passed"
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
