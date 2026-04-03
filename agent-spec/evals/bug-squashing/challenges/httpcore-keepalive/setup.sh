#!/bin/bash
git clone --depth 50 https://github.com/encode/httpcore.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 10a65822~1 2>/dev/null && cd ..
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

python3 -m venv .venv
.venv/bin/pip install -e ".[trio,anyio]" --quiet 2>/dev/null
.venv/bin/pip install pytest pytest-httpbin trustme --quiet 2>/dev/null
