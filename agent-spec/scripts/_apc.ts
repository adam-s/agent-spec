/**
 * Lightweight APC emitter for TypeScript sandboxes. Zero dependencies.
 */

import { appendFileSync, mkdirSync } from "fs";
import { dirname, basename } from "path";

const RUN_ID = process.env.AGENT_SPEC_RUN_ID ?? "unknown";
const LOG = `/tmp/agent-spec/${RUN_ID}/events.jsonl`;

export function log(
  level: string,
  event: string,
  msg: string,
  data?: Record<string, unknown>
) {
  mkdirSync(dirname(LOG), { recursive: true });
  const entry = {
    ts: new Date().toISOString(),
    level,
    src: basename(process.argv[1] ?? "unknown"),
    event,
    msg,
    data: data ?? {},
  };
  appendFileSync(LOG, JSON.stringify(entry) + "\n");
}

const DEBUG_ENABLED = (process.env.AGENT_SPEC_DEBUG ?? "1") !== "0";

export function debug(
  tag: string,
  msg: string,
  data?: (() => Record<string, unknown>) | Record<string, unknown>
) {
  if (!DEBUG_ENABLED) return;
  const resolved = typeof data === "function" ? data() : data;
  const ts = new Date().toISOString().slice(11, 23);
  let line = `[${ts}] [${tag}] ${msg}`;
  if (resolved && Object.keys(resolved).length > 0) {
    line += `  ${JSON.stringify(resolved)}`;
  }
  process.stderr.write(`\x1b[2m${line}\x1b[0m\n`);
  log("DEBUG", `debug:${tag}`, msg, resolved ?? {});
}
