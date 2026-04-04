#!/bin/bash
# Clone textual at the buggy commit (parent of fix commit 04b03c8)
git clone --depth 50 https://github.com/Textualize/textual.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 04b03c8db64266a6a7811cc161bae9986e53b1a1~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null
