# Token Efficiency Eval

Do .claude/ instruction strategies affect tokens-to-correctness?

## Background

Multiple open-source projects claim to reduce Claude Code token usage through CLAUDE.md instructions. A [prior benchmark](https://github.com/adam-s/testing-claude-agent) tested 6 config variants across 3 challenges but with only 1-2 runs per config -- not enough to separate signal from run-to-run variance.

This eval reproduces that experiment with agent-spec's sandbox isolation and repeated trials.

## Experimental Design

### Why 3 challenges at different difficulty levels

Research on LLM benchmarking shows that tasks must land in the "discriminating zone" to differentiate instruction strategies. If every config passes every task, the only measurable difference is instruction file size (a ceiling effect).

- **csv-reporter** (easy): Single-file Python, stdlib only. All configs should pass first attempt. Establishes the token floor.
- **sqlite-window-queries** (medium): Single-file Node.js with SQL. All configs should pass. Slightly more complex.
- **hono-websocket-counter** (hard): Multi-file server with HTML, WebSockets, shared state, and broadcast. Requires iteration -- the agent's first approach may not work. This is where instruction quality can plausibly affect retries and token consumption.

### Why 6 configs testing different .claude/ structures

The original experiment tested not just CLAUDE.md content but .claude/ **architecture** -- whether rules/, agents/, hooks/, and skills/ directories change agent behavior.

| Config | Structure | What it tests |
|--------|-----------|---------------|
| A-baseline | `CLAUDE.md` (1 line) | Control -- minimal instructions |
| B-token-efficient | `CLAUDE.md` (12 lines) | Flat rules: no preamble, simple code |
| C-structured | `CLAUDE.md` + `rules/` + `agents/` + `reference/` | Multi-file with MUST/NEVER rules |
| D-workflow | `CLAUDE.md` + `rules/` + `skills/` + `hooks/` | Sequential gates and verification hooks |
| E-hybrid | `CLAUDE.md` + `rules/` + `agents/` | Mixed: inline rules + components |
| F-drona23 | `CLAUDE.md` (61 lines) | Full [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient) |

## Running

From `agent-spec/agent-spec/`:

```bash
# Verify setup
python3 scripts/cli.py list

# Sequential smoke test (one config, all 3 challenges)
python3 scripts/cli.py run token-efficiency A-baseline

# After smoke test passes, run configs in parallel with port isolation
# Each config gets its own port range via the harness
python3 scripts/cli.py run token-efficiency B-token-efficient
python3 scripts/cli.py run token-efficiency C-structured
# ... etc

# For 5 reps: repeat above sequence 5 times (30 cli.py runs = 90 challenge runs)

# Generate results
python3 scripts/summarize.py token-efficiency --filter-eval
```

## Interpreting Results

| Column | Meaning |
|--------|---------|
| Runs | Completed runs for this config |
| Pass | Runs that passed all tests |
| Avg Tokens | Mean input + output tokens (headline metric) |
| Std | Standard deviation across runs |
| Avg Cost | Mean USD cost per run |
| Delta | Difference from baseline (negative = fewer tokens) |

**What to look for:**

1. **Easy challenges (csv-reporter, sqlite-window-queries):** All configs should pass. Token differences here are mostly instruction overhead -- configs with more text in .claude/ will use more input tokens per turn. A config that somehow uses fewer tokens here is genuinely more efficient.

2. **Hard challenge (hono-websocket-counter):** This is where the signal lives. Look for:
   - Pass rate differences (does a config help the agent succeed more often?)
   - Token variance (does a config produce more consistent results?)
   - Token count on passing runs (does a config help the agent find the solution faster?)

3. **Structural vs flat:** Compare C-structured and D-workflow (multi-file .claude/) against B-token-efficient and F-drona23 (flat CLAUDE.md). Does .claude/ architecture matter beyond CLAUDE.md content?

## Known Limitations

1. **Three challenges.** Enough for directional signal across easy/medium/hard. Not conclusive for all task types (debugging, refactoring, multi-file).
2. **Model-specific.** Results are for claude-sonnet-4-6. Override with `--model`.
3. **Cache effects.** Interleave config order across repetitions to distribute prompt caching evenly.
4. **Bun dependency.** hono-websocket-counter requires Bun. The setup.sh falls back to npm but tests use Bun's WebSocket.
