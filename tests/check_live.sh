#!/usr/bin/env bash
# Run both live clients against the mock relay and check what they printed.
set -euo pipefail
cd "$(dirname "$0")/.."
# GNU timeout is not on macOS: fall back to perl's alarm.
if ! command -v timeout >/dev/null; then timeout() { perl -e 'alarm shift; exec @ARGV' "$@"; }; fi
PYTHON=${PYTHON:-python}
export AQ_API_KEY=aqk_test AQ_FEED_URL='ws://127.0.0.1:18777/ws?symbol=BTC&channel=tob100'
expected=$'best bid 100  best ask 101\nbest bid 99  best ask 100.5\nbest bid 98  best ask 103'
for client in "node live/feed.mjs" "$PYTHON -u live/feed.py"; do
  node tests/mock_relay.mjs & mock=$!
  sleep 0.5
  out=$( (timeout 5 $client || true) 2>&1 )
  kill $mock 2>/dev/null || true; wait $mock 2>/dev/null || true
  got=$(printf '%s\n' "$out" | grep '^best bid' | sed -E 's/([0-9])\.0( |$)/\1\2/g' | head -6 || true)
  want=$(printf '%s\n%s' "$expected" "$expected")
  if [ "$got" != "$want" ]; then
    echo "FAIL: $client printed:"; printf '%s\n' "$out"; exit 1
  fi
  printf '%s\n' "$out" | grep -q 'refused\|401' || { echo "FAIL: $client did not report the refused handshake"; exit 1; }
  echo "ok: $client"
done
