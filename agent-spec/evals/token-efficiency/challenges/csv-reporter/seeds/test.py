import subprocess
import sys

result = subprocess.run(
    [sys.executable, "report.py"],
    capture_output=True, text=True
)
output = result.stdout.strip()
lines = output.split("\n")
passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        failed += 1

check("Total revenue is $22015.00",
      any("$22015.00" in line for line in lines))

check("Top 3 products: Widget A (275), Widget B (126), Widget C (75)",
      any("Widget A (275)" in line and "Widget B (126)" in line and "Widget C (75)" in line for line in lines))

check("Revenue by region includes North ($9355.00)",
      any("North ($9355.00)" in line for line in lines))

check("Highest revenue month is 2024-05 ($4315.00)",
      any("2024-05" in line and "$4315.00" in line for line in lines))

check("Highest avg order value is Widget D ($585.00)",
      any("Widget D" in line and "$585.00" in line for line in lines))

print(f"\n{passed}/{passed + failed} tests passed")
if failed > 0:
    sys.exit(1)
