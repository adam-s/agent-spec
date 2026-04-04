#!/usr/bin/env bash
set -e

# Run the relevant test suites
.venv/bin/python3 -m pytest test/orm/dml/test_bulk_statements.py test/sql/test_update.py -x -q
if [ $? -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 0
fi

# Reproduction check: compile an UPDATE with cross-entity WHERE
# The bug causes columns from the wrong table to appear in SET
.venv/bin/python3 -c "
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

class Base(DeclarativeBase):
    pass

class A(Base):
    __tablename__ = 'a'
    id: Mapped[int] = mapped_column(primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(onupdate=sa.func.now())
    is_deleted: Mapped[int] = mapped_column(default=0)

class B(Base):
    __tablename__ = 'b'
    id: Mapped[int] = mapped_column(primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(onupdate=sa.func.now())
    is_deleted: Mapped[int] = mapped_column(default=0)

u = sa.update(B.__table__).where(A.id.in_([1, 2, 3])).values(is_deleted=1)
compiled = str(u.compile(dialect=postgresql.dialect()))
print(f'Compiled SQL: {compiled}')

# Check 1: SET clause should not have duplicate updated_at
set_clause = compiled.split('SET')[1].split('FROM')[0]
if set_clause.count('updated_at') > 1:
    print('BUG: duplicate updated_at in SET clause (columns from wrong table)')
    exit(1)

# Check 2: is_deleted param should be bound to is_deleted, not a_is_deleted
if 'a_is_deleted' in compiled:
    print('BUG: is_deleted bound to wrong table alias')
    exit(1)

# Check 3: SET clause should only reference target table columns
if 'a.' in set_clause.replace('updated_at', ''):
    print('BUG: SET clause references columns from FROM table')
    exit(1)

print('Reproduction checks passed')
"
if [ $? -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 0
fi

echo "RESULT: PASS"
