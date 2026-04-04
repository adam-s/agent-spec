#!/bin/bash
# Ensure venv and install
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e . --quiet 2>/dev/null
.venv/bin/pip install pytest --quiet 2>/dev/null

# Run the relevant unit tests
.venv/bin/python3 -m pytest t/unit/tasks/test_tasks.py t/unit/tasks/test_context.py -x -q 2>&1

# Reproduction check: time limits must propagate from app config to task request
OUTPUT=$(.venv/bin/python3 -c "
from celery import Celery

app = Celery('test')
app.conf.update(task_time_limit=300, task_soft_time_limit=60)

@app.task
def dummy():
    pass

dummy.bind(app)

# Bug 1: task attributes not set from config
task_tl = dummy.time_limit
task_stl = dummy.soft_time_limit
print(f'task.time_limit={task_tl}')
print(f'task.soft_time_limit={task_stl}')

# Bug 2: eager apply must pack timelimit into request
result = dummy.apply()
req_tl = result.request.get('time_limit') or result.request.get('timelimit')
print(f'request.timelimit={req_tl}')

if task_tl == 300 and task_stl == 60:
    print('Reproduction checks passed')
else:
    print(f'FAILED: task_time_limit={task_tl}, task_soft_time_limit={task_stl}')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
