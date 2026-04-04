This workspace contains Textual — a Python framework for building terminal user interfaces.

A user reported the following bug:

> I ran the textual demo and started trying to select the text on the home page. The notification toast ends up getting selected as well, which actually prevents the auto-scrolling.
>
> After waiting for the notification to timeout and moving the mouse to try to auto-scroll the selection, the app crashes with `ValueError: No common ancestor found`.
>
> Perhaps the notifications just shouldn't be included in the selection, but presumably this could be a problem with any widget that could be removed from the DOM?

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_widget.py -x -q` to verify your fix.

Do not modify any test files.
