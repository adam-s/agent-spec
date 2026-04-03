# Bug-Squashing Recursive Training Loop

## Overview

A self-improving system that trains a bug-squashing agent using known deterministic results. GitHub bugs with committed fixes serve as ground truth. The loop tunes the agent's instructions — not its code. Every improvement must be generalized.

## Architecture

Three levels, matching agent-spec's recursive model:

```mermaid
graph TD
    L0[Level 0: Orchestrator<br/>agent-spec + human]
    L1[Level 1: Bug-Squasher Agent<br/>disposable, follows protocol]
    L2[Level 2: Bug-Squasher Instructions<br/>.claude/agents/bug-squasher.md<br/>THE PRODUCT]
    REV[Reviewer Agent<br/>has the answer key]

    L0 -->|launches| L1
    L0 -->|launches| REV
    L1 -->|reads| L2
    L1 -->|produces| FIX[Attempted Fix]
    REV -->|reads| FIX
    REV -->|reads| TRUTH[Known Fix + Issue]
    REV -->|produces| FINDINGS[Generalized Findings]
    L0 -->|applies| FINDINGS
    FINDINGS -->|improves| L2

    style L2 fill:#f9f,stroke:#333
    style FIX fill:#ff9,stroke:#333
    style TRUTH fill:#9f9,stroke:#333
    style FINDINGS fill:#9ff,stroke:#333
```

**What is throwaway:** Level 1 agents, their attempted fixes, reviewer instances, workspaces.

**What is permanent:** Level 2 instructions (`.claude/agents/bug-squasher.md`), generalized findings committed to `.claude/`.

## The Iteration Loop

```mermaid
sequenceDiagram
    participant O as Orchestrator (L0)
    participant S as Bug-Squasher (L1)
    participant R as Reviewer
    participant I as Instructions (L2)

    O->>O: Select bug from TRAINING set
    O->>O: Checkout repo at buggy commit
    O->>S: Launch in workspace<br/>(bug description + repo, NO fix)
    S->>I: Read bug-squashing protocol
    S->>S: Diagnose and attempt fix
    S-->>O: Fix attempt + event trace

    O->>R: Launch with answer key<br/>(issue, discussion, known fix, agent's fix)
    R->>R: Compare agent fix vs known fix
    R->>R: Extract GENERALIZED findings only
    R-->>O: Structured findings

    O->>O: Apply findings to instructions
    O->>O: Run held-out validation
    alt Held-out improves
        O->>I: Commit instruction changes
    else Held-out unchanged or worse
        O->>O: Revert — finding was overfit
    end

    O->>O: Next iteration
```

## The Generalization Gate

The reviewer has the answer key, which creates an overfitting risk. Every finding must pass the generalization filter before it can modify instructions.

```mermaid
flowchart LR
    F[Finding from Reviewer]
    T1{Names a library,<br/>error type, or domain?}
    T2{Would help on a<br/>completely different project?}
    T3{Principle or recipe?}
    V{Held-out validation:<br/>pass rate improved?}

    F --> T1
    T1 -->|Yes| REJECT[Reject: overfit]
    T1 -->|No| T2
    T2 -->|No| REJECT
    T2 -->|Yes| T3
    T3 -->|Recipe| REJECT
    T3 -->|Principle| APPLY[Apply to instructions]
    APPLY --> V
    V -->|No| REVERT[Revert change]
    V -->|Yes| COMMIT[Commit to .claude/]

    style REJECT fill:#f99
    style COMMIT fill:#9f9
    style REVERT fill:#ff9
```

## Budget Ladder Integration

Same bug, same instructions, different budgets. Measures cost-to-correctness — the primary metric.

```mermaid
graph LR
    BUG[Bug N] --> B1[$1.00 budget]
    BUG --> B2[$2.00 budget]
    BUG --> B3[$5.00 budget]
    BUG --> B4[$10.00 budget]

    B1 --> R1[FAIL / PASS<br/>cost: $0.92]
    B2 --> R2[FAIL / PASS<br/>cost: $1.74]
    B3 --> R3[PASS<br/>cost: $3.20]
    B4 --> R4[PASS<br/>cost: $4.15]

    R1 & R2 & R3 & R4 --> M[Cost-to-correctness curve]

    style M fill:#9ff
```

As instructions improve, the curve shifts left — bugs get fixed at lower budgets.

## Train/Held-Out Split

```mermaid
graph TD
    BENCH[Bug Benchmark<br/>N GitHub bugs with known fixes]
    BENCH --> TRAIN[Training Set ~60%<br/>Reviewer sees bugs + fixes]
    BENCH --> HELD[Held-Out Set ~40%<br/>Reviewer NEVER sees these]

    TRAIN --> LOOP[Iteration Loop<br/>Extract findings]
    LOOP --> APPLY[Apply to instructions]
    APPLY --> VAL[Validate on held-out]
    VAL -->|Improved| KEEP[Keep changes]
    VAL -->|No change| DROP[Revert: overfit]

    style HELD fill:#f9f,stroke:#333
    style TRAIN fill:#9f9,stroke:#333
```

## Convergence Criteria

The loop converges when:

1. **Pass rate on held-out set** stops improving across iterations
2. **Cost-to-correctness** on held-out set stabilizes
3. **Instruction changes** become smaller (diminishing returns)

Measured per iteration:

| Metric | How |
|--------|-----|
| Training pass rate | % of training bugs fixed |
| Held-out pass rate | % of held-out bugs fixed (the real score) |
| Avg cost to fix | Mean token cost across passing runs |
| Instruction delta | Lines changed in bug-squasher.md |

## What Each Agent Sees

| | Bug-Squasher (L1) | Reviewer |
|---|---|---|
| Bug description | Yes | Yes |
| Repo at buggy commit | Yes | Yes |
| GitHub issue/discussion | No | Yes |
| Known fix commit | No | Yes |
| Agent's attempted fix | (produces it) | Yes |
| Bug-squasher instructions | Yes (follows them) | Yes (evaluates them) |

## Workspace Setup

For each bug in the benchmark:

1. Clone the repo at the **parent of the fix commit** (the buggy state)
2. Place bug description in `prompt.md` (from the GitHub issue, sanitized of fix hints)
3. `verify.sh` runs the repo's own test suite
4. The known fix commit is stored separately for the reviewer, never in the workspace

## Next Steps

1. Source 8-12 GitHub bugs (post-May 2025, with fix commits and tests)
2. Split into training (5-7) and held-out (3-5)
3. Build `.claude/agents/bug-squasher.md` — initial protocol
4. Build `.claude/agents/bug-reviewer.md` — structured reviewer with generalization enforcement
5. Build `.claude/skills/bug-squashing-loop/SKILL.md` — orchestrator
6. Run first iteration, measure baseline
