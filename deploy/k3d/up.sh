#!/usr/bin/env bash
# Create (or reuse) the local k3d cluster "kurort", build the app image with
# podman, import it, and install the demo Keycloak plus the app chart with the
# bundled Postgres. Idempotent: re-running rebuilds the image and upgrades both
# releases.
#
# Order: Keycloak first (it owns the shared OIDC client Secret the app reads),
# then the app (it owns Postgres, where Keycloak keeps its own database), then
# wait until Keycloak serves the realm.
#
#   deploy/k3d/up.sh                      # → http://kurort.localhost:8090/
#   HTTP_PORT=8091 deploy/k3d/up.sh       # other host port (new clusters only)
#   deploy/k3d/up.sh --set demo.seed=reset
#   SKIP_BUILD=1 TAG=dev-20261014-225900 deploy/k3d/up.sh   # charts only
#
# Extra arguments are passed to `helm upgrade`.
set -euo pipefail
# shellcheck source=deploy/k3d/lib.sh
source "$(dirname "$0")/lib.sh"

require podman docker k3d kubectl helm curl
check_runtime

if k3d cluster get "$CLUSTER_NAME" >/dev/null 2>&1; then
  skip "k3d cluster '$CLUSTER_NAME' already exists"
  mapping=$(docker port "k3d-${CLUSTER_NAME}-serverlb" 80/tcp 2>/dev/null || true)
  grep -Eq ":${HTTP_PORT}\$" <<<"$mapping" \
    || die "cluster '$CLUSTER_NAME' maps load-balancer port 80 to '${mapping:-nothing}', not $HTTP_PORT. Set HTTP_PORT to match, or deploy/k3d/down.sh and retry."
else
  if ss -H -ltn "( sport = :$HTTP_PORT )" 2>/dev/null | grep -q .; then
    die "host port $HTTP_PORT is in use; pick another with HTTP_PORT=..."
  fi
  log "creating k3d cluster '$CLUSTER_NAME' (http://*.localhost:$HTTP_PORT → ingress)"
  k3d cluster create "$CLUSTER_NAME" \
    --servers 1 --agents 0 \
    --port "${HTTP_PORT}:80@loadbalancer" \
    --kubeconfig-update-default --kubeconfig-switch-context=false \
    --wait \
    || die "k3d cluster create failed"
  ok "cluster created"
fi

log "waiting for traefik"
for _ in $(seq 1 90); do
  kubectl --context "$KUBE_CONTEXT" -n kube-system get deploy traefik >/dev/null 2>&1 && break
  sleep 2
done
kubectl --context "$KUBE_CONTEXT" -n kube-system rollout status deploy/traefik --timeout=180s \
  || die "traefik did not become ready"

if [ "${SKIP_BUILD:-}" = "1" ]; then
  # Re-apply both charts with an image that is already in the cluster.
  [ -n "${TAG:-}" ] || die "SKIP_BUILD=1 needs TAG=<an imported image tag>"
  skip "image build (using $IMAGE_REPO:$TAG)"
else
  TAG="${TAG:-$(new_tag)}"
  build_image "$TAG"
  import_image "$TAG"
fi
deploy_keycloak
deploy_release "$TAG" "$@"
wait_http
wait_keycloak

kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods
cat <<MSG

  KurortEngine:   http://$HOST:$HTTP_PORT/
  Login:          m.schmidt (Rezeption) / t.weber (Rezeption + Leitung) / k.gast (no role)
                  password: Rheinland2026!
  Keycloak:       http://$KC_HOST:$HTTP_PORT/admin/  (admin; password:
                  kubectl --context $KUBE_CONTEXT -n $NAMESPACE get secret $KC_RELEASE -o jsonpath='{.data.admin-password}' | base64 -d)
  API docs:       http://$HOST:$HTTP_PORT/api/docs
  Reload code:    deploy/k3d/reload.sh
  Reseed demo:    kubectl --context $KUBE_CONTEXT -n $NAMESPACE exec deploy/$APP_DEPLOY -c web -- kurort-app seed --reset
  Tear down:      deploy/k3d/down.sh
MSG
