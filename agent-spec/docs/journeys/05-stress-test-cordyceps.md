# Journey 5: Stress Test with Cordyceps

**Capabilities tested:** cordyceps injection, file deletion, stimuli injection, config swapping, parallel variants, agent resilience, cleanup

## Scenario

You want to test how robust your `.claude/` instructions are by mutating the environment. Delete files the agent expects, inject misleading files, swap configs, inject visual stimuli. If the instructions are good, the agent handles all of it.

## Steps

### 1. Delete additional files

```yaml
# target.yaml
delete_before_run:
  - main-file.ext
  - config.json
  - README.md
```

```bash
scripts/run-eval.sh my-project tuned
```

### 2. Inject misleading files

```bash
mkdir -p targets/my-project/inject
echo '{"wrong": "data"}' > targets/my-project/inject/config.json
scripts/run-eval.sh my-project tuned --inject targets/my-project/inject
```

### 3. Inject visual stimuli

```bash
scripts/tuning/capture-wireframe.sh "https://example.com" /tmp/stimuli/wireframe-1.png
scripts/tuning/parallel-invoke.sh my-project tuned --instances 3 \
  --stimuli-dir /tmp/stimuli --keep
```

### 4. Config swap matrix

```bash
scripts/tuning/parallel-invoke.sh my-project --configs baseline,tuned,empty
python3 scripts/reporting/report.py <id1> <id2> <id3> --group-by config
```

### 5. Empty .claude/ floor test

```bash
mkdir -p targets/my-project/configs/empty
touch targets/my-project/configs/empty/CLAUDE.md
scripts/run-eval.sh my-project empty
```

## Verification Checklist

### File deletion (delete_before_run)

- [ ] Files listed in `delete_before_run` are absent from sandbox before agent starts
- [ ] Files NOT listed are present (selective deletion, not wipe)
- [ ] Deleting a directory (not just a file) works
- [ ] Deleting a file that doesn't exist in source repo — no error, silent skip
- [ ] Source repo files unchanged after eval (deletion only in sandbox)
- [ ] Agent's events.jsonl shows it was asked to produce the deleted files
- [ ] Multiple files in delete list all deleted (not just first)
- [ ] File with spaces in name deleted correctly
- [ ] File in subdirectory deleted correctly (e.g., `src/main.ts`)
- [ ] Deleting `.claude/CLAUDE.md` from delete_before_run — does swap happen after delete? (it should — swap replaces the whole .claude/ dir)

### Injection (--inject)

