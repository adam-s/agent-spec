# Fix Safety

Before implementing any fix, verify your full diagnosis by answering:

1. **What value or state am I changing?** Name the specific variable, header, field, or condition.
2. **Who reads this downstream?** Search for every consumer of that value. If you are removing or moving something, every dependent must still get what it needs.
3. **Does my fix handle all sources?** If the value can come from multiple places (function return, header, parameter, config), your fix must account for each source — not just the one in the current code path.

If you cannot answer all three, your diagnosis is incomplete. Go back and read more code before changing anything.

After implementing, re-read your diff and check: did you break any consumer you identified in step 2?
