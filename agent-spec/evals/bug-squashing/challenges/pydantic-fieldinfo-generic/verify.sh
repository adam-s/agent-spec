#!/usr/bin/env bash
set -e

# Run existing test suite
.venv/bin/python3 -m pytest tests/test_fields.py -x -q -o 'addopts='
if [ $? -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 0
fi

# Reproduction check: parameterize generic model with Annotated type
.venv/bin/python3 -c "
from typing import Annotated, Generic, TypeVar
from pydantic import BaseModel, Field
from annotated_types import Gt

T = TypeVar('T')

class Model(BaseModel, Generic[T]):
    t: T

M = Model[Annotated[int, Field(gt=1)]]
field = M.model_fields['t']

# After fix: annotation should be int, not Annotated[...]
if field.annotation is not int:
    print(f'BUG: annotation is {field.annotation!r}, expected int')
    exit(1)

# Metadata should contain the Gt constraint
gt_items = [m for m in field.metadata if isinstance(m, Gt)]
if not gt_items:
    print(f'BUG: metadata missing Gt constraint, got {field.metadata!r}')
    exit(1)

if gt_items[0].gt != 1:
    print(f'BUG: Gt constraint has wrong value {gt_items[0].gt}, expected 1')
    exit(1)

# Multi-field case: existing Annotated + substituted Annotated
class Parent(BaseModel, Generic[T]):
    a: T
    b: Annotated[T, 1]

Sub = Parent[Annotated[int, 3]]

if Sub.model_fields['a'].annotation is not int:
    print(f'BUG: Parent.a annotation is {Sub.model_fields[\"a\"].annotation!r}, expected int')
    exit(1)

if Sub.model_fields['b'].annotation is not int:
    print(f'BUG: Parent.b annotation is {Sub.model_fields[\"b\"].annotation!r}, expected int')
    exit(1)

print('Reproduction checks passed')
"
if [ $? -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 0
fi

echo "RESULT: PASS"
