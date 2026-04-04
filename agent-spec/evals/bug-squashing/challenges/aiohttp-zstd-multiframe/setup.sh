#!/bin/bash
# Clone aiohttp at the buggy commit (parent of fix commit cfcad08)
git clone --depth 50 https://github.com/aio-libs/aiohttp.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout cfcad08dbd4c2c4247f505d9a34ff5c09586b42e~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Init submodules (aiohttp vendors llhttp)
git submodule update --init 2>/dev/null

# Set up Python environment — skip C extensions (need Cython to build from source)
python3 -m venv .venv
AIOHTTP_NO_EXTENSIONS=1 .venv/bin/pip install -e . --quiet
.venv/bin/pip install pytest trustme pytest-asyncio --quiet
