This workspace contains Rich — a Python library for rich text and formatting in the terminal.

There is a bug that causes `Console.print()` to hang indefinitely when given a string containing ANSI escape sequences. For example:

```python
from rich.console import Console
Console(highlight=False).print('\x1b[38;5;249mi\x1b[0m')
```

This hangs on the current version but worked on earlier versions. The issue is in `rich/cells.py` — the `split_graphemes()` function enters an infinite loop because ANSI escape characters like `\x1b` return 0 from `get_character_cell_size()`, causing the position to never advance.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug so that strings with ANSI escape sequences no longer cause a hang. Run the tests with `.venv/bin/python3 -m pytest tests/test_cells.py -x -q` to verify your fix.

Do not modify any test files.
