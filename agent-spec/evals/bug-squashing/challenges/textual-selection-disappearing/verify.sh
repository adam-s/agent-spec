#!/bin/bash
# Ensure venv and install
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null

# Run the relevant test files
.venv/bin/python3 -m pytest tests/test_widget.py -x -q 2>&1

# Reproduction check: the fix must handle selection when widgets are removed.
# Two valid approaches: (1) make toast non-selectable, or (2) catch ValueError in screen
OUTPUT=$(.venv/bin/python3 -c "
from textual.widgets._toast import Toast, ToastHolder, ToastRack

# Check if toast-related widgets are marked non-selectable
toast_classes = [Toast, ToastHolder, ToastRack]
non_selectable = all(
    getattr(cls, 'ALLOW_SELECT', True) is False
    for cls in toast_classes
)

if non_selectable:
    print('Toast widgets are non-selectable - fix applied')
    print('Reproduction checks passed')
else:
    # Alternative: check if screen handles the error
    import inspect
    from textual.screen import Screen
    src = inspect.getsource(Screen)
    if 'ValueError' in src or 'common_ancestor' in src.lower():
        print('Screen handles ValueError for missing ancestors')
        print('Reproduction checks passed')
    else:
        print('Fix not found: toast is selectable and screen does not catch ValueError')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
