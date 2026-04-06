# agent-spec vs Model-Level Reasoning Research

## The Model-Level Topics

These are all about improving **the model itself** — changing weights, training loops, inference strategies:

- **Inference-time scaling / reasoning models**: More compute at inference (chain-of-thought, search, verification) to get better answers from the same weights
- **Self-refinement**: Model critiques and revises its own output during generation
- **Reinforcement learning**: Training signal from rewards (outcomes) rather than demonstrations
- **Distillation**: Compressing a large model's behavior into a smaller one

All of these change or exploit **what happens inside the model**.

## What agent-spec Does (Instruction-Level)

- Takes a fixed model as-is — never touches weights, training, or inference strategy
- Asks: given this model, what **instructions, rules, and structure** around it produce the best agent behavior?
- Measures with tokens-to-correctness: did the agent solve the task, and how efficiently?
- Iterates on the `.claude/` directory (the instruction layer), not the model

**The analogy**: They're improving the athlete. We're improving the playbook.

A reasoning model with bad instructions still flails. A weaker model with precise instructions can outperform it on structured tasks. agent-spec is empirically testing that second claim — and the bug-squasher work already showed haiku + good instructions beating sonnet with default instructions.

## Where They Overlap

Self-refinement is the closest cousin. agent-spec's `/iterate` skill does external self-refinement — run, score, diagnose, fix instructions, repeat. But it's refining the *prompt environment*, not the model's internal reasoning chain.

## The Two-Chat Workflow

Developing `.claude/` instructions is itself an agent-assisted process, but it works best with two separate chats:

1. **The context chat** — holds the full picture of what you're trying to achieve, reviews experiment results, and evolves the `.claude/` instructions. This chat accumulates understanding over time and writes handoff documents when it's time to test changes.
2. **The execution chat** — picks up handoffs from the context chat and runs experiments, evals, or coding tasks against the current instructions. Its results flow back to the context chat for diagnosis.

This separation matters because the context chat stays focused on *why* instructions should change, while the execution chat stays disposable — it runs, produces signal, and gets replaced. Mixing both into one chat degrades the context chat's accumulated understanding with execution noise, and makes the execution chat too cautious to be disposable.

## The Short Version

Those topics ask "how do we make the model smarter?" agent-spec asks "how do we make the context around the model smarter?" Both matter, and they compound.
