# Running KurortEngine on Kubernetes

The staff web application ships as one container image and one Helm chart,
`deploy/helm/kurort-engine`. The chart runs the app (FastAPI) and, by default,
a bundled single-instance Postgres 17. Database migrations and demo seeding run
as init containers of the app pod. Staff log in through OpenID Connect; the
local k3d setup adds a demo Keycloak (see [Authentication](#authentication)).

## Local cluster on k3d

Prerequisites: `podman` (builds the image), `docker` or a Docker-API socket for
k3d, `k3d` 5.x, `kubectl`, `helm` 3, `curl`.

```bash
deploy/k3d/up.sh        # create cluster "kurort", build, import, install
                        # Keycloak + app → http://kurort.localhost:8090/
deploy/k3d/reload.sh    # after code changes: rebuild + roll the app pod (~30 s)
deploy/k3d/down.sh      # delete cluster "kurort" (and the demo database)
SKIP_BUILD=1 TAG=<tag> deploy/k3d/up.sh   # re-apply both charts, no image build
```

`up.sh` is idempotent. It creates the k3d cluster `kurort` with the cluster
load balancer's port 80 on host port 8090 (`HTTP_PORT=...` changes it for a new
cluster), builds `localhost/kurort-engine:dev-<timestamp>` with podman, moves it
into the cluster with `podman save` + `k3d image import` (no registry), and runs
`helm upgrade --install` for two releases into namespace `kurort`: first the
demo Keycloak (`keycloak`, chart `deploy/k3d/keycloak`), then the app
(`kurort`, `deploy/k3d/values-k3d.yaml`), and finally waits until Keycloak
serves its realm. Every build gets a fresh tag, so the app Deployment always
rolls. `reload.sh` only touches the app; re-run `up.sh` after changing the
Keycloak chart. Extra arguments go to the app's `helm upgrade`:

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
| Secret | `kurort-auth` | `session-secret` (generated once, kept), `client-secret` when given as a value (only with `auth.enabled`) |

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
| `assistant.engine` | `rules` | command bar planner: `rules` (built-in German phrase rules, no key) or `claude` (Claude via the Anthropic API; the rules answer when it fails or takes longer than 15 s) |
| `assistant.model` | `claude-opus-5-5` | Claude model for `engine=claude` |
| `assistant.existingSecret` / `.existingSecretKey` | — / `api-key` | Secret holding the Anthropic API key, passed as `ANTHROPIC_API_KEY` (required for `engine=claude`; the pod needs outbound HTTPS to `api.anthropic.com`) |
| `ingress.enabled`, `.className`, `.host`, `.annotations`, `.tls` | on, `traefik`, `kurort.localhost` | standard Ingress settings |
| `resources`, `podSecurityContext`, `securityContext` | small requests, non-root | app pod |
| `postgresql.enabled` | `true` | bundled database |
| `postgresql.auth.username` / `.database` / `.password` | `kurort` / `kurort` / generated | bundled database credentials |
| `postgresql.persistence.size` / `.storageClass` | `2Gi` / default class | bundled database volume |
| `externalDatabase.existingSecret` / `.existingSecretKey` | empty / `uri` | Secret holding the database URL when `postgresql.enabled=false` |
| `externalDatabase.url` | empty | alternatively a URL; the chart creates the Secret |
| `auth.enabled` | `true` | OIDC login (`KURORT_AUTH=oidc`); `false` = no login (`off`), local use only |
| `auth.publicUrl` | `http(s)://<ingress.host>` | browser-facing app URL; redirect URI is `<publicUrl>/auth/callback` |
| `auth.oidc.issuer` | — (required) | public issuer as it appears in tokens |
| `auth.oidc.internalUrl` | = issuer | base the pod uses for discovery, token, JWKS and userinfo calls |
| `auth.oidc.clientId` | `kurort-app` | confidential client |
| `auth.oidc.clientSecret` / `.existingSecret` / `.existingSecretKey` | — / — / `client-secret` | client secret as a value, or a Secret holding it (one is required) |
| `auth.session.existingSecret` / `.existingSecretKey` | — / `session-secret` | cookie-signing key; empty = generated once into `<fullname>-auth` |

With `auth.enabled=true` the render fails fast when the issuer, the client
secret or a public URL is missing. With `assistant.engine=claude` it fails when
`assistant.existingSecret` is missing:

```bash
kubectl -n kurort create secret generic kurort-assistant --from-literal=api-key='<Anthropic API key>'
helm upgrade --install kurort deploy/helm/kurort-engine -n kurort --reuse-values \
  --set assistant.engine=claude --set assistant.existingSecret=kurort-assistant
```

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
- **Authentication.** Point `auth.oidc.*` at the company Keycloak (see
  [below](#using-an-external-or-company-keycloak)); never deploy with
  `auth.enabled=false` outside a laptop.
- **Demo mornings.** Seed data is laid out around the date it was generated.
  Before a demo, reseed so today's arrivals and departures are current:
  `kubectl -n kurort exec deploy/kurort -c web -- kurort-app seed --reset`,
  or deploy with `--set demo.seed=reset` so every pod start reseeds. To show
  the same day every time, pin it with `--set app.today=YYYY-MM-DD`.

## Authentication

The app logs staff in with OpenID Connect: authorization code flow with PKCE
(S256) against a confidential client, then a signed session cookie. Access
needs one of the realm roles `rezeption`, `leitung`, `housekeeping` or `kueche`
in a flat `roles` claim (`realm_access.roles` is the fallback). Front-desk roles
land on the dashboard, `housekeeping` on the room status, `kueche` on the HACCP
app; a signed-in user with none of them gets 403.
The app reads these variables (the chart sets them from `auth.*`):
`KURORT_AUTH`, `KURORT_PUBLIC_URL`, `KURORT_OIDC_ISSUER`,
`KURORT_OIDC_INTERNAL_URL`, `KURORT_OIDC_CLIENT_ID`,
`KURORT_OIDC_CLIENT_SECRET`, `KURORT_SESSION_SECRET`.

### Demo Keycloak on k3d

`deploy/k3d/keycloak` is a small demo chart, not part of the app chart. It
stands in for the customer's company Keycloak: `deploy/k3d/up.sh` installs it on
the local cluster, and it can also carry a demo on a real cluster
([below](#a-public-demo-behind-a-tunnel)). Real staff accounts belong in the
company Keycloak. On k3d:

| | |
|---|---|
| Realm | `hotel-rheinland` ("Hotel Rheinland · Bad Orb"), login pages in German (English selectable) |
| Login / issuer | http://auth.kurort.localhost:8090/realms/hotel-rheinland |
| Admin console | http://auth.kurort.localhost:8090/admin/ — user `admin` |
| Admin password | `kubectl --context k3d-kurort -n kurort get secret keycloak -o jsonpath='{.data.admin-password}' \| base64 -d` |
| Client | `kurort-app`, confidential, standard flow only, PKCE S256 required |
| Client secret | generated once into Secret `keycloak-kurort-app-client` (key `client-secret`); the app release reads the same Secret (`auth.oidc.existingSecret` in `values-k3d.yaml`) |
| Database | own database + role `keycloak` in the app's bundled Postgres, created by an init container |
| Memory | about 0.5 GiB (limit 1 GiB) |

Demo users (fictional), all with the password `Rheinland2026!`
(`demoPassword` in the chart values):

| User | Name | Roles |
|---|---|---|
| `m.schmidt` | Maria Schmidt | `rezeption` |
| `t.weber` | Thomas Weber | `rezeption`, `leitung` |
| `s.klein` | Sandra Klein | `housekeeping` |
| `j.becker` | Jana Becker | `kueche` |
| `k.gast` | Karl Gast | none — shows the app's 403 |

The realm is imported from a ConfigMap on the **first** start only; later
starts keep whatever is in Keycloak's database (`IGNORE_EXISTING`). A post-start
hook re-applies the client secret from the Secret on every start. To re-import
after changing users or client settings, drop the realm (admin console) or the
`keycloak` database and restart the pod.

Keycloak runs in production mode (`start`, as in SRW) with
`KC_HOSTNAME=http://auth.kurort.localhost:8090` and
`KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`. The hostname pins the issuer and the
browser-facing endpoints; the backchannel endpoints follow the request host.
That is why `auth.oidc.internalUrl` can be the in-cluster Service
(`http://keycloak.kurort.svc.cluster.local:8080/realms/hotel-rheinland`): its
discovery document lists token, JWKS and userinfo on the Service while tokens
still carry the public `iss`. Inside a pod, `auth.kurort.localhost` does not
resolve at all, so the public URL is not usable there.

Keycloak marks its login cookies `Secure; SameSite=None` even over plain HTTP.
Browsers accept that on `http://*.localhost` (a secure context), but on any
other plain-HTTP hostname the login fails with "Cookie konnte nicht gefunden
werden" — serve Keycloak over HTTPS anywhere but a laptop.

### A public demo behind a tunnel

A demo on a real cluster that browsers outside the network can reach, for
example through a Cloudflare Tunnel straight to the Services with no Ingress:

1. Pick two HTTPS hostnames, say `app.example.de` and `login.example.de`.
   HTTPS is required: Keycloak's login cookies are `Secure`, and so is the
   app's session cookie when `auth.publicUrl` is `https://`.
2. Install Keycloak first, with a new demo password: the default one is
   published in this repository, and on a public URL anyone could use it.

   ```bash
   helm upgrade --install keycloak deploy/k3d/keycloak -n kurort --create-namespace \
     --set hostname=https://login.example.de \
     --set ingress.enabled=false \
     --set client.appUrl=https://app.example.de \
     --set demoPassword='<new demo password>' \
     --set admin.password='<admin password>'
   ```

3. Then the app. The release names matter: the app reads the client Secret
   `keycloak-kurort-app-client` and calls `keycloak.kurort.svc`, and the
   Keycloak chart expects the app's Postgres as `kurort-postgresql`, which
   `fullnameOverride=kurort` produces.

   ```bash
   helm upgrade --install kurort deploy/helm/kurort-engine -n kurort \
     --set fullnameOverride=kurort \
     --set image.repository=<registry>/kurort-engine --set image.tag=<commit> \
     --set ingress.enabled=false \
     --set auth.publicUrl=https://app.example.de \
     --set auth.oidc.issuer=https://login.example.de/realms/hotel-rheinland \
     --set auth.oidc.internalUrl=http://keycloak.kurort.svc.cluster.local:8080/realms/hotel-rheinland \
     --set auth.oidc.existingSecret=keycloak-kurort-app-client
   ```

4. Route `app.example.de` to Service `kurort` (port 80) and `login.example.de`
   to Service `keycloak` (port 8080), the latter **only** for paths under
   `/realms/` and `/resources/`. That is all the login needs, and it keeps the
   admin console off the internet.

Both charts generate their passwords once and find them again with Helm
`lookup`. That needs `helm upgrade --install` against the cluster; a renderer
without cluster access (some GitOps setups) generates new ones on every
reconcile and breaks the database logins, so supply those values yourself
there. The bundled Postgres has no backups: fine for made-up demo data only.

### Using an external or company Keycloak

Create a client in the company realm:

- Client type OpenID Connect, client authentication **on** (confidential),
  standard flow only (no direct access grants, no implicit flow).
- Advanced → Proof Key for Code Exchange method: **S256**.
- Valid redirect URI `https://<app-host>/auth/callback`, valid post-logout
  redirect URI `https://<app-host>/*`, web origin `https://<app-host>`.
- A protocol mapper "User Realm Role" with token claim name `roles`,
  multivalued, added to the ID token, access token and userinfo.
- Realm roles `rezeption`, `leitung`, `housekeeping` and `kueche`, assigned to
  staff (or via groups).

Then deploy with:

```bash
kubectl -n kurort create secret generic kurort-oidc --from-literal=client-secret='<secret>'
helm upgrade --install kurort deploy/helm/kurort-engine -n kurort \
  --set ingress.host=rezeption.example.de \
  --set auth.publicUrl=https://rezeption.example.de \
  --set auth.oidc.issuer=https://login.example.de/realms/<realm> \
  --set auth.oidc.existingSecret=kurort-oidc
```

Set `auth.oidc.internalUrl` only when the pod cannot reach the public issuer
URL (split DNS, a Keycloak in the same cluster); the IdP must then serve
backchannel endpoints for that host, as Keycloak does with
`hostname-backchannel-dynamic`.

## Docker Compose

For a single machine without Kubernetes, `compose.yaml` runs Postgres and the
app. See [local-development.md](local-development.md#docker-compose).
