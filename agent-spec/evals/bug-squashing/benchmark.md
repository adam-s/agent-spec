# Bug-Squashing Benchmark

8 real bugs from open-source Python repos, all fixed after May 2025 (post training cutoff). Each has a known fix commit and test suite.

## Level Mapping

| Level | What | Where |
| ----- | ---- | ----- |
| 0 (Orchestrator) | agent-spec — launches agents, runs reviewer, scores, iterates | `agent-spec/` |
| 1 (Sub-agents) | Disposable Claude instances in cloned repo workspaces | `/tmp/claude/agent-spec-{uuid}/` |
| 2 (The Product) | Bug-squasher `.claude/` — injected via cordyceps | `bug-squasher/.claude/` |
| Workspaces | Cloned repos at buggy commits (not a level) | `/tmp/claude/agent-spec-{uuid}/` |

The eval symlinks to the product: `configs/bug-squasher → ../../../../bug-squasher/.claude`.

## Training Set (5 bugs)

The reviewer agent sees these bugs and their fixes during instruction tuning.

### 1. rich-infinite-loop

| Field | Value |
|-------|-------|
| Repo | Textualize/rich |
| Issue | #3958 |
| PR | #4006 |
| Fix commit | `7338cb9dafd0d0e916585f191ae505b3e602bb51` |
| Files | `rich/cells.py`, `tests/test_cells.py` |
| Bug type | Infinite loop (zero-width ANSI escape chars in split_graphemes) |
| Complexity | Medium — logic fix + edge case handling |

### 2. marshmallow-email-idn

| Field | Value |
|-------|-------|
| Repo | marshmallow-code/marshmallow |
| Issue | (linked in PR) |
| PR | #2937 |
| Fix commit | `f07eadc87dfac25ed505d5cd9d186920f2682733` |
| Files | `src/marshmallow/validate.py`, `tests/test_validate.py` |
| Bug type | Validation logic (Email validator rejects valid IDN domains) |
| Complexity | Medium — regex/validation fix |

### 3. arrow-humanize-month

| Field | Value |
|-------|-------|
| Repo | arrow-py/arrow |
| Issue | (linked in PR) |
| PR | #1242 |
| Fix commit | `b423717da81aaf8117313b4b377efaa6413a9639` |
| Files | `arrow/arrow.py` |
| Bug type | Boundary condition (humanize reports "a month" for 16-day diffs) |
| Complexity | Low — threshold adjustment |

### 4. werkzeug-bearer-whitespace

| Field | Value |
|-------|-------|
| Repo | pallets/werkzeug |
| Issue | (linked in PR) |
| PR | #3129 |
| Fix commit | `dafe7f1e37cf78cc7f11a9706c62a23e0dba9010` |
| Files | `src/werkzeug/datastructures/auth.py`, `tests/test_http.py` |
| Bug type | String formatting (trailing whitespace in WWW-Authenticate bearer) |
| Complexity | Low — small targeted fix |

### 5. botocore-chunked-upload

| Field | Value |
|-------|-------|
| Repo | boto/botocore |
| Issue | (linked in PR) |
| PR | #3652 |
| Fix commit | `b2e20b2d4e6ee92b7f46bbad73a5a9a7abe18b28` |
| Files | `botocore/httpchecksum.py`, `tests/functional/test_s3.py`, `tests/unit/test_httpchecksum.py` |
| Bug type | HTTP protocol (Content-Length + Transfer-Encoding: chunked conflict) |
| Complexity | Medium-high — protocol-level fix |

## Held-Out Set (3 bugs)

The reviewer agent NEVER sees these. Used only to validate that instruction improvements generalize.

### 6. textual-selection-disappearing

| Field | Value |
|-------|-------|
| Repo | Textualize/textual |
| Issue | #6452 |
| PR | #6455 |
| Fix commit | `04b03c8db64266a6a7811cc161bae9986e53b1a1` |
| Files | `src/textual/screen.py`, `src/textual/widget.py`, `tests/test_widget.py` |
| Bug type | UI state (selection disappears on interaction) |
| Complexity | Medium — state management fix |

### 7. aiohttp-zstd-multiframe

| Field | Value |
|-------|-------|
| Repo | aio-libs/aiohttp |
| Issue | #12234 |
| PR | #12290 |
| Fix commit | `cfcad08dbd4c2c4247f505d9a34ff5c09586b42e` |
| Files | `aiohttp/compression_utils.py`, `tests/test_compression_utils.py`, `tests/test_http_parser.py` |
| Bug type | Streaming (zstd decompression fails on multi-frame responses) |
| Complexity | Medium — compression pipeline fix |

### 8. httpcore-keepalive

| Field | Value |
|-------|-------|
| Repo | encode/httpcore |
| Issue | (linked in PR) |
| PR | #1000 |
| Fix commit | `10a658221deb38a4c5b16db55ab554b0bf731707` |
| Files | `httpcore/_async/connection_pool.py`, `httpcore/_sync/connection_pool.py`, tests |
| Bug type | Connection pool logic (idle connections dropped prematurely) |
| Complexity | Medium — must fix both sync and async pools |

## Bug Type Distribution

| Type | Count | Examples |
|------|-------|---------|
| Logic/boundary | 3 | infinite loop, month threshold, selection state |
| Validation | 2 | email IDN, unreachable warning |
| Protocol/format | 2 | chunked upload, bearer whitespace |
| Streaming/data | 1 | zstd multi-frame |

## Workspace Setup Pattern

For each bug:

1. `git clone --depth 50 <repo>` into workspace
2. `git checkout <fix_commit>~1` (the buggy state)
3. Install deps (`pip install -e .` or equivalent)
4. Agent gets bug description from the GitHub issue (sanitized of fix hints)
5. `verify.sh` runs the repo's test suite (or targeted test file)
