#!/bin/bash
git clone --depth 50 https://github.com/Textualize/rich.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 7338cb9~1 2>/dev/null && cd ..
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null
