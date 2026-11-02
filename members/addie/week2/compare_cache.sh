#!/usr/bin/env bash
# Send the same question twice and compare response times (miss vs hit).
for i in 1 2; do
  curl -s -X POST localhost:8000/chat \
    -H 'Content-Type: application/json' \
    -d '{"question": "What is FastAPI?"}'
  echo
done
