# Local development

## Python environment

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[web,dev]"
```

The engine (`kurort_engine`) needs only `[dev]`; the staff web application
(`kurort_app`) needs `[web]`.

## Postgres for tests and development

```bash
podman run -d --name kurort-test-pg -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=kurort -e POSTGRES_PASSWORD=kurort -e POSTGRES_DB=kurort \
  docker.io/library/postgres:17-alpine
```

The app tests (`tests/app/`) create and drop their own database on that server
(`KURORT_TEST_DATABASE_URL`, default
`postgresql+psycopg://kurort:kurort@127.0.0.1:55432/kurort_test`). Without a
reachable server they are skipped, not failed.

```bash
.venv/bin/python -m pytest tests/app -q          # web app
.venv/bin/python -m pytest -q                    # everything
```

## Running the app

```bash
export KURORT_DATABASE_URL=postgresql+psycopg://kurort:kurort@127.0.0.1:55432/kurort
.venv/bin/kurort-app migrate
.venv/bin/kurort-app seed --reset            # demo data around today
.venv/bin/kurort-app serve --port 8000 --reload
```

Open http://127.0.0.1:8000/ (API docs at `/api/docs`). `KURORT_TODAY=2026-10-14`
pins the business date; `kurort-app seed --reset` lays the demo data out around
it.

## Docker Compose

```bash
podman compose up -d --build        # or: docker compose up -d --build
open http://localhost:8080/          # PORT=8104 podman compose up ... for another port
podman compose logs -f app
podman compose down                  # add -v to drop the database volume
```

The app container waits for Postgres, applies migrations, seeds demo data when
the database is empty (`KURORT_SEED=if-empty|reset|off`) and serves on 8080.

## Kubernetes

See [kubernetes.md](kubernetes.md): `deploy/k3d/up.sh` brings the whole stack
up on a local k3d cluster.
