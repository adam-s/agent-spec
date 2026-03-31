# Bug Catalog

Bugs discovered during harness iterations. Each entry documents a class of problem, not just a specific instance.

---

## B01: macOS date format incompatibility

**Story:** `date +%s%3N` was used for millisecond timestamps. On macOS, `%3N` is not supported and produces a literal `3N` suffix, causing bash arithmetic to fail with "value too great for base".

**Impact:** invoke.sh crashed before running the agent. Duration tracking was completely broken.

**General principle:** Never assume GNU coreutils behavior on macOS. Use `date +%s` (seconds) and multiply, or use Python for precise timestamps.

**Authoritative rule:** All bash scripts must work on macOS (BSD userland) and Linux (GNU coreutils). Test both.

---

## B02: Bash brace expansion in default values

**Story:** `${4:-{}}` was intended to default to empty JSON `{}`, but bash interprets the braces as part of the parameter expansion syntax. The default consumed only `{` and appended a literal `}`, producing `{"a":1}}` — invalid JSON.

**Impact:** Every APC log entry had malformed JSON. All jq parsing silently failed.

**General principle:** Never use `{}` inside `${var:-default}`. Assign defaults separately: `data="${4:-"{}"}"`

**Authoritative rule:** Use `python3` or `jq` to build JSON from bash. Never use `printf` with user-provided JSON fragments.

---

## B03: Stale sandbox files distort evaluations

**Story:** When the sandbox copies the full source repo, it includes the reference implementation (e.g., `report.py`). The agent can just modify the existing file instead of writing from scratch, making the task trivially easy and the evaluation meaningless.

**Impact:** Token counts are artificially low. The evaluation doesn't test the agent's ability to produce code — it tests its ability to not break existing code.

**General principle:** Delete the files the agent must produce before running the evaluation. The `delete_before_run` field in target.yaml specifies which files.

**Authoritative rule:** Always verify the sandbox does NOT contain the expected output before invoking the agent.

---

## B04: Orphaned server processes from WebSocket tests

**Story:** The hono-websocket-counter test starts a bun server. If the test or verify script fails, the server stays running on port 3100, blocking subsequent runs and consuming 100% CPU.

**Impact:** Port collisions on re-runs. CPU waste. Requires manual cleanup.

**General principle:** Every process started during verification must be tracked and stopped, even on failure. Use `trap` for cleanup in verify scripts, and always stop port processes before starting new ones.

**Authoritative rule:** verify.sh scripts that start servers must stop them in all exit paths. The harness must stop known ports before and after each run.

---

## B05: Sidecar termination noise in output

**Story:** Stopping the resource monitor sidecar with `kill` produces a "Terminated: 15" message on stderr that leaks into the harness output, confusing users.

**Impact:** Cosmetic — users see a misleading "Terminated" line after a successful run.

**General principle:** After sending a stop signal, always `wait` for the process to suppress the shell's built-in termination message.

**Authoritative rule:** Pattern: `kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true`

---

## B06: cleanup.sh fails on empty glob

**Story:** `ls -d /tmp/claude/agent-spec-*/` exits with code 1 when no matches exist. Under `set -euo pipefail`, this halts the entire cleanup script.

**Impact:** Cleanup reports failure even when everything is already clean.

**General principle:** Glob commands that may match zero files must have `|| true` or `2>/dev/null` to handle the empty case.

**Authoritative rule:** Always guard glob-based ls/find with `|| echo "0"` or similar fallback.

---

## B07: Token-efficient instructions cost more tokens

**Story:** A 6-line CLAUDE.md with rules like "no preamble, no closing fluff, prefer simple code" caused haiku to use 4,582 tokens on csv-reporter, vs 1,723 for the 1-line baseline ("A coding project."). The instructions added input token overhead on every turn without reducing output.

**Impact:** 2.7x more expensive. 2.4x longer duration. Same pass rate (both PASS).

**General principle:** Instruction overhead compounds per turn. Short, declarative instructions add context to every API call. On simple tasks where the agent gets it right on the first try, any instruction beyond the minimum is pure cost.

**Authoritative rule:** Always measure. Never assume instructions save tokens — test with baseline and compare. Instructions are an optimization for complex tasks where first-attempt failure is common, not for simple one-shot tasks.

---

## B08: run-eval.sh YAML parser f-string escaping

**Story:** The Python YAML parser was embedded in a bash `eval "$(python3 -c "...")"` block. Python f-strings with `{` characters were interpreted as bash parameter expansion, producing syntax errors.

**Impact:** run-eval.sh was completely broken on first attempt.

**General principle:** Never embed Python with f-strings or regex inside bash `eval "$(python3 -c "...")"`. The `{` and `}` characters conflict between Python and bash.

**Authoritative rule:** Use heredoc with single-quoted delimiter (`<< 'PYEOF'`) for inline Python in bash. Pass variables via environment, not string interpolation.

---

## B09: Uninitialized bash arrays under set -u

**Story:** `EXTRA_FLAGS=()` was declared but never populated. `"${EXTRA_FLAGS[@]}"` under `set -u` (treat unset variables as errors) throws "unbound variable" because bash treats an empty array as unset.

**Impact:** run-eval.sh crashed when no extra flags were passed (the common case).

**General principle:** Empty bash arrays are "unbound" under `set -u`. Guard with `${#array[@]} -gt 0` before expansion.

**Authoritative rule:** Pattern: `if [[ ${#ARRAY[@]} -gt 0 ]]; then cmd "${ARRAY[@]}"; fi`

---

## B10: Port allocation race in parallel runs

**Story:** `parallel-invoke.sh` launched 3 invoke.sh instances simultaneously. Each scanned ports 3100-3110 with `lsof` and all 3 saw 3100 as free before any agent bound it. All 3 agents got port 3100, causing collisions.

**Impact:** Port collisions caused test failures (instance 3 FAIL) despite correct agent code. False negative — the agent wrote correct code but verification ran against the wrong server.

**General principle:** Non-atomic port allocation races when multiple processes scan simultaneously. The scanner sees the port as free, but by the time the process binds it, another process already has it.

**Authoritative rule:** For parallel runs, pre-assign ports sequentially in the launcher (3100, 3101, 3102...) and pass via `--port`. Never let parallel processes independently scan for free ports.
