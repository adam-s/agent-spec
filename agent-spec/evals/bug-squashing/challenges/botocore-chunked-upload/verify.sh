#!/bin/bash
# Ensure venv and install
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet 2>/dev/null

# Run the relevant test file
.venv/bin/python3 -m pytest tests/unit/test_httpchecksum.py -x -q 2>&1

# Reproduction check: non-seekable stream with Content-Length must not keep both headers
OUTPUT=$(.venv/bin/python3 -c "
import io
from botocore.httpchecksum import apply_request_checksum

class NonSeekableStream(io.RawIOBase):
    def __init__(self, data):
        self._data = data
        self._pos = 0
    def read(self, n=-1):
        if n == -1:
            n = len(self._data) - self._pos
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk
    def readable(self):
        return True

# Build a minimal request-like dict
request = {
    'headers': {
        'Content-Length': '11',
    },
    'body': NonSeekableStream(b'hello world'),
    'url': 'https://bucket.s3.amazonaws.com/key',
    'context': {
        'checksum': {
            'request_algorithm': {
                'algorithm': 'crc32',
                'in': 'trailer',
                'name': 'crc32',
            }
        }
    },
}

apply_request_checksum(request)

headers = request['headers']
has_content_length = 'Content-Length' in headers
has_transfer_encoding = headers.get('Transfer-Encoding', '') == 'chunked'
has_decoded_length = 'X-Amz-Decoded-Content-Length' in headers

if has_content_length and has_transfer_encoding:
    print('BUG: Both Content-Length and Transfer-Encoding: chunked present')
elif has_decoded_length and not has_content_length:
    print('Reproduction checks passed')
else:
    print(f'Unexpected state: CL={has_content_length} TE={has_transfer_encoding} decoded={has_decoded_length}')
" 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Reproduction checks passed"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
