# syntax=docker/dockerfile:1
# KurortEngine staff web application (FastAPI + Postgres).
#
# Build:  podman build -t kurort-engine:dev .        (docker build works too)
# Run:    see compose.yaml, or deploy/helm/kurort-engine for Kubernetes.
#
# The image runs `kurort-app serve` on $PORT (8080). Database migrations and
# demo seeding are separate `kurort-app` subcommands, run by the compose
# entrypoint or by the Helm chart's init containers.

ARG PYTHON_IMAGE=docker.io/library/python:3.12-slim

# ---------------------------------------------------------------- builder ---
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /build
# Dependencies first so source edits do not invalidate the dependency layer.
COPY pyproject.toml README.md ./
RUN mkdir -p src/kurort_engine src/kurort_app \
 && touch src/kurort_engine/__init__.py src/kurort_app/__init__.py \
 && pip install ".[web]" \
 && pip uninstall -y kurort-engine

COPY src/ ./src/
RUN pip install --no-deps . \
 && python -c "from kurort_engine.rates import load_profile; load_profile('hessen', 'bad_orb')" \
 && python -c "import kurort_app.main" \
 && pip uninstall -y pip

# ---------------------------------------------------------------- runtime ---
FROM ${PYTHON_IMAGE}

LABEL org.opencontainers.image.title="kurort-engine" \
      org.opencontainers.image.description="KurortEngine staff web application for Hotel Rheinland" \
      org.opencontainers.image.source="https://github.com/Knaeckebrothero/KurortEngine"

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN groupadd --gid 65532 app \
 && useradd --uid 65532 --gid 65532 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv
COPY deploy/docker/entrypoint.sh /usr/local/bin/kurort-entrypoint

WORKDIR /tmp
USER 65532:65532
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8080'), timeout=2).status == 200 else 1)"]

CMD ["kurort-app", "serve"]