- [ ] `--inject <dir>` copies all files from dir into sandbox root
- [ ] Injection happens AFTER delete_before_run (can inject replacements)
- [ ] Injected file overwrites sandbox file with same name
- [ ] Injected file in subdirectory creates that subdirectory in sandbox
- [ ] Injecting a `.claude/CLAUDE.md` — does it survive the swap? (it shouldn't — swap happens after inject)
- [ ] Order of operations: copy repo → delete files → inject files → swap .claude/ → inject emitters → run agent
- [ ] Verify order by injecting a file, deleting it in delete_before_run, and checking if it's present (it should be: inject is after delete)
- [ ] Empty inject directory — no error, no files copied
- [ ] Inject directory with 100 files — all copied
- [ ] Inject directory that doesn't exist — error message, not crash
- [ ] `--inject` flag passed through run-eval.sh to invoke.sh correctly
- [ ] Injected files appear in sandbox (verify with --keep and ls)

### Stimuli injection (--stimuli-dir)

- [ ] Each instance gets one file from stimuli-dir as `wireframe.png`
- [ ] Files distributed round-robin (instance 1 gets file 1, instance 2 gets file 2, etc.)
- [ ] With 3 stimuli and 3 instances — each gets a different file
- [ ] With 2 stimuli and 3 instances — instance 3 wraps to stimulus 1
- [ ] With 1 stimulus and 3 instances — all 3 get the same file
- [ ] With 0 stimuli (empty dir) — no wireframe.png injected, no error
- [ ] Stimuli files can be any format (PNG, JSON, TXT) — copied as wireframe.png regardless
- [ ] Temp inject directories (`/tmp/agent-spec-inject-*`) cleaned up after all runs complete
- [ ] `--keep` still preserves sandbox with wireframe.png inside
- [ ] Stimulus file larger than 10MB — copied without truncation

### Config swapping

- [ ] Swap replaces entire `.claude/` directory (not merge)
- [ ] If config has `.claude/rules/foo.md`, sandbox gets only that (not old rules)
- [ ] If config has no `.claude/` subdirectory (just CLAUDE.md), sandbox gets minimal .claude/
- [ ] Empty CLAUDE.md (0 bytes) — agent runs with no instructions (valid test)
- [ ] CLAUDE.md with `@import` references — imports resolve relative to sandbox
- [ ] Config with `rules/`, `skills/`, `agents/` subdirectories — all copied to sandbox .claude/
- [ ] Swap logged as `config_swapped` event with config path

### Screenshot capture (capture-wireframe.sh)

- [ ] `capture-wireframe.sh <url> <output>` produces a PNG file
- [ ] Default viewport: 1280x800
- [ ] Custom viewport: `capture-wireframe.sh <url> <out> 375 800` produces mobile-width
- [ ] Output directory created automatically if missing
- [ ] URL that 404s — screenshot shows error page (not script crash)
- [ ] URL that times out (>30s) — script exits with error, not hang
- [ ] URL with redirect — follows redirect and screenshots final page
- [ ] Output file with spaces in path — works correctly
- [ ] Running capture-wireframe.sh 3 times in parallel — no Playwright conflicts

### Parallel resilience

- [ ] 3 simultaneous cordyceps runs with different injections don't interfere
- [ ] Each sandbox is isolated (injection in sandbox A doesn't appear in sandbox B)
- [ ] Port collision: if one instance's server crashes, other instances unaffected
- [ ] One instance taking 10x longer than others — parallel-invoke.sh waits for all
- [ ] One instance crashing — other instances still complete and produce results
- [ ] Manifest file contains all run_ids (even from crashed instances, if they got far enough)

### Cleanup

- [ ] Inject temp dirs removed: `ls /tmp/agent-spec-inject-*` returns nothing after completion
- [ ] Sandboxes removed (unless --keep): `ls /tmp/claude/agent-spec-*` returns nothing
- [ ] Ports freed: `lsof -ti:3100 -ti:3101 -ti:3102` returns nothing
- [ ] PID registry cleaned: `/tmp/agent-spec-pids.txt` has no stale entries
- [ ] `--keep` preserves sandboxes but still cleans inject temp dirs and ports
- [ ] `/stop` cleans up everything including kept sandboxes

### Source repo protection

- [ ] Source repo checksum before == after (never modified)
- [ ] Source repo `.claude/` unchanged (swap only affects sandbox)
- [ ] `git status` in source repo shows no changes after any cordyceps operation
- [ ] Even a catastrophic agent error doesn't touch source repo
- [ ] Agent running `rm -rf /` inside sandbox — harness survives (sandbox is disposable)

### Edge cases

- [ ] Target with no delete_before_run, no setup, no inject — pure copy + swap + run
- [ ] Target with 20 files in delete_before_run — all deleted
- [ ] Inject a file with same name as a file in delete_before_run — inject wins (it runs after)
- [ ] Inject + stimuli at same time — both applied (inject first, then stimuli via separate mechanism)
- [ ] Config directory that doesn't exist — error before any sandbox creation (fail fast)
- [ ] Source repo that's a symlink — cp -a follows symlink correctly
- [ ] Source repo with `.git/` directory — copied to sandbox (agent may use git)
- [ ] Source repo with `node_modules/` — copied (large but correct; setup commands may need it)
