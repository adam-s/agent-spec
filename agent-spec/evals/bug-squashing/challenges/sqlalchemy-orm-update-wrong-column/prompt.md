This workspace contains SQLAlchemy — a Python SQL toolkit and Object Relational Mapper.

A user reported the following bug:

> Executing an update-from in postgresql adds to the column list all the columns in the from table that have `onupdate`. This is not supported by postgresql.
>
> ```python
> from datetime import datetime
> from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
> import sqlalchemy as sa
> from sqlalchemy.dialects import postgresql
>
> class Base(DeclarativeBase):
>     pass
>
> class A(Base):
>     __tablename__ = "a"
>     id: Mapped[int] = mapped_column(primary_key=True)
>     updated_at: Mapped[datetime] = mapped_column(onupdate=sa.func.now())
>     is_deleted: Mapped[int] = mapped_column(default=0)
>
> class B(Base):
>     __tablename__ = "b"
>     id: Mapped[int] = mapped_column(primary_key=True)
>     updated_at: Mapped[datetime] = mapped_column(onupdate=sa.func.now())
>     is_deleted: Mapped[int] = mapped_column(default=0)
>
> u = sa.update(B.__table__).where(A.id.in_([1, 2, 3])).values(is_deleted=1)
> print(u.compile(dialect=postgresql.dialect()))
> ```
>
> This produces:
> ```sql
> UPDATE b SET is_deleted=%(a_is_deleted)s, updated_at=now(), updated_at=now() FROM a WHERE a.id IN (...)
> ```
>
> The `SET` clause includes columns from table `a` (the FROM table) instead of only from table `b` (the target table). The `is_deleted` parameter is also incorrectly bound to `a_is_deleted`. Using `A.__table__.c.id` instead of `A.id` in the WHERE clause avoids the bug, confirming it's the ORM layer that gets confused about which entity owns the statement.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest test/orm/dml/test_bulk_statements.py test/sql/test_update.py -x -q` to verify your fix.

Do not modify any test files.
