"""Static checks for the container, Compose and Helm deployment artefacts.

No cluster or container runtime is needed; the Helm checks render the chart
with ``helm template`` and are skipped when the binary is absent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "deploy" / "helm" / "kurort-engine"
K3D_VALUES = ROOT / "deploy" / "k3d" / "values-k3d.yaml"
KEYCLOAK_CHART = ROOT / "deploy" / "k3d" / "keycloak"

helm = shutil.which("helm")
needs_helm = pytest.mark.skipif(helm is None, reason="helm not installed")


def _render(*args: str, chart: Path = CHART, release: str = "kurort") -> list[dict]:
    result = subprocess.run(
        [helm, "template", release, str(chart), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _by_kind(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d["kind"] == kind]


def _web_env(docs: list[dict]) -> dict[str, dict]:
    pod = _by_kind(docs, "Deployment")[0]["spec"]["template"]["spec"]
    return {e["name"]: e for e in pod["containers"][0]["env"]}


def _helm_error(*args: str) -> str:
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        _render(*args)
    return excinfo.value.stderr


def test_dockerfile_runs_the_app_as_non_root():
    text = (ROOT / "Dockerfile").read_text()
    assert 'pip install ".[web]"' in text
    assert "USER 65532:65532" in text
    assert 'CMD ["kurort-app", "serve"]' in text
    assert "/healthz" in text


def test_dockerignore_keeps_the_context_small():
    lines = [
        ln
        for ln in (ROOT / ".dockerignore").read_text().splitlines()
        if ln and not ln.startswith("#")
    ]
    assert lines[0] == "*", "the build context must be an allow-list"
    for keep in ("!pyproject.toml", "!README.md", "!src/", "!deploy/docker/"):
        assert keep in lines


def test_compose_waits_for_a_healthy_database():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    db, app = compose["services"]["db"], compose["services"]["app"]
    assert db["image"].endswith("postgres:17-alpine")
    assert "healthcheck" in db
    assert app["depends_on"]["db"]["condition"] == "service_healthy"
    assert app["command"] == ["kurort-entrypoint"]
    assert "KURORT_DATABASE_URL" in app["environment"]
    assert app["environment"]["KURORT_AUTH"] == "off", "Compose is the login-free local stack"


def test_entrypoint_migrates_before_serving():
    script = (ROOT / "deploy" / "docker" / "entrypoint.sh").read_text()
    order = [
        script.index(step)
        for step in ("kurort-app wait-db", "kurort-app migrate", "exec kurort-app serve")
    ]
    assert order == sorted(order)


@needs_helm
def test_chart_renders_app_and_bundled_postgres():
    docs = _render("-f", str(K3D_VALUES))
    deployment = _by_kind(docs, "Deployment")[0]
    pod = deployment["spec"]["template"]["spec"]
    assert [c["name"] for c in pod["initContainers"]] == ["wait-db", "migrate", "seed"]
    web = pod["containers"][0]
    assert web["readinessProbe"]["httpGet"]["path"] == "/readyz"
    assert web["livenessProbe"]["httpGet"]["path"] == "/healthz"
    assert web["securityContext"]["readOnlyRootFilesystem"] is True
    assert pod["securityContext"]["runAsNonRoot"] is True
    db_env = next(e for e in web["env"] if e["name"] == "KURORT_DATABASE_URL")
    assert db_env["valueFrom"]["secretKeyRef"] == {
        "name": "kurort-postgresql",
        "key": "database-url",
    }
    assert _by_kind(docs, "StatefulSet")[0]["metadata"]["name"] == "kurort-postgresql"
    ingress = _by_kind(docs, "Ingress")[0]
    assert ingress["spec"]["ingressClassName"] == "traefik"
    assert ingress["spec"]["rules"][0]["host"] == "kurort.localhost"


@needs_helm
def test_chart_uses_an_external_secret_without_bundled_postgres():
    docs = _render(
        "--set",
        "postgresql.enabled=false",
        "--set",
        "externalDatabase.existingSecret=pg-app",
        "--set",
        "demo.seed=off",
        "--set",
        "auth.enabled=false",
    )
    assert not _by_kind(docs, "StatefulSet")
    pod = _by_kind(docs, "Deployment")[0]["spec"]["template"]["spec"]
    assert [c["name"] for c in pod["initContainers"]] == ["wait-db", "migrate"]
    db_env = next(e for e in pod["containers"][0]["env"] if e["name"] == "KURORT_DATABASE_URL")
    assert db_env["valueFrom"]["secretKeyRef"] == {"name": "pg-app", "key": "uri"}


@needs_helm
def test_chart_refuses_a_missing_database_and_a_bad_seed_mode():
    no_auth = ("--set", "auth.enabled=false")
    assert "externalDatabase" in _helm_error("--set", "postgresql.enabled=false", *no_auth)
    assert "demo.seed" in _helm_error("--set", "demo.seed=bogus", *no_auth)


@needs_helm
def test_k3d_values_wire_the_app_to_the_demo_keycloak():
    docs = _render("-f", str(K3D_VALUES))
    env = _web_env(docs)
    assert env["KURORT_AUTH"]["value"] == "oidc"
    assert env["KURORT_PUBLIC_URL"]["value"] == "http://kurort.localhost:8090"
    assert (
        env["KURORT_OIDC_ISSUER"]["value"]
        == "http://auth.kurort.localhost:8090/realms/hotel-rheinland"
    )
    assert env["KURORT_OIDC_INTERNAL_URL"]["value"].startswith(
        "http://keycloak.kurort.svc.cluster.local:8080/"
    )
    assert env["KURORT_OIDC_CLIENT_ID"]["value"] == "kurort-app"
    assert env["KURORT_OIDC_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "keycloak-kurort-app-client",
        "key": "client-secret",
    }
    assert env["KURORT_SESSION_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "kurort-auth",
        "key": "session-secret",
    }
    auth_secret = next(
        d for d in _by_kind(docs, "Secret") if d["metadata"]["name"] == "kurort-auth"
    )
    assert len(auth_secret["stringData"]["session-secret"]) >= 32
    assert "client-secret" not in auth_secret["stringData"]


@needs_helm
def test_chart_without_auth_runs_login_free():
    docs = _render("-f", str(K3D_VALUES), "--set", "auth.enabled=false")
    env = _web_env(docs)
    assert env["KURORT_AUTH"]["value"] == "off"
    assert not [name for name in env if name.startswith(("KURORT_OIDC_", "KURORT_SESSION"))]
    assert "kurort-auth" not in [d["metadata"]["name"] for d in _by_kind(docs, "Secret")]


@needs_helm
def test_chart_stores_a_literal_client_secret():
    docs = _render(
        "--set",
        "auth.oidc.issuer=https://login.example.de/realms/x",
        "--set",
        "auth.oidc.clientSecret=s3cr3t",
    )
    env = _web_env(docs)
    assert env["KURORT_OIDC_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "kurort-kurort-engine-auth",
        "key": "client-secret",
    }
    assert env["KURORT_OIDC_INTERNAL_URL"]["value"] == "https://login.example.de/realms/x"
    assert env["KURORT_PUBLIC_URL"]["value"] == "http://kurort.localhost"
    secret = next(d for d in _by_kind(docs, "Secret") if d["metadata"]["name"].endswith("-auth"))
    assert secret["stringData"]["client-secret"] == "s3cr3t"


@needs_helm
def test_chart_fails_fast_on_incomplete_auth():
    issuer = ("--set", "auth.oidc.issuer=https://login.example.de/realms/x")
    secret = ("--set", "auth.oidc.existingSecret=oidc")
    assert "auth.oidc.issuer" in _helm_error(*secret)
    assert "clientSecret" in _helm_error(*issuer)
    assert "auth.publicUrl" in _helm_error(*issuer, *secret, "--set", "ingress.enabled=false")


@needs_helm
def test_demo_keycloak_realm_matches_the_app_contract():
    docs = _render(chart=KEYCLOAK_CHART, release="keycloak")
    names = {(d["kind"], d["metadata"]["name"]) for d in docs}
    k3d_values = yaml.safe_load(K3D_VALUES.read_text())
    assert ("Secret", k3d_values["auth"]["oidc"]["existingSecret"]) in names

    configmap = _by_kind(docs, "ConfigMap")[0]
    realm = json.loads(next(iter(configmap["data"].values())))
    assert realm["realm"] == "hotel-rheinland"
    assert realm["defaultLocale"] == "de" and realm["registrationAllowed"] is False
    assert {r["name"] for r in realm["roles"]["realm"]} == {
        "rezeption", "leitung", "housekeeping", "kueche"
    }

    client = realm["clients"][0]
    assert client["clientId"] == k3d_values["auth"]["oidc"]["clientId"]
    assert client["publicClient"] is False and client["directAccessGrantsEnabled"] is False
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert client["redirectUris"] == [k3d_values["auth"]["publicUrl"] + "/auth/callback"]
    mapper = client["protocolMappers"][0]
    assert mapper["protocolMapper"] == "oidc-usermodel-realm-role-mapper"
    assert mapper["config"]["claim.name"] == "roles"

    users = {u["username"]: set(u["realmRoles"]) for u in realm["users"]}
    assert {"rezeption"} <= users["m.schmidt"]
    assert {"rezeption", "leitung"} <= users["t.weber"]
    assert not {"rezeption", "leitung", "housekeeping", "kueche"} & users["k.gast"]
    assert users["j.becker"] == {"default-roles-hotel-rheinland", "kueche"}
    jana = next(u for u in realm["users"] if u["username"] == "j.becker")
    assert (jana["firstName"], jana["lastName"]) == ("Jana", "Becker")
    declared = {r["name"] for r in realm["roles"]["realm"]} | {
        "default-roles-hotel-rheinland"
    }
    assert all(roles <= declared for roles in users.values())
    assert users["s.klein"] == {"default-roles-hotel-rheinland", "housekeeping"}
    sandra = next(u for u in realm["users"] if u["username"] == "s.klein")
    assert (sandra["firstName"], sandra["lastName"]) == ("Sandra", "Klein")

    keycloak = _by_kind(docs, "Deployment")[0]["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e for e in keycloak["env"]}
    assert env["KC_HOSTNAME"]["value"] == "http://auth.kurort.localhost:8090"
    assert env["KC_HOSTNAME_BACKCHANNEL_DYNAMIC"]["value"] == "true"
    # Keycloak reads every KC_* variable as one of its own options.
    official = {
        "KC_DB",
        "KC_DB_URL",
        "KC_DB_USERNAME",
        "KC_DB_PASSWORD",
        "KC_HOSTNAME",
        "KC_HOSTNAME_BACKCHANNEL_DYNAMIC",
        "KC_PROXY_HEADERS",
        "KC_HTTP_ENABLED",
        "KC_HEALTH_ENABLED",
        "KC_BOOTSTRAP_ADMIN_USERNAME",
        "KC_BOOTSTRAP_ADMIN_PASSWORD",
    }
    assert {name for name in env if name.startswith("KC_")} <= official
