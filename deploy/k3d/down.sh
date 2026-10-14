#!/usr/bin/env bash
# Delete the local k3d cluster "kurort" (and with it the demo database).
# Touches no other cluster.
set -euo pipefail
# shellcheck source=deploy/k3d/lib.sh
source "$(dirname "$0")/lib.sh"

require k3d
[ "$CLUSTER_NAME" = "kurort" ] || [ "${FORCE:-}" = "1" ] \
  || die "refusing to delete cluster '$CLUSTER_NAME' (set FORCE=1 if you really mean it)"
if k3d cluster get "$CLUSTER_NAME" >/dev/null 2>&1; then
  k3d cluster delete "$CLUSTER_NAME" || die "k3d cluster delete failed"
  ok "cluster '$CLUSTER_NAME' deleted"
else
  skip "no cluster '$CLUSTER_NAME'"
fi
