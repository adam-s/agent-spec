# Bug Catalog

This catalog documents **Claude Code agent behavioral bugs** — cases where the coding agent consistently does something wrong that requires explicit `.claude/` instructions to correct. These are training gaps in the model's behavior, not script or harness bugs.

Script bugs that get fixed in code do not belong here. If the fix is a code change (to a bash script, Python file, etc.), the fix lives in the commit and the bug does not need a catalog entry. This catalog is only for behaviors that persist across runs because the agent needs to be *told* not to do them.

## Entry format

```markdown
## BNN: Short name

**Behavior:** What the agent does wrong (the recurring pattern)
**Impact:** What breaks or degrades as a result
**Instruction fix:** What to put in `.claude/` to correct the behavior
```

---
