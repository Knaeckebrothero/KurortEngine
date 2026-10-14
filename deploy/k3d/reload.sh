#!/usr/bin/env bash
# Fast UI iteration: rebuild the image under a fresh tag, import it, and roll
# the app Deployment. Requires the cluster from deploy/k3d/up.sh. Keycloak is
# left alone; re-run up.sh after changing deploy/k3d/keycloak.
#
#   deploy/k3d/reload.sh [extra helm args]
set -euo pipefail
# shellcheck source=deploy/k3d/lib.sh
source "$(dirname "$0")/lib.sh"

require podman docker k3d kubectl helm curl
check_runtime
k3d cluster get "$CLUSTER_NAME" >/dev/null 2>&1 || die "no cluster '$CLUSTER_NAME' — run deploy/k3d/up.sh first"

TAG="${TAG:-$(new_tag)}"
build_image "$TAG"
import_image "$TAG"
deploy_release "$TAG" "$@"
wait_http
