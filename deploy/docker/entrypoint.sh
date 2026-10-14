#!/bin/sh
# Compose entrypoint: wait for Postgres, migrate, seed demo data, serve.
# KURORT_SEED controls seeding: if-empty (default) | reset | off.
set -eu

kurort-app wait-db --timeout "${KURORT_WAIT_DB_TIMEOUT:-60}"
kurort-app migrate
case "${KURORT_SEED:-if-empty}" in
  if-empty) kurort-app seed --if-empty ;;
  reset)    kurort-app seed --reset ;;
  off)      echo "kurort-app: seeding disabled" ;;
  *)        echo "KURORT_SEED must be if-empty, reset or off (got '${KURORT_SEED}')" >&2; exit 2 ;;
esac
exec kurort-app serve
