#!/usr/bin/env python3
"""Test fizzbuzz output."""
import subprocess, sys

subprocess.run([sys.executable, "fizzbuzz.py"], stdout=open("fizzbuzz_output.txt", "w"), check=True)
lines = open("fizzbuzz_output.txt").read().strip().split("\n")

assert len(lines) == 100, f"Expected 100 lines, got {len(lines)}"
assert lines[0] == "1", f"Line 1: expected '1', got '{lines[0]}'"
assert lines[2] == "Fizz", f"Line 3: expected 'Fizz', got '{lines[2]}'"
assert lines[4] == "Buzz", f"Line 5: expected 'Buzz', got '{lines[4]}'"
assert lines[14] == "FizzBuzz", f"Line 15: expected 'FizzBuzz', got '{lines[14]}'"
assert lines[99] == "Buzz", f"Line 100: expected 'Buzz', got '{lines[99]}'"
print("All checks passed.")
