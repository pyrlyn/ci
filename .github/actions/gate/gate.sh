#!/usr/bin/env bash
# Gate over a `needs` JSON (NEEDS): fail only when a job's result is `failure`. `success`,
# `skipped` and `cancelled` pass. An empty `needs` is a wiring error and fails.
set -euo pipefail
fail=0
count=0
while IFS=$'\t' read -r name result; do
  count=$((count + 1))
  echo "$name: $result"
  if [ "$result" = "failure" ]; then
    echo "::error title=gate::$name failed"
    fail=1
  elif [ "$result" != "success" ]; then
    echo "  ($result: does not fail the gate)"
  fi
done < <(jq -r 'to_entries[] | [.key, .value.result] | @tsv' <<<"$NEEDS")
if [ "$count" -eq 0 ]; then
  echo "::error title=gate::no jobs to gate on (empty needs)"
  exit 1
fi
exit "$fail"
