This workspace contains aiohttp — an asynchronous HTTP client/server framework for Python.

A user reported the following bug:

> When a server responds with a zstd-encoded response containing multiple frames, aiohttp fails to decompress the second frame with `ClientPayloadError: 400, message: Can not decode content-encoding: zstd`.
>
> Internally the exception is "Already at the end of a Zstandard frame" — the `ZstdDecompressor` is one-shot-per-frame and cannot process additional frames after the first one ends.
>
> Python docs mention this limitation and suggest using `compression.zstd.decompress` to avoid it, but that doesn't work for streaming decompression.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/test_compression_utils.py -x -q` to verify your fix.

Do not modify any test files.
