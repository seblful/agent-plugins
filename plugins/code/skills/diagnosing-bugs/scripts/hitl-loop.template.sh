#!/usr/bin/env bash
# Human-in-the-loop reproduction loop.
# The agent copies this file to a scratch directory and edits the steps there —
# never in place. The user runs the copy in their own terminal
# (in Claude Code: `! bash <path>`); the agent's shell has no terminal to prompt in.
#
# Usage:
#   bash hitl-loop.sh [results-file]    # default: hitl-results.env beside the script
#
# Two helpers:
#   step "<instruction>"          → show instruction, wait for Enter
#   capture VAR "<question>"      → show question, read one line into VAR
#
# Every capture is printed and appended to the results file as KEY=VALUE,
# under a "# run <timestamp>" header, for the agent to read.

set -euo pipefail

RESULTS="${1:-$(dirname "$0")/hitl-results.env}"
CAPTURED=()

no_input() {
  printf '\nNo input left. Run this in your own terminal (in Claude Code: ! bash %s).\n' "$0" >&2
  exit 2
}

step() {
  printf '\n>>> %s\n' "$1"
  IFS= read -r -p "    [Enter when done] " _ || no_input
}

capture() {
  local var="$1" question="$2" answer=""
  printf '\n>>> %s\n' "$question"
  IFS= read -r -p "    > " answer || [[ -n "$answer" ]] || no_input
  printf -v "$var" '%s' "$answer"
  CAPTURED+=("$var")
}

# --- edit below ---------------------------------------------------------

step "Start the system and get to the point just before the bug."

capture REPRODUCED "Perform the action that triggers the bug. Did it happen? (y/n)"

capture SYMPTOM "Paste the exact error or wrong output (or 'none'):"

# --- edit above ---------------------------------------------------------

printf '# run %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" >> "$RESULTS"
printf '\n--- Captured ---\n'
for var in ${CAPTURED[@]+"${CAPTURED[@]}"}; do
  printf '%s=%s\n' "$var" "${!var}" | tee -a "$RESULTS"
done
printf '\nAppended to %s\n' "$RESULTS"
