#!/bin/bash
# Clone botocore at the buggy commit (parent of fix commit b2e20b2)
git clone --depth 50 https://github.com/boto/botocore.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout b2e20b2d4e6ee92b7f46bbad73a5a9a7abe18b28~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e . --quiet 2>/dev/null
