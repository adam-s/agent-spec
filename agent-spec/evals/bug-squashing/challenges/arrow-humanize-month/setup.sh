#!/bin/bash
# Clone arrow at the buggy commit (parent of fix commit b423717)
git clone --depth 50 https://github.com/arrow-py/arrow.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout b423717~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e ".[test]" --quiet 2>/dev/null
