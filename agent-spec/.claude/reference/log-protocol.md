# Log Protocol

All events are JSONL lines appended to `/tmp/agent-spec/{run_id}/events.jsonl`.

## Stdout Protocol

invoke.py emits the same events as JSONL on **stdout** (compact, one per line):

```
{"event":"run_started","data":{"run_id":"abc","target":"csv-reporter","config":"baseline",...}}
{"event":"agent_complete","data":{"duration_ms":28000}}
{"event":"token_update","data":{"input":7,"output":1006,"cost_usd":0.078}}
{"event":"score","data":{"result":"PASS"}}
{"event":"run_finished","data":{"run_id":"abc","result":"PASS","cost_usd":0.078,"duration_s":28}}
```

Human-readable output (headers, spinners, status lines) goes to **stderr**. Parent processes (parallel.py) read stdout JSONL to track child results — no regex parsing needed.

To capture only the structured stream: `python3 scripts/invoke.py ... 2>/dev/null | jq .`

## Format

```json
{"ts":"ISO8601","level":"INFO","src":"script.sh","event":"event_name","msg":"text","data":{}}
```

## Levels

`DEBUG`, `INFO`, `WARN`, `ERROR`, `METRIC`

## Well-Known Events

### Lifecycle
- `run_started` — run_id, target, config, model, budget, port
- `sandbox_created` — sandbox, source
- `files_deleted` — files (comma-separated list)
- `files_injected` — from (inject directory path)
- `setup_command` — cmd, exit_code (each successful setup command)
- `setup_complete` — (all setup done)
- `setup_failed` — cmd, exit_code, stderr
- `empty_config` — config (WARN: agent has no instructions)
- `config_swapped` — config
- `agent_started` — target, config, model, budget, port
- `agent_complete` — exit_code, duration_ms
- `agent_error` — exit_code, duration_ms, stderr
- `agent_timeout` — timeout
- `run_terminated` — signal, run_id (external SIGTERM/SIGINT/SIGHUP)
- `run_finished` — run_id, target, config, result, cost_usd, duration_s (terminal event)

### Verification
- `verification_output` — output (full verify.sh stdout+stderr), exit_code
- `test_passed` / `test_failed` — test_name
- `score` — result (PASS/FAIL/N/A)

### Parallel
- `parallel_started` — target, total, configs, models, instances
- `instance_launched` — instance, config, model, port
- `instance_complete` — instance, run_id, result, exit_code
- `instance_failed` — instance, run_id, exit_code, stderr_tail
- `parallel_complete` — total, passed, failed, run_ids, duration_ms

### Iteration
- `iteration_started` — depth, max_depth, target, config, session_id, instances
- `iteration_diagnosed` — depth, session_id, findings_count, findings_summary
- `iteration_fixed` — depth, session_id, files_changed (list of paths)
- `iteration_complete` — depth, session_id, converged (bool), pass_rate, duration_ms
- `iteration_session_complete` — session_id, final_depth, converged, total_cost_usd, total_duration_ms

### Metrics
- `token_update` — input, output, cache_create, cache_read, cost_usd, turns, duration_ms, duration_api_ms, stop_reason, session_id, is_error, result_message, permission_denials
- `resource_snapshot` — cpu, mem, disk_free_gb

### Stream Events (only with `--stream` flag)
- `claude_turn_start` — role (new conversational turn)
- `claude_tool_use` — tool, tool_use_id (agent called a tool)

Raw Claude stream events are saved to `{run_dir}/stream.jsonl` for post-run analysis.

## Emitting

- **Bash**: `source scripts/lib.sh` then `apc_log LEVEL event "message" '{"key":"value"}'`
- **Python**: `from _apc import log; log("INFO", "event", "message", {"key": "value"})`
- **TypeScript**: `import { log } from "./_apc"; log("INFO", "event", "message", { key: "value" })`

## Debug Logging

Developer diagnostics with lazy evaluation and env toggle. Writes to stderr (dim) and `events.jsonl` (level `DEBUG`, event `debug:{tag}`). Filter with `jq 'select(.level=="DEBUG")'`.

Disabled with `AGENT_SPEC_DEBUG=0`. Enabled by default.

### Call signatures

```
debug('tag', 'message')
debug('tag', 'message', {'key': 'value'})
debug('tag', 'message', lambda: {'key': expensive()})   # Python lazy
debug('tag', 'message', () => ({ key: expensive() }))   // TS lazy
```

### Emitting debug

- **Python (harness)**: `from lib import debug; debug("invoke", "sandbox ready", {"path": sandbox})`
- **Python (sandbox)**: `from _apc import debug; debug("test", "db initialized")`
- **TypeScript (sandbox)**: `import { debug } from "./_apc"; debug("test", "server started", { port: 3100 })`
- **Bash** (inline — no library needed):
  ```bash
  apc_debug() {
    [ "${AGENT_SPEC_DEBUG:-1}" = "0" ] && return
    local tag="$1" msg="$2" data="${3:-{\}}"
    local ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    printf '\033[2m[%s] [%s] %s\033[0m\n' "$ts" "$tag" "$msg" >&2
    local log="/tmp/agent-spec/${AGENT_SPEC_RUN_ID:-unknown}/events.jsonl"
    mkdir -p "$(dirname "$log")"
    printf '{"ts":"%s","level":"DEBUG","src":"%s","event":"debug:%s","msg":"%s","data":%s}\n' \
      "$ts" "$(basename "$0")" "$tag" "$msg" "$data" >> "$log"
  }
  ```

### Filtering debug events

```bash
jq 'select(.level=="DEBUG")' /tmp/agent-spec/<run_id>/events.jsonl
jq 'select(.event=="debug:verify")' /tmp/agent-spec/<run_id>/events.jsonl
```

## Reading

- Live: `python3 scripts/dashboard.py <run_id>`
- Stream (compact, no color): `python3 scripts/dashboard.py <run_id> --stream`
- Score: `python3 scripts/report.py --score <run_id>`
- Tokens: `python3 scripts/report.py --tokens <run_id>`
- Session tokens: `python3 scripts/report.py --tokens --session <session_id>`
- Compare: `python3 scripts/report.py --compare <run_id> <run_id>`
- Session report: `python3 scripts/report.py --session <session_id>`
- Full report: `python3 scripts/report.py --all`
- Baseline save: `python3 scripts/report.py --baseline save <run_id>`
- Baseline check: `python3 scripts/report.py --baseline check <run_id>`
- Config diff: `python3 scripts/dashboard.py --diff <run_id1> <run_id2>`
- Parallel status: `python3 scripts/dashboard.py --parallel <parallel_run_id>`
- Resources: `python3 scripts/system_monitor.py`
- Raw: `jq 'select(.event=="token_update")' /tmp/agent-spec/{run_id}/events.jsonl`
