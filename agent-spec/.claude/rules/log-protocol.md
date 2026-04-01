# Log Protocol

All events are JSONL lines appended to `/tmp/agent-spec/{run_id}/events.jsonl`.

## Format

```json
{"ts":"ISO8601","level":"INFO","src":"script.sh","event":"event_name","msg":"text","data":{}}
```

## Levels

`DEBUG`, `INFO`, `WARN`, `ERROR`, `METRIC`

## Well-Known Events

### Lifecycle
- `sandbox_created` — sandbox, source
- `files_deleted` — files (comma-separated list)
- `files_injected` — from (inject directory path)
- `setup_command` — cmd, exit_code (each successful setup command)
- `setup_complete` — (all setup done)
- `setup_failed` — cmd, exit_code, stderr
- `empty_config` — config (WARN: agent has no instructions)
- `config_swapped` — config
- `sidecar_started` — pid, interval
- `agent_started` — target, config, model, budget, port
- `agent_complete` — exit_code, duration_ms
- `agent_error` — exit_code, duration_ms, stderr
- `agent_timeout` — timeout
- `run_terminated` — signal, run_id (external SIGTERM/SIGINT/SIGHUP)

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

### Metrics
- `token_update` — input, output, cache_create, cache_read, cost_usd, turns
- `resource_snapshot` — cpu, mem, disk_free_gb

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

- Live: `scripts/dashboard.py <run_id>`
- Tokens: `scripts/tokens.py <run_id>`
- Score: `scripts/score.py <run_id>`
- Resources: `scripts/resources.sh <run_id>`
- Compare: `python3 scripts/report.py --compare <run_id> <run_id>`
- Full report: `python3 scripts/report.py --all`
- Raw: `jq 'select(.event=="token_update")' /tmp/agent-spec/{run_id}/events.jsonl`
