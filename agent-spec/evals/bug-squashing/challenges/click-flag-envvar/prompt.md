This workspace contains click — a Python package for creating command line interfaces.

A user reported the following bug:

> Setting a boolean flag option's environment variable to `false` is parsed as `True`. The flag value is always `True` when setting any envvar, regardless of the envvar's value.
>
> ```python
> import click
>
> @click.command()
> @click.option("--dry-run/--no-dry-run", default=False, envvar="DRY_RUN")
> def main(dry_run: bool):
>     print(type(dry_run))
>     print(f"Dry run: {dry_run}")
>
> if __name__ == "__main__":
>     main()
> ```
>
> ```sh
> export DRY_RUN=false
> python hi.py
> ```
>
> Output:
> ```
> <class 'bool'>
> Dry run: True
> ```
>
> Expected: `Dry run: False` — the envvar value `"false"` should be parsed as boolean `False`.
>
> The root issue is in how flag options reconcile `default`, `flag_value`, `type`, and environment variable parsing. The absence of a value is being mixed up with the value of absence.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_options.py tests/test_basic.py -x -q` to verify your fix.

Do not modify any test files.
