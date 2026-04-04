This workspace contains Pydantic — a data validation library for Python.

A user reported the following bug:

> When parameterizing a generic model with an `Annotated` type, the `FieldInfo` is not properly rebuilt. The field metadata from the `Annotated` wrapper is lost or double-wrapped.
>
> ```python
> from typing import Annotated
> from pydantic import BaseModel, Field
>
> class Model[T](BaseModel):
>     t: T
>
> M = Model[Annotated[int, Field(gt=1)]]
>
> M.model_fields['t']
> #> FieldInfo(annotation=Annotated[int, FieldInfo(annotation=NoneType, required=True, metadata=[Gt(gt=1)])], required=True)
> ```
>
> The `annotation` should be `int` (the inner type), not the full `Annotated[...]` wrapper. And the `metadata` list on the outer `FieldInfo` should contain `Gt(gt=1)`, but it's empty — the constraint is trapped inside the nested `FieldInfo`.
>
> Using `Model[int]` works fine, confirming the bug is specific to `Annotated` type substitution during generic parameterization.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_fields.py -x -q -o 'addopts='` to verify your fix.

Do not modify any test files.

---

**Hint from a previous debugging attempt:** A prior attempt patched `apply_typevars_map` to detect and unwrap `FieldInfo` inside `Annotated`, but this only handled the `Field(gt=1)` case — plain metadata like `Annotated[int, 3]` was still left wrapped. The fix should handle all `Annotated` metadata types, not just `FieldInfo`. Consider using `FieldInfo.from_annotation()` which already knows how to unpack any `Annotated` type.
