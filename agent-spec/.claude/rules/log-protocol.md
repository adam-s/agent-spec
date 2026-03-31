# Log Protocol

All events are JSONL lines appended to `/tmp/agent-spec/{run_id}/events.jsonl`.

## Format

```json
{"ts":"ISO8601","level":"INFO","src":"script.sh","event":"event_name","msg":"text","data":{}}
```

## Levels

`DEBUG`, `INFO`, `WARN`, `ERROR`, `METRIC`

## Well-Known Events

- `agent_started` — target, config, model, budget
- `agent_complete` — exit_code, duration_ms
- `agent_error` — exit_code, duration_ms, stderr_tail
- `token_update` — input, output, cache_create, cache_read, cost_usd, turns
- `resource_snapshot` — cpu, mem, disk_free_gb
- `test_passed` / `test_failed` — test_name
- `score` — result (PASS/FAIL)

## Emitting

- **Bash**: `source scripts/apc/lib.sh` then `apc_log LEVEL event "message" '{"key":"value"}'`
- **Python**: `from _apc import log; log("INFO", "event", "message", {"key": "value"})`
- **TypeScript**: `import { log } from "./_apc"; log("INFO", "event", "message", { key: "value" })`

## Reading

- Live: `scripts/cli/dashboard.sh <run_id>`
- Tokens: `scripts/reporting/tokens.sh <run_id>`
- Score: `scripts/reporting/score.sh <run_id>`
- Resources: `scripts/reporting/resources.sh <run_id>`
- Compare: `scripts/reporting/compare.sh <run_id> <run_id>`
- Full report: `python3 scripts/reporting/report.py --all`
- Raw: `jq 'select(.event=="token_update")' /tmp/agent-spec/{run_id}/events.jsonl`
