# Submodules

Third-party repositories used as eval targets or config sources.

## Setup

After cloning:

```bash
git submodule update --init
```

Or clone with submodules included:

```bash
git clone --recurse-submodules <repo-url>
```

## Contents

| Submodule | Source | Purpose |
|-----------|--------|---------|
| `intercept/` | [adam-s/intercept](https://github.com/adam-s/intercept) | Eval target |
| `alphadidactic/` | [adam-s/alphadidactic](https://github.com/adam-s/alphadidactic) | Eval target |
| `skills/` | [anthropics/skills](https://github.com/anthropics/skills) | Claude Code skills library |
