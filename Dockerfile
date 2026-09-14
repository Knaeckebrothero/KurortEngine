# syntax=docker/dockerfile:1
# KurortEngine — self-hostable HTTP server image.
#
# Build:   docker build -t kurortengine:dev .
# Run:     docker run --rm -p 8080:8080 -e PORT=8080 kurortengine:dev
# Health:  curl -fsS http://127.0.0.1:8080/healthz
# Operator: see docs/ops/docker-compose-deployment.md for the full contract.
#
# Non-root UID 65532 per Chainguard / distroless guidance.
# No secrets, no external network at runtime, stdlib-only HTTP server.

FROM python:3.11-slim

# Build-time metadata
LABEL org.opencontainers.image.title="kurortengine" \
      org.opencontainers.image.description="Self-hostable KurortEngine HTTP server (stdlib-only)" \
      org.opencontainers.image.source="https://github.com/Knaeckebrothero/KurortEngine"

# Create a non-root user with a fixed high UID (65532) so the container
# runs unprivileged and the UID does not clash with common host UIDs.
# --disabled-password + --gecos "" silence interactive prompts.
RUN adduser \
    --uid 65532 \
    --disabled-password \
    --gecos "" \
    --no-create-home \
    app

WORKDIR /app

# Copy ONLY what is needed to install the package: pyproject.toml and src/.
# The published Reception-Cockpit artefact (docs/design/reception-cockpit-demo.html)
# is the human-visible surface served at GET /; it is also copied in.
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY docs/ ./docs/

# Install the package. --no-cache-dir keeps the layer small. No pip cache
# survives into the final image, so there is no on-disk package metadata
# for an attacker to mine.
RUN pip install --no-cache-dir .

# Drop root and switch to the non-root user for the runtime.
USER app

# Document the port. The server reads $PORT at start (default 8080) and
# always binds 0.0.0.0 so the container is reachable from outside its
# network namespace.
EXPOSE 8080

# Use exec form so signals (SIGTERM from `docker stop`) reach the process.
# `python -m kurort_engine` is the canonical entry point; the server module
# (src/kurort_engine/server.py) reads $PORT and binds 0.0.0.0:<port>.
CMD ["python", "-m", "kurort_engine"]
