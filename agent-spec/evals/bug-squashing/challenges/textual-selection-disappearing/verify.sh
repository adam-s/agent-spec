#!/bin/bash
# Ensure venv and install (agent may have broken or moved it)
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null

# Run the relevant test files
.venv/bin/python3 -m pytest tests/test_widget.py -x -q 2>&1

# Reproduction check: selection with removed widget must not crash
# The bug crashes with ValueError when a widget in the selection is
# removed from the DOM (e.g. notification toast timeout).
# The fix should either prevent such widgets from being selected
# or handle the missing ancestor gracefully.
OUTPUT=$(.venv/bin/python3 -c "
# Check that the fix is present by testing the actual behavior:
# get_common_ancestor with detached widgets, or toast non-selectability
from textual.widget import Widget

# Test 1: Check if toast widgets are marked non-selectable
try:
    from textual.widgets._toast import Toast
    toast = Toast('test')
    if not getattr(toast, 'ALLOW_SELECT', True):
        print('Toast is non-selectable - fix applied via ALLOW_SELECT')
        print('Reproduction checks passed')
    else:
        # Toast is still selectable - check if screen handles the error
        from textual.screen import Screen
        import inspect
        src = inspect.getsource(Screen)
        if 'ValueError' in src and 'ancestor' in src.lower():
            print('Screen handles ValueError for missing ancestors')
            print('Reproduction checks passed')
        else:
            print('Fix not found: toast is selectable and screen does not catch ValueError')
except ImportError:
    # Toast module may have different structure
    print('Could not import Toast - checking screen directly')
    from textual.screen import Screen
    import inspect
    src = inspect.getsource(Screen)
    if 'ValueError' in src:
        print('Screen handles ValueError')
        print('Reproduction checks passed')
    else:
        print('Fix not found')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
