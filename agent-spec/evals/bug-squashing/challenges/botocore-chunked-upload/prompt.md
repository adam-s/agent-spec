This workspace contains botocore — the low-level AWS SDK for Python, used internally by boto3.

A user reported the following bug:

> Passing a non-seekable stream to `s3.put_object()` with an explicit `ContentLength` fails with a `SignatureDoesNotMatch` error. A seekable stream (like `io.BytesIO`) works fine.
>
> The SDK is sending an incompatible set of headers:
> ```
> Content-Length: 11
> Transfer-Encoding: chunked
> Content-Encoding: aws-chunked
> ```
>
> This is explicitly disallowed in HTTP RFC 7230 section 3.3: "A sender MUST NOT send a Content-Length header field in any message that contains a Transfer-Encoding header field." The result is a signature mismatch because the client and server calculate different signatures.

A virtual environment is available at `.venv/`. Use `.venv/bin/python3` to run code.

Find and fix the bug. Run the tests with `.venv/bin/python3 -m pytest tests/unit/test_httpchecksum.py -x -q` to verify your fix.

Do not modify any test files.
