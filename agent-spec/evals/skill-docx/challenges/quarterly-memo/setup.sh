#!/bin/bash
# Pre-install both Python and Node tooling so the agent can pick either path.
python3 -m venv .venv
.venv/bin/pip install -r seeds/requirements.txt --quiet

# Install docx-js locally so the agent can `require('docx')` without network.
npm init -y --silent >/dev/null 2>&1
npm install docx --silent --no-audit --no-fund >/dev/null 2>&1
