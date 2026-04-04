#!/bin/bash
# Clone aiohttp at the buggy commit (parent of fix commit cfcad08)
git clone --depth 50 https://github.com/aio-libs/aiohttp.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout cfcad08dbd4c2c4247f505d9a34ff5c09586b42e~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null
