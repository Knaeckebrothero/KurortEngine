# Running KurortEngine on Kubernetes

The staff web application ships as one container image and one Helm chart,
`deploy/helm/kurort-engine`. The chart runs the app (FastAPI) and, by default,
a bundled single-instance Postgres 17. Database migrations and demo seeding run
as init containers of the app pod.

## Local cluster on k3d

Prerequisites: `podman` (builds the image), `docker` or a Docker-API socket for
k3d, `k3d` 5.x, `kubectl`, `helm` 3, `curl`.

```bash
deploy/k3d/up.sh        # create cluster "kurort", build, import, install
                        # → http://kurort.localhost:8090/
deploy/k3d/reload.sh    # after code changes: rebuild + roll the pod (~30 s)
deploy/k3d/down.sh      # delete cluster "kurort" (and the demo database)
```

`up.sh` is idempotent. It creates the k3d cluster `kurort` with the cluster
load balancer's port 80 on host port 8090 (`HTTP_PORT=...` changes it for a new
cluster), builds `localhost/kurort-engine:dev-<timestamp>` with podman, moves it
into the cluster with `podman save` + `k3d image import` (no registry), and runs
`helm upgrade --install kurort` into namespace `kurort` using
`deploy/k3d/values-k3d.yaml`. Every build gets a fresh tag, so the Deployment
always rolls. Extra arguments go to Helm:

```bash
deploy/k3d/up.sh --set demo.seed=reset --set app.today=2026-10-21
```

`*.localhost` resolves to the loopback address in browsers and curl, so no
`/etc/hosts` entry is needed.

k3d talks to whatever answers the Docker API. On a host with Docker installed
that is Docker itself; on a podman-only host export
`DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock` first (untested here;
see the k3d podman guide).

Useful commands:

```bash
kubectl --context k3d-kurort -n kurort get pods
kubectl --context k3d-kurort -n kurort logs deploy/kurort -c web -f
kubectl --context k3d-kurort -n kurort logs deploy/kurort -c migrate
kubectl --context k3d-kurort -n kurort exec deploy/kurort -c web -- kurort-app seed --reset
kubectl --context k3d-kurort -n kurort exec -it kurort-postgresql-0 -- psql -U kurort kurort
```

## What the chart deploys

| Object | Name (k3d) | Purpose |
|---|---|---|
| Deployment | `kurort` | init containers `wait-db` → `migrate` → `seed` (unless `demo.seed=off`), then `web` (`kurort-app serve`, port 8080) |
| Service | `kurort` | ClusterIP, port 80 → 8080 |
| Ingress | `kurort` | `ingress.host`, class `traefik` by default |
| StatefulSet | `kurort-postgresql` | bundled Postgres 17 with a PVC (only when `postgresql.enabled`) |
| Services | `kurort-postgresql`, `kurort-postgresql-hl` | ClusterIP and headless |
| Secret | `kurort-postgresql` | `username`, `password`, `database`, `database-url` |

Probes: startup and liveness on `/healthz` (process up), readiness on `/readyz`
(database answers). Containers run as non-root with a read-only root file
system; `/tmp` is an `emptyDir` and `HOME=/tmp`.

The bundled Postgres password is generated on first install and read back from
the Secret on every upgrade. The Secret carries `helm.sh/resource-policy: keep`
and the PVC outlives `helm uninstall`, so a reinstall finds matching credentials
and data. Delete both by hand to start clean.

## Values reference

| Key | Default | Meaning |
|---|---|---|
| `image.repository` / `image.tag` / `image.pullPolicy` | `localhost/kurort-engine` / `dev` / `IfNotPresent` | app image (k3d values use `Never`) |
| `replicaCount` | `1` | keep at 1: every pod migrates in an init container (move `kurort-app migrate` into a Job before scaling out) |
| `app.hotelName`, `app.hotelCity` | `Hotel Rheinland`, `Bad Orb` | shown in the UI |
| `app.today` | empty | pin the business date (`YYYY-MM-DD`) for a reproducible demo |
| `app.extraEnv` | `{}` | extra `KURORT_*` variables for all app containers |
| `demo.seed` | `if-empty` | `if-empty` seeds an empty DB, `reset` wipes and reseeds on every pod start, `off` never seeds |
| `ingress.enabled`, `.className`, `.host`, `.annotations`, `.tls` | on, `traefik`, `kurort.localhost` | standard Ingress settings |
| `resources`, `podSecurityContext`, `securityContext` | small requests, non-root | app pod |
| `postgresql.enabled` | `true` | bundled database |
| `postgresql.auth.username` / `.database` / `.password` | `kurort` / `kurort` / generated | bundled database credentials |
| `postgresql.persistence.size` / `.storageClass` | `2Gi` / default class | bundled database volume |
| `externalDatabase.existingSecret` / `.existingSecretKey` | empty / `uri` | Secret holding the database URL when `postgresql.enabled=false` |
| `externalDatabase.url` | empty | alternatively a URL; the chart creates the Secret |

The app accepts `postgresql://`, `postgres://` and `postgresql+psycopg://` URLs.

## Production notes

- **Database.** Disable the bundled Postgres and use a managed database or a
  CloudNativePG cluster. CNPG creates `<cluster>-app` with the connection URL
  under `uri`:

  ```bash
  helm upgrade --install kurort deploy/helm/kurort-engine -n kurort \
    --set postgresql.enabled=false \
    --set externalDatabase.existingSecret=kurort-db-app \
    --set demo.seed=off \
    --set image.repository=ghcr.io/<org>/kurort-engine --set image.tag=<version> \
    --set ingress.host=rezeption.example.de
  ```

- **TLS.** Set `ingress.tls` (and, with cert-manager, a
  `cert-manager.io/cluster-issuer` annotation). The app trusts
  `X-Forwarded-*` headers from the ingress.
- **Backups.** The bundled StatefulSet has none. Production data belongs in a
  database with scheduled backups (CNPG `ScheduledBackup` to object storage),
  plus a tested restore.
- **Authentication.** The app has no login yet. Do not expose it beyond a
  trusted network without an authenticating proxy in front.
- **Demo mornings.** Seed data is laid out around the date it was generated.
  Before a demo, reseed so today's arrivals and departures are current:
  `kubectl -n kurort exec deploy/kurort -c web -- kurort-app seed --reset`,
  or deploy with `--set demo.seed=reset` so every pod start reseeds. To show
  the same day every time, pin it with `--set app.today=YYYY-MM-DD`.

## Docker Compose

For a single machine without Kubernetes, `compose.yaml` runs Postgres and the
app. See [local-development.md](local-development.md#docker-compose).
