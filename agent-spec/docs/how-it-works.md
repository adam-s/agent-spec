# How agent-spec Works

## The Big Idea

agent-spec builds and tests `.claude/` instruction sets — the files that tell a Claude Code agent how to approach a task. The end product is a portable `.claude/` directory that anyone can drop into a repo and use.

The bug-squasher is the first example: a `.claude/` directory that teaches Claude Code how to debug and fix bugs in any open-source project.

## Three Levels

agent-spec operates as a recursive system with three nested levels.

```mermaid
graph TD
    L0["Level 0: Orchestrator<br/>(You + agent-spec)"]
    L1["Level 1: Sub-agents<br/>(Disposable Claude instances)"]
    L2["Level 2: The Product<br/>(.claude/ directory)"]

    L0 -->|launches| L1
    L0 -->|improves| L2
    L2 -->|injected into| L1
    L1 -->|behavior is signal for| L0

    style L0 fill:#2d5a3d,stroke:#4a9,color:#fff
    style L1 fill:#4a4a6a,stroke:#77a,color:#fff
    style L2 fill:#6a3d2d,stroke:#a74,color:#fff
```

| Level | What it is | What it does |
|-------|-----------|--------------|
| **Level 0** | You + agent-spec | Launches agents, scores results, diagnoses failures, improves instructions |
| **Level 1** | Disposable Claude instances in `/tmp` workspaces | Does the actual work (e.g., fixes a bug). Code is throwaway — behavior is the signal |
| **Level 2** | The `.claude/` directory (e.g., bug-squasher) | The product. Must be self-sufficient — the agent reading it never knows agent-spec exists |

## What Happens During an Eval Run

```mermaid
sequenceDiagram
    participant Human as You (Human)
    participant L0 as Level 0 (Orchestrator)
    participant Workspace as /tmp workspace
    participant L1 as Level 1 (Sub-agent)

    Human->>L0: "Run the botocore challenge"
    L0->>Workspace: Clone repo at buggy commit
    L0->>Workspace: Inject .claude/ from config (bug-squasher)
    L0->>L1: Launch Claude Code in workspace with prompt
    Note over L1: Agent reads .claude/CLAUDE.md<br/>Follows debugging strategy:<br/>1. Reproduce<br/>2. Narrow from symptom<br/>3. Understand + fix<br/>4. Verify
    L1->>Workspace: Writes fix (code changes)
    L0->>Workspace: Run verify.sh
    Workspace-->>L0: RESULT: PASS or FAIL
    L0-->>Human: Report: PASS/FAIL, token count, time
```

## Where the Config Comes From

The bug-squasher `.claude/` directory lives as a standalone product at `bug-squasher/.claude/`. The eval symlinks to it:

```mermaid
graph LR
    Product["bug-squasher/.claude/<br/>(the product)"]
    Symlink["evals/bug-squashing/configs/bug-squasher"]
    Workspace["/tmp workspace/.claude/"]

    Product ---|symlink| Symlink
    Symlink ---|copied into| Workspace

    style Product fill:#6a3d2d,stroke:#a74,color:#fff
    style Symlink fill:#4a4a4a,stroke:#888,color:#fff
    style Workspace fill:#4a4a6a,stroke:#77a,color:#fff
```

This separation matters: the config is **not** an eval artifact. It's the real product. Evals just test it.

## The Self-Improvement Loop

When an eval fails, the failure is signal about the instructions, not about the eval.

```mermaid
graph TD
    A[Run eval against known bug] --> B{Did it pass?}
    B -->|Yes| C[Record baseline:<br/>tokens, time, pass]
    B -->|No| D[Diagnose: Why did it fail?]
    D --> E{What kind of failure?}
    E -->|Instruction gap| F[Improve .claude/ instructions]
    E -->|Eval defect| G[Fix the eval scaffolding]
    E -->|Model limitation| H[Add hints or escalate]
    F --> I[Delete failed artifacts, run again]
    G --> I
    H --> I
    I --> A

    style A fill:#2d5a3d,stroke:#4a9,color:#fff
    style C fill:#2d5a3d,stroke:#4a9,color:#fff
    style F fill:#6a3d2d,stroke:#a74,color:#fff
```

The key metric is **tokens-to-correctness** — not just pass/fail, but how efficiently the agent got there.

## Using It Yourself

The whole point of Level 2 being self-sufficient is that you can use it directly, without agent-spec:

```mermaid
graph LR
    A["Clone any repo"] --> B["Drop in bug-squasher/.claude/"]
    B --> C["Open Claude Code"]
    C --> D["Paste the bug report"]
    D --> E["Agent debugs and fixes it"]

    style E fill:#2d5a3d,stroke:#4a9,color:#fff
```

That's it. The agent reads the `.claude/CLAUDE.md`, follows the debugging strategy (reproduce, narrow, understand, fix, verify), and produces a fix. It doesn't know or care that agent-spec trained those instructions.

## Configs as Experiments

Different configs represent different instruction strategies. You can A/B test them:

```mermaid
graph TD
    Challenge["Same bug<br/>(e.g., botocore streaming issue)"]
    A["Config A: baseline"]
    B["Config B: token-efficient"]
    C["Config C: bug-squasher"]

    Challenge --> A
    Challenge --> B
    Challenge --> C

    A --> RA["PASS — 45,000 tokens"]
    B --> RB["PASS — 28,000 tokens"]
    C --> RC["PASS — 31,000 tokens"]

    style Challenge fill:#4a4a6a,stroke:#77a,color:#fff
    style RB fill:#2d5a3d,stroke:#4a9,color:#fff
```

Same bug, different instructions, compare results. This is how you know which instruction strategies actually work — not by reading them and guessing, but by measuring.

## Summary

| Concept | In plain terms |
|---------|---------------|
| **agent-spec** | A training harness for `.claude/` instruction sets |
| **Level 0** | The coach watching game film |
| **Level 1** | The players on the field |
| **Level 2** | The playbook the players follow |
| **Eval** | A known challenge with a deterministic pass/fail check |
| **Config** | A `.claude/` directory variant to test |
| **Tokens-to-correctness** | The headline metric — how much work to get the right answer |
| **Bug-squasher** | The first product — a `.claude/` that teaches debugging |
