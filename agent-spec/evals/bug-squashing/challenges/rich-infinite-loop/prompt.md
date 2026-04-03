This workspace contains Rich — a Python library for rich text and formatting in the terminal.

A user reported the following bug:

> I was passing a string containing ANSI escape sequences into `Console.print()`. Prior to the latest release this would print a mostly unformatted string including ANSI escape sequences.
>
> With the latest release, this now results in a hang as ANSI escape characters such as `\x1b` return a 0 from `cells.get_character_cell_size()`, resulting in an infinite loop in `cells.split_graphemes()`. Previously, `\x1b` would return a 1 and the string would print without hanging.
>
> Example:
> ```python
> from rich.console import Console
> Console(highlight=False).print('\x1b[38;5;249mi\x1b[0m')
> ```

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_cells.py -x -q` to verify your fix.

Do not modify any test files.
