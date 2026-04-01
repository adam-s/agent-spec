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
