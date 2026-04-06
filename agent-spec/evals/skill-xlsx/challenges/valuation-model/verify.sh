#!/bin/bash
# Verify valuation-model: check skill-specific financial model conventions.
# These are things the xlsx skill explicitly mandates that no model defaults to:
#   - Parens-negative number format ($#,##0;($#,##0);-)
#   - Yellow background on key assumption cells (RGB FFFF00)
#   - Blue font (RGB 0000FF) on input cells

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install openpyxl --quiet 2>/dev/null

if [ ! -f dcf.xlsx ]; then
    echo "dcf.xlsx not found"
    echo "RESULT: FAIL"
    exit 0
fi

OUTPUT=$(.venv/bin/python3 << 'PYEOF'
import sys
from openpyxl import load_workbook

errors = []

try:
    wb = load_workbook('dcf.xlsx')
except Exception as e:
    print(f'Could not open dcf.xlsx: {e}')
    sys.exit(1)

# Sanity: at least one sheet, with content
if not wb.sheetnames:
    print('No sheets found')
    sys.exit(1)

# Walk every cell in every sheet collecting evidence
parens_negative_count = 0   # cells with format containing ;(  (parens on negative)
yellow_fill_count = 0       # cells with yellow background fill
blue_font_count = 0         # cells with blue 0000FF font
formula_count = 0           # cells with =formula
year_text_count = 0         # cells whose value is a year stored as text

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    for row in ws.iter_rows():
        for cell in row:
            # Number format check — parens-negative pattern
            fmt = cell.number_format or ''
            if ';(' in fmt:
                parens_negative_count += 1

            # Yellow fill check — RGB FFFF00 (with or without alpha prefix)
            if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
                rgb = str(cell.fill.fgColor.rgb).upper()
                if rgb in ('FFFF00', 'FFFFFF00', '00FFFF00') or rgb.endswith('FFFF00'):
                    yellow_fill_count += 1

            # Blue font check — RGB 0000FF (with or without alpha prefix)
            if cell.font and cell.font.color and cell.font.color.rgb:
                rgb = str(cell.font.color.rgb).upper()
                if rgb in ('0000FF', 'FF0000FF', '000000FF') or rgb.endswith('0000FF'):
                    blue_font_count += 1

            # Formula check
            if isinstance(cell.value, str) and cell.value.startswith('='):
                formula_count += 1

            # Year-as-text check: a string that looks like a 4-digit year
            if isinstance(cell.value, str) and len(cell.value) == 4 and cell.value.isdigit():
                yr = int(cell.value)
                if 2020 <= yr <= 2035:
                    year_text_count += 1

# Sanity: needs to be a real DCF model with formulas
if formula_count < 5:
    errors.append(f'Only {formula_count} formulas found — expected a multi-year DCF with at least 5 formulas')

# Skill-specific assertions
# The xlsx skill consistently produces these patterns when followed.
# A spreadsheet built without the skill will not include them.
if parens_negative_count < 3:
    errors.append(
        f'Only {parens_negative_count} cells use the parens-negative number format ";(...)". '
        'The xlsx skill mandates negative numbers as parentheses (e.g., $#,##0;($#,##0);-) '
        'and applies it broadly across financial models. Expected at least 3.'
    )

if blue_font_count == 0:
    errors.append(
        'No cells have blue font color (RGB 0000FF). '
        'The xlsx skill mandates blue font for hardcoded input values'
    )

print(f'Evidence: {formula_count} formulas, {parens_negative_count} parens-negative formats, '
      f'{yellow_fill_count} yellow fills, {blue_font_count} blue fonts, {year_text_count} year-as-text')

if errors:
    print('ERRORS:')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)

print('All skill-specific conventions present')
PYEOF
)

EXIT=$?
echo "$OUTPUT"

if [ $EXIT -eq 0 ] && echo "$OUTPUT" | grep -q "All skill-specific conventions present"; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
