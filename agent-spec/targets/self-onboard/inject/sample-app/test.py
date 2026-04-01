"""Tests for word counter app."""
import subprocess
import sys
import tempfile
import os

passed = 0
total = 0


def test(name, text, expected_unique):
    global passed, total
    total += 1
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        f.flush()
        result = subprocess.run(
            [sys.executable, "app.py", f.name],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
        )
    os.unlink(f.name)
    if f"Total unique words: {expected_unique}" in result.stdout:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name}")
        print(f"  Expected unique words: {expected_unique}")
        print(f"  Got: {result.stdout.strip()}")


test("basic count", "hello world hello", 2)
test("case insensitive", "Hello hello HELLO", 1)
test("punctuation", "yes! yes. yes? no.", 2)
test("empty", "", 0)

print(f"{passed}/{total} tests passed")
