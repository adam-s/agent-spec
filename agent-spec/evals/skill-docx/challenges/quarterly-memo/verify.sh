#!/bin/bash
# Verify quarterly-memo: check skill-specific docx conventions.
# These are things the docx skill explicitly mandates that no default tool produces:
#   - Arial as the default font (docx-js defaults to Times-ish; python-docx defaults to Calibri)
#   - Bulleted lists implemented via real numbering (w:numPr) and NEVER unicode bullets in text
#   - Heading styles applied to section titles (built-in Heading1/Heading2 IDs)

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --quiet 2>/dev/null

if [ ! -f memo.docx ]; then
    echo "memo.docx not found"
    echo "RESULT: FAIL"
    exit 0
fi

OUTPUT=$(.venv/bin/python3 << 'PYEOF'
import sys
import zipfile
import re

errors = []

try:
    z = zipfile.ZipFile('memo.docx')
except Exception as e:
    print(f'Could not open memo.docx as zip: {e}')
    sys.exit(1)

names = z.namelist()
if 'word/document.xml' not in names or '[Content_Types].xml' not in names:
    print('Not a valid .docx — missing word/document.xml or [Content_Types].xml')
    sys.exit(1)

document_xml = z.read('word/document.xml').decode('utf-8', errors='replace')
styles_xml = z.read('word/styles.xml').decode('utf-8', errors='replace') if 'word/styles.xml' in names else ''
numbering_xml = z.read('word/numbering.xml').decode('utf-8', errors='replace') if 'word/numbering.xml' in names else ''

# --- Sanity: enough text content for a real memo ---
text_runs = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', document_xml)
all_text = ' '.join(text_runs)
if len(all_text) < 200:
    errors.append(
        f'Document has only {len(all_text)} characters of text — '
        'expected a multi-section memo with at least 200 characters'
    )

# --- Heading style check ---
# The skill mandates using built-in Heading IDs (Heading1, Heading2, ...)
heading_style_uses = re.findall(r'<w:pStyle\s+w:val="(Heading[1-9])"', document_xml)
if not heading_style_uses:
    errors.append(
        'No paragraphs use a Heading style (Heading1/Heading2/...). '
        'The docx skill mandates applying built-in heading styles to section titles'
    )

# --- Bullet check: must use w:numPr, NOT unicode bullets in text ---
# Real bullets reference a numbering definition.
num_pr_count = len(re.findall(r'<w:numPr\b', document_xml))
if num_pr_count < 6:
    errors.append(
        f'Only {num_pr_count} paragraphs use <w:numPr> numbering. '
        'The docx skill mandates real list numbering for bullets; '
        'the memo asks for 10 bullet points across three sections'
    )

# Unicode bullets inside text runs are forbidden by the skill.
unicode_bullet_chars = ['\u2022', '\u25E6', '\u25AA', '\u25CF', '\u00B7']
unicode_bullets_in_text = sum(
    sum(t.count(ch) for ch in unicode_bullet_chars) for t in text_runs
)
if unicode_bullets_in_text > 0:
    errors.append(
        f'Found {unicode_bullets_in_text} unicode bullet characters inside <w:t> text runs. '
        'The docx skill explicitly forbids unicode bullets — bullets must use w:numPr numbering'
    )

# --- Font check: Arial must appear as a configured font ---
# The skill mandates Arial as the default font.
arial_in_styles = 'Arial' in styles_xml
arial_in_document = 'Arial' in document_xml
if not (arial_in_styles or arial_in_document):
    errors.append(
        'No reference to "Arial" font in styles.xml or document.xml. '
        'The docx skill mandates Arial as the default font for universal compatibility'
    )

print(
    f'Evidence: {len(text_runs)} text runs ({len(all_text)} chars), '
    f'{len(heading_style_uses)} heading-style paragraphs, '
    f'{num_pr_count} numbered paragraphs, '
    f'{unicode_bullets_in_text} unicode bullets in text, '
    f'arial_in_styles={arial_in_styles} arial_in_document={arial_in_document}'
)

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
