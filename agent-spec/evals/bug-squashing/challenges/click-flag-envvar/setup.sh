#!/bin/bash
# Clone click at the buggy commit (parent of fix commit 9caedb9)
git clone --depth 50 https://github.com/pallets/click.git .tmp-clone 2>/dev/null
cd .tmp-clone && git checkout 9caedb9206103dfb5465e1916bc2f13b9c10c0e4~1 2>/dev/null && cd ..

# Move repo contents to workspace root
mv .tmp-clone/* .tmp-clone/.* . 2>/dev/null
rm -rf .tmp-clone

# Set up Python environment
python3 -m venv .venv
.venv/bin/pip install -e . --quiet
.venv/bin/pip install pytest --quiet
