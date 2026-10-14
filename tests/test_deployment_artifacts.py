"""Static checks for the container, Compose and Helm deployment artefacts.

No cluster or container runtime is needed; the Helm checks render the chart
with ``helm template`` and are skipped when the binary is absent.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "deploy" / "helm" / "kurort-engine"
K3D_VALUES = ROOT / "deploy" / "k3d" / "values-k3d.yaml"

helm = shutil.which("helm")
needs_helm = pytest.mark.skipif(helm is None, reason="helm not installed")


def _render(*args: str) -> list[dict]:
    result = subprocess.run(
        [helm, "template", "kurort", str(CHART), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _by_kind(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d["kind"] == kind]


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
    )
    assert not _by_kind(docs, "StatefulSet")
    pod = _by_kind(docs, "Deployment")[0]["spec"]["template"]["spec"]
    assert [c["name"] for c in pod["initContainers"]] == ["wait-db", "migrate"]
    db_env = next(e for e in pod["containers"][0]["env"] if e["name"] == "KURORT_DATABASE_URL")
    assert db_env["valueFrom"]["secretKeyRef"] == {"name": "pg-app", "key": "uri"}


@needs_helm
def test_chart_refuses_a_missing_database_and_a_bad_seed_mode():
    for args in (("--set", "postgresql.enabled=false"), ("--set", "demo.seed=bogus")):
        with pytest.raises(subprocess.CalledProcessError):
            _render(*args)
