#!/usr/bin/env bash
# Table test for .github/actions/gate/gate.sh: a `needs` JSON in, pass (0) or fail (1) out.
set -euo pipefail
script="$(cd "$(dirname "$0")/../.." && pwd)/.github/actions/gate/gate.sh"
fail=0
check() { # <name> <expected exit> <needs JSON>
  local got=0
  NEEDS="$3" bash "$script" >/dev/null 2>&1 || got=$?
  if [ "$got" = "$2" ]; then echo "ok   $1"; else echo "FAIL $1: exit $got, want $2"; fail=1; fi
}
check "all success" 0 '{"a":{"result":"success"},"b":{"result":"success"}}'
check "skipped passes" 0 '{"a":{"result":"success"},"b":{"result":"skipped"}}'
check "cancelled passes" 0 '{"a":{"result":"cancelled"},"b":{"result":"success"}}'
check "all cancelled passes" 0 '{"a":{"result":"cancelled"},"b":{"result":"cancelled"}}'
check "cancelled config passes" 0 '{"config":{"result":"cancelled"},"rust":{"result":"skipped"}}'
check "failure fails" 1 '{"a":{"result":"success"},"b":{"result":"failure"}}'
check "failure among cancelled fails" 1 '{"a":{"result":"failure"},"b":{"result":"cancelled"}}'
check "failed config fails" 1 '{"config":{"result":"failure"},"rust":{"result":"skipped"}}'
check "empty needs fails" 1 '{}'
exit "$fail"
