#!/bin/bash
# Ensure venv and install (skip C extensions — need Cython to build from source)
[ -d .venv ] || python3 -m venv .venv
AIOHTTP_NO_EXTENSIONS=1 .venv/bin/pip install -e . --quiet 2>/dev/null
.venv/bin/pip install pytest trustme pytest-asyncio --quiet 2>/dev/null

# Run tests (override addopts to avoid xdist dependency)
.venv/bin/python3 -m pytest tests/test_compression_utils.py -x -q -o 'addopts=' 2>&1

# Reproduction check: multi-frame zstd decompression
OUTPUT=$(.venv/bin/python3 -c "
import compression.zstd as zstd

# Create two separate zstd frames
c1 = zstd.ZstdCompressor()
frame1 = c1.compress(b'A' * 1000) + c1.flush()
c2 = zstd.ZstdCompressor()
frame2 = c2.compress(b'B' * 1000) + c2.flush()

multi_frame = frame1 + frame2

# Use aiohttp's ZSTD decompressor
from aiohttp.compression_utils import ZSTDDecompressor

d = ZSTDDecompressor()
try:
    result = d.decompress_sync(multi_frame, 0)
    if result == b'A' * 1000 + b'B' * 1000:
        print('Reproduction checks passed')
    else:
        print(f'Wrong output: got {len(result)} bytes, expected 2000')
except Exception as e:
    print(f'Decompression failed: {type(e).__name__}: {e}')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
