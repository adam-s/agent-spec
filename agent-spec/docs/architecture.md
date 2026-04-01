# Architecture

agent-spec is a test harness for `.claude/` directories. It launches Claude agents in disposable sandboxes, scores their output deterministically, and uses failures as signal to improve the instructions.

## System Overview

```mermaid
graph TB
    subgraph "Level 0: Orchestrator"
        CLI[agent-spec CLI]
        INVOKE[invoke.py]
        PARALLEL[parallel.py]
        ITERATE[/iterate skill]
    end

    subgraph "Level 1: Sandboxed Agents"
        S1[Sandbox 1<br>/tmp/claude/agent-spec-abc/]
        S2[Sandbox 2<br>/tmp/claude/agent-spec-def/]
        S3[Sandbox N<br>/tmp/claude/agent-spec-ghi/]
    end

    subgraph "Level 2: The Product"
        CLAUDE[target/.claude/<br>CLAUDE.md, rules/, skills/]
    end

    CLI --> INVOKE
    CLI --> PARALLEL
    PARALLEL --> INVOKE
    ITERATE --> PARALLEL
    INVOKE -->|copy source + swap .claude/| S1
    INVOKE -->|copy source + swap .claude/| S2
    INVOKE -->|copy source + swap .claude/| S3
    CLAUDE -.->|read by agents inside| S1
    CLAUDE -.->|read by agents inside| S2
    CLAUDE -.->|read by agents inside| S3
    S1 -->|PASS/FAIL| ITERATE
    S2 -->|PASS/FAIL| ITERATE
    S3 -->|PASS/FAIL| ITERATE
    ITERATE -->|diagnose + fix| CLAUDE
```

## Run Lifecycle

A single evaluation follows this sequence:

```mermaid
sequenceDiagram
    participant User
    participant CLI as agent-spec CLI
    participant Invoke as invoke.py
    participant Sandbox as /tmp sandbox
    participant Agent as claude -p
    participant Verify as verify.sh

    User->>CLI: agent-spec run target [config]
    CLI->>Invoke: resolve target + config
    Invoke->>Sandbox: copy source repo
    Invoke->>Sandbox: delete files (cordyceps)
    Invoke->>Sandbox: swap .claude/ with config
    Invoke->>Sandbox: run setup commands
    Invoke->>Agent: claude -p <prompt>
    Note over Agent,Sandbox: Agent works inside sandbox<br>reads .claude/ instructions<br>produces/modifies code
    Agent-->>Invoke: exit + output.json
    Invoke->>Verify: bash verify.sh
    Verify-->>Invoke: RESULT: PASS or FAIL
    Invoke-->>CLI: run_id, score, cost
    CLI-->>User: ✓ target/config: PASS (38s) $0.04
```

## Iteration Loop

The `/iterate` skill automates the feedback loop:

```mermaid
flowchart TD
    START([Start]) --> LAUNCH[Launch N parallel agents<br>against target with config]
    LAUNCH --> SCORE{All pass?}
    SCORE -->|Yes| CONVERGE([Converged])
    SCORE -->|No| OBSERVE[Read failures:<br>verify.sh output, produced code,<br>events.jsonl]
    OBSERVE --> DIAGNOSE[Classify each failure<br>into findings table]
    DIAGNOSE --> FIX[Fix target/.claude/<br>based on findings]
    FIX --> DEPTH{Max depth<br>reached?}
    DEPTH -->|No| LAUNCH
    DEPTH -->|Yes| STOP([Not converged])
```

## Config Resolution

Configs are `.claude/` directories that get swapped into the sandbox. They resolve with target-specific taking priority:

```mermaid
flowchart LR
    REQ[Requested config name] --> CHECK{Exists in<br>target/configs/?}
    CHECK -->|Yes| USE_TARGET[Use target-specific config]
    CHECK -->|No| CHECK2{Exists in<br>_shared/configs/?}
    CHECK2 -->|Yes| USE_SHARED[Use shared config]
    CHECK2 -->|No| ERROR[ERROR: config not found<br>Available: ...]
```

## Cordyceps Injection

The sandbox is a disposable copy. Before the agent sees it, the harness can modify anything:

```mermaid
flowchart LR
    SOURCE[Source repo] -->|copy| SANDBOX[Sandbox copy]
    SANDBOX --> DELETE[Delete files<br>agent must recreate them]
    DELETE --> INJECT[Inject files<br>emitters, test data]
    INJECT --> SWAP[Swap .claude/<br>with config variant]
    SWAP --> SETUP[Run setup commands<br>npm install, etc.]
    SETUP --> READY[Ready for agent]
```

The original repo is never modified. The name comes from the [cordyceps fungus](https://en.wikipedia.org/wiki/Cordyceps) — the harness takes over its host.

## Directory Structure

```
agent-spec/
├── scripts/           # Core harness scripts
│   ├── cli.py         # Unified entry point
│   ├── invoke.py      # Single run: sandbox + agent + verify
│   ├── parallel.py    # Multi-run: A/B tests, benchmarks
│   ├── dashboard.py   # Live monitoring
│   ├── report.py      # Comparison reports
│   └── lib.py         # Shared utilities
├── targets/           # Test fixtures
│   ├── _shared/       # Configs shared across targets
│   │   └── configs/
│   │       ├── baseline/
│   │       ├── structured/
│   │       └── ...
│   ├── csv-reporter/
│   │   ├── target.yaml
│   │   ├── prompt.md
│   │   ├── verify.sh
│   │   └── configs/
│   │       └── tuned/
│   └── ...
├── docs/              # Documentation
│   ├── architecture.md
│   ├── getting-started.md
│   ├── cli-reference.md
│   └── writing-targets.md
├── results/           # Archived run results (git-ignored)
└── .claude/           # agent-spec's own instructions
    ├── CLAUDE.md
    ├── rules/
    ├── skills/
    └── reference/
```
