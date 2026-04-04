#!/bin/bash
# Clone marshmallow at the buggy commit (parent of fix commit f07eadc)
git clone --depth 50 https://github.com/marshmallow-code/marshmallow.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout f07eadc87dfac25ed505d5cd9d186920f2682733~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null
