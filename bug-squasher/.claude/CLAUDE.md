# Bug Squasher

You are debugging a bug in an open-source project. The workspace contains the project source code at a commit where the bug is present.

## Debugging strategy

1. **Reproduce first.** Write a minimal script that triggers the bug. Confirm you can see the failure before reading any source code. If the bug is a hang, use `timeout` to make it observable.

2. **Narrow from the symptom.** Use the error message, stack trace, or hang location to identify the specific function and file. Read only that code — do not explore broadly.

3. **Understand the code, then fix.** Read the function that contains the bug. If the bug is in one code path (e.g. non-seekable streams) but an equivalent code path works (e.g. seekable streams), read the working path first to understand the full intended pattern. Apply the same pattern to the broken path — don't invent a different fix. Before changing a value, header, or variable, trace who reads it downstream — if you remove or move something, make sure anything that depends on it still gets what it needs.

4. **Verify.** Run the project's test suite as described in the prompt. Then re-run your reproduction script to confirm the specific bug is fixed.

## When you're stuck

If reproduction doesn't reveal the cause:
- Instrument the suspected code path — add print statements at function entry/exit to see actual inputs and outputs. Label clearly so you can trace the flow:
  - Python: `print(f"ClassName.method: {input=} {output=}")`
  - JavaScript: `console.log("ClassName.method:", { input, output })`
  - Go: `log.Printf("ClassName.Method: input=%v output=%v", input, output)`
- Isolate the unit — call the suspected function directly with controlled inputs, outside the full call chain.
- Test boundaries — try empty, None/null, zero, single-element, and maximum inputs. Many bugs only manifest at edges.

If you can't identify the right file:
- Read the full stack trace bottom-up. The deepest application frame (not library frame) is where to start.
- Reduce the reproduction — strip your script to the absolute minimum that still triggers the bug. Each thing you remove rules out a code path.

If your fix doesn't work:
- Diff your change against the original — are you editing the right location?
- Check if the code path you fixed is actually the one being executed. Instrument to confirm.

## After fixing

- After fixing, search the surrounding code for fallback paths, try/except blocks, or workarounds that handle the same case your fix addresses. If your fix makes them redundant, **remove them** — redundant fallbacks can silently bypass the validation or logic your fix introduced.
- Test edge cases around your fix — not just the reported case. If you changed validation logic, test invalid inputs too. If you changed a conditional, test the boundary.

## What to avoid

- Do not explore git history to find the answer. The fix must come from understanding the code, not from reading past commits.
- Do not read files speculatively. Every file you open should be justified by the reproduction or stack trace.
- Do not modify test files unless the prompt explicitly says to.
