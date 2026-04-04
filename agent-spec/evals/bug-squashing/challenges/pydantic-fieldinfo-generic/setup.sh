#!/usr/bin/env bash
set -e

git clone --shallow-since=2025-11-01 https://github.com/pydantic/pydantic.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 6800281ba87625346daf5826563740ded8a9851b 2>/dev/null && cd ..
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null || true
rm -rf .tmp-clone

python3 -m venv .venv
.venv/bin/pip install -e "." --quiet 2>/dev/null
.venv/bin/pip install pytest pytest-benchmark dirty-equals jsonschema --quiet 2>/dev/null
