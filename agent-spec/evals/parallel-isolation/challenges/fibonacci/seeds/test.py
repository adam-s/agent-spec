#!/usr/bin/env python3
"""Test fibonacci output."""
import subprocess, sys

subprocess.run([sys.executable, "fibonacci.py"], stdout=open("fibonacci_output.txt", "w"), check=True)
lines = open("fibonacci_output.txt").read().strip().split("\n")

expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181]
assert len(lines) == 20, f"Expected 20 lines, got {len(lines)}"
for i, (got, exp) in enumerate(zip(lines, expected)):
    assert int(got.strip()) == exp, f"Line {i+1}: expected {exp}, got {got.strip()}"
print("All checks passed.")
