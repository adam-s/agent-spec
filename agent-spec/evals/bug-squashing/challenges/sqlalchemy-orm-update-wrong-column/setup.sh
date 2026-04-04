#!/usr/bin/env bash
set -e

git clone --depth 500 https://github.com/sqlalchemy/sqlalchemy.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout cbdc5b632c485fb695dd55e3a9d58b3ba35811ce 2>/dev/null && cd ..
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null || true
rm -rf .tmp-clone

DISABLE_SQLALCHEMY_CEXT=1 python3 -m venv .venv
.venv/bin/pip install -e . --quiet 2>/dev/null
.venv/bin/pip install pytest --quiet 2>/dev/null
