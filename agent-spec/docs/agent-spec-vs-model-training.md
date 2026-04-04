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

## The Short Version

Those topics ask "how do we make the model smarter?" agent-spec asks "how do we make the context around the model smarter?" Both matter, and they compound.
