#!/bin/bash
# Clone pytest at the buggy commit (parent of fix PR #13976)
git clone --depth 200 https://github.com/pytest-dev/pytest.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 774372083b9555d41cc1c56cc1375f4011cc0054 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e . --quiet
