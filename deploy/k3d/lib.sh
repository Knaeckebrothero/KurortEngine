# Shared helpers for deploy/k3d/*.sh — source, don't execute.
# shellcheck shell=bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
CLUSTER_NAME="${CLUSTER_NAME:-kurort}"
KUBE_CONTEXT="k3d-${CLUSTER_NAME}"
NAMESPACE="${NAMESPACE:-kurort}"
RELEASE="${RELEASE:-kurort}"
# values-k3d.yaml sets fullnameOverride=kurort, so the Deployment is "kurort".
APP_DEPLOY="${APP_DEPLOY:-kurort}"
HTTP_PORT="${HTTP_PORT:-8090}"
HOST="${HOST:-kurort.localhost}"
IMAGE_REPO="${IMAGE_REPO:-localhost/kurort-engine}"
CHART_DIR="$REPO_ROOT/deploy/helm/kurort-engine"
VALUES_FILE="$SCRIPT_DIR/values-k3d.yaml"
# Demo Keycloak (stands in for the customer's company Keycloak).
KC_RELEASE="${KC_RELEASE:-keycloak}"
KC_CHART_DIR="$SCRIPT_DIR/keycloak"
KC_HOST="${KC_HOST:-auth.kurort.localhost}"
KC_REALM="${KC_REALM:-hotel-rheinland}"

log()  { printf '\033[1;34m[kurort]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }
skip() { printf '\033[1;33m[skip]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

require() {
  local bin
  for bin in "$@"; do
    command -v "$bin" >/dev/null || die "missing required binary: $bin"
  done
}

# k3d drives a Docker-API runtime: Docker itself, or podman via DOCKER_HOST.
check_runtime() {
  docker info >/dev/null 2>&1 \
    || die "k3d needs a Docker API: start Docker, or export DOCKER_HOST=unix://\$XDG_RUNTIME_DIR/podman/podman.sock"
}

new_tag() {
  printf 'dev-%s' "$(date +%Y%m%d-%H%M%S)"
}

build_image() {
  local tag=$1
  log "building $IMAGE_REPO:$tag with podman"
  podman build --format docker -t "$IMAGE_REPO:$tag" "$REPO_ROOT" \
    || die "podman build failed"
  ok "image built"
}

import_image() {
  local tag=$1 tmp
  tmp=$(mktemp -d) || die "mktemp failed"
  log "importing $IMAGE_REPO:$tag into k3d cluster '$CLUSTER_NAME'"
  podman save --format docker-archive -o "$tmp/kurort-engine.tar" "$IMAGE_REPO:$tag" \
    || { rm -rf "$tmp"; die "podman save failed"; }
  k3d image import "$tmp/kurort-engine.tar" -c "$CLUSTER_NAME" \
    || { rm -rf "$tmp"; die "k3d image import failed"; }
  rm -rf "$tmp"
  ok "image imported"
}

deploy_release() {
  local tag=$1
  shift
  log "helm upgrade --install $RELEASE (image tag $tag)"
  helm upgrade --install "$RELEASE" "$CHART_DIR" \
    --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" --create-namespace \
    -f "$VALUES_FILE" --set image.tag="$tag" --set ingress.host="$HOST" \
    --wait --timeout 5m "$@" \
    || die "helm upgrade failed — kubectl --context $KUBE_CONTEXT -n $NAMESPACE get pods,events"
  ok "release deployed"
}

wait_http() {
  local url="http://$HOST:$HTTP_PORT/healthz" i
  log "waiting for $url"
  for i in $(seq 1 60); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
      ok "app answers at http://$HOST:$HTTP_PORT/"
      return 0
    fi
    sleep 2
  done
  die "no answer from $url after 120s"
}

# Install/upgrade the demo Keycloak. No --wait: on a fresh cluster its database
# lives in the app release's Postgres, which deploy_release creates next. The
# release does create the shared client Secret immediately, which the app needs.
deploy_keycloak() {
  log "helm upgrade --install $KC_RELEASE (demo Keycloak)"
  helm upgrade --install "$KC_RELEASE" "$KC_CHART_DIR" \
    --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" --create-namespace \
    --set hostname="http://$KC_HOST:$HTTP_PORT" --set ingress.host="$KC_HOST" \
    --set client.appUrl="http://$HOST:$HTTP_PORT" \
    || die "helm upgrade of $KC_RELEASE failed"
  ok "keycloak release applied"
}

wait_keycloak() {
  local url="http://$KC_HOST:$HTTP_PORT/realms/$KC_REALM/.well-known/openid-configuration" i
  log "waiting for Keycloak (first start imports the realm; allow a few minutes)"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status "deploy/$KC_RELEASE" --timeout=8m \
    || die "Keycloak did not become ready — kubectl --context $KUBE_CONTEXT -n $NAMESPACE logs deploy/$KC_RELEASE"
  for i in $(seq 1 60); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
      ok "realm $KC_REALM answers at $url"
      return 0
    fi
    sleep 2
  done
  die "no discovery document at $url after 120s"
}
