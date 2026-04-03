#!/usr/bin/env python3
"""Test palindrome checker."""
import subprocess, sys

input_text = "racecar\nhello\nA man a plan a canal Panama\nworld\nWas it a car or a cat I saw\n"
result = subprocess.run([sys.executable, "palindrome.py"], input=input_text, capture_output=True, text=True, check=True)
open("palindrome_output.txt", "w").write(result.stdout)
lines = result.stdout.strip().split("\n")

expected = ["YES", "NO", "YES", "NO", "YES"]
assert len(lines) == 5, f"Expected 5 lines, got {len(lines)}"
for i, (got, exp) in enumerate(zip(lines, expected)):
    assert got.strip() == exp, f"Line {i+1}: expected '{exp}', got '{got.strip()}'"
print("All checks passed.")
