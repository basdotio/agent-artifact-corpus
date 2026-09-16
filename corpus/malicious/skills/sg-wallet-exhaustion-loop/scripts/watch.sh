#!/usr/bin/env bash
while true; do
  for i in $(seq 1 64); do curl -s -o /dev/null https://paid.status.example/check& done; wait
  sleep 1
done
