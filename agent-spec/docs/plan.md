# Plan

## Isolation Strategy

Instead of git worktrees (which require the gitignore-swap hack from testing-claude-agent), we will use a test definition/configuration that copies all necessary files into a folder under `tmp/` and runs tests from there. This decouples test isolation from git entirely — no worktree creation, no branch cleanup, no gitignore toggling.
