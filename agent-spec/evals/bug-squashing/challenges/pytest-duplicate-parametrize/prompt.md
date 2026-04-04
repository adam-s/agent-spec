This workspace contains pytest — the Python testing framework.

A user reported the following bug:

> When using `indirect=[...]` (a list) with `@pytest.mark.parametrize`, pytest incorrectly raises a "duplicate parametrization" collection error. This worked before and is a regression.
>
> Minimal reproduction:
>
> ```python
> import pytest
>
> @pytest.fixture(params=["a", "b"])
> def target(request):
>     return request.param
>
> @pytest.fixture
> def val(request):
>     return int(request.param)
>
> @pytest.mark.parametrize(
>     "val, target",
>     [("1", 1), ("2", 2)],
>     indirect=["val"],
> )
> def test_foo(val, target):
>     assert str(val) == str(target)
> ```
>
> Running this produces:
> ```
> test_bar.py::test_foo: duplicate parametrization of 'target'
> ```
>
> Expected: the test should collect and run — `target` is parametrized via the fixture and overridden via `parametrize` with `indirect=["val"]`, which should only make `val` indirect, leaving `target` as a direct override.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest testing/python/collect.py testing/python/metafunc.py -x -q` to verify your fix.

Do not modify any test files.
