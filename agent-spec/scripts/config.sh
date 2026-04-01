#!/usr/bin/env bash
# config.sh — All constants for agent-spec. Source this file, never hardcode these values.

# Port allocation
PORT_MIN=3100
PORT_MAX=3110

# Timeouts
TIMEOUT_DEFAULT=600  # seconds

# Regression thresholds
REGRESSION_COST_THRESHOLD=50   # percent increase
REGRESSION_TOKEN_THRESHOLD=50  # percent increase

# Paths
SANDBOX_ROOT="/tmp/claude/agent-spec"
RUN_ROOT="/tmp/agent-spec"
PID_FILE="/tmp/agent-spec-pids.txt"

# Agent defaults
DEFAULT_MODEL="claude-sonnet-4-6"
DEFAULT_BUDGET="2.00"

# Resolve project root (works from any script location)
if [[ -z "${PROJECT_DIR:-}" ]]; then
  PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
