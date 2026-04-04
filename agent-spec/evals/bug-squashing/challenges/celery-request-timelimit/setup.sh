#!/bin/bash
# Clone celery at the buggy commit (parent of fix commit 1fe2a08)
git clone --depth 50 https://github.com/celery/celery.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 1fe2a08d0c71ec83a242e1032d48fb804f92337a~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e . --quiet
.venv/bin/pip install pytest --quiet
