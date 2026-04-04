This workspace contains celery — a distributed task queue for Python.

A user reported the following bug:

> When configuring time limits via `app.conf`, `task.request.time_limit` and `task.request.soft_time_limit` are always `None` inside a running task, even when the limits are correctly set in the app config.
>
> ```python
> celery_app.conf.update(
>     task_soft_time_limit=3,
>     task_time_limit=10,
> )
>
> @task_prerun.connect
> def on_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **_):
>     req = getattr(task, "request", None)
>     if req:
>         print(f"soft_limit={getattr(req, 'soft_time_limit', None)}")
> ```
>
> Expected: `soft_time_limit` should be `3` (from config)
> Actual: `soft_time_limit` is `None`
>
> This affects both worker execution and eager mode (`task.apply()`).

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest t/unit/tasks/test_tasks.py t/unit/tasks/test_context.py -x -q` to verify your fix.

Do not modify any test files.
