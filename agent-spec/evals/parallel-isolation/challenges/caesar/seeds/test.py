#!/usr/bin/env python3
"""Test caesar cipher."""
import subprocess, sys

cases = [
    ("3\nHello, World!", "Khoor, Zruog!"),
    ("13\nThe Quick Brown Fox", "Gur Dhvpx Oebja Sbk"),
    ("-3\nKhoor, Zruog!", "Hello, World!"),
    ("0\nNo change", "No change"),
]

results = []
for input_text, expected in cases:
    result = subprocess.run([sys.executable, "caesar.py"], input=input_text, capture_output=True, text=True, check=True)
    got = result.stdout.strip()
    assert got == expected, f"Input '{input_text}': expected '{expected}', got '{got}'"
    results.append(got)

open("caesar_output.txt", "w").write("\n".join(results) + "\n")
print("All checks passed.")
