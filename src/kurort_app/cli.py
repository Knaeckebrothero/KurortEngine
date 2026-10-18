"""``kurort-app`` operator CLI: wait-db, migrate, seed, serve."""

from __future__ import annotations

import argparse
import os
import sys
import time

from sqlalchemy import text


def _wait_db(timeout: float) -> int:
    from kurort_app.db import get_engine

    deadline = time.monotonic() + timeout
    while True:
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            print("kurort-app: database reachable", flush=True)
            return 0
        except Exception as exc:  # noqa: BLE001
            if time.monotonic() > deadline:
                print(
                    f"kurort-app: database not reachable after {timeout:.0f}s: {exc}",
                    file=sys.stderr,
                )
                return 1
            time.sleep(1)


def _migrate() -> int:
    from kurort_app.db import get_sessionmaker
    from kurort_app.defaults import ensure_defaults
    from kurort_app.migrate import upgrade

    upgrade()
    with get_sessionmaker()() as session:
        ensure_defaults(session)
    print("kurort-app: migrations applied", flush=True)
    return 0


def _seed(if_empty: bool, reset: bool) -> int:
    from kurort_app.db import get_sessionmaker
    from kurort_app.seed import seed_demo_data

    with get_sessionmaker()() as session:
        created = seed_demo_data(session, if_empty=if_empty, reset=reset)
    print(
        f"kurort-app: seed {'created ' + str(created) + ' reservations' if created else 'skipped (data present)'}",
        flush=True,
    )
    return 0


def _serve(host: str, port: int, reload: bool) -> int:
    import uvicorn

    from kurort_app.auth import AuthConfigError, validate_settings
    from kurort_app.config import get_settings

    try:
        validate_settings(get_settings())
    except AuthConfigError as exc:
        print(f"kurort-app: {exc}", file=sys.stderr, flush=True)
        return 2
    uvicorn.run(
        "kurort_app.main:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    return 0


def _apps(args) -> int:
    from pathlib import Path

    from kurort_app.apps.registry import AppRegistry, DefinitionError, load_definition

    registry = AppRegistry()
    if args.apps_cmd == "validate":
        paths = [Path(p) for p in args.paths] if args.paths else list(registry.directories)
        failed = False
        for path in paths:
            files = sorted(path.glob("*.yaml")) if path.is_dir() else [path]
            for file in files:
                try:
                    load_definition(file)
                    print(f"OK {file}")
                except DefinitionError as exc:
                    failed = True
                    print(str(exc))
        return int(failed)
    from kurort_app.apps.models import AppInstallation
    from kurort_app.db import get_sessionmaker

    with get_sessionmaker()() as session:
        if args.apps_cmd == "install":
            app = registry.valid.get(args.slug)
            if app is None:
                print(f"App nicht gefunden: {args.slug}")
                return 1
            from kurort_app.apps.installations import install

            install(session, app)
            session.commit()
            print(f"{app.slug} installiert")
        else:
            for slug, app in registry.valid.items():
                installed = session.get(AppInstallation, slug)
                status = (
                    "Nicht installiert"
                    if installed is None
                    else ("Aktiv" if installed.enabled else "Deaktiviert")
                )
                print(f"{slug}\t{app.version}\t{status}")
            for slug in registry.broken:
                print(f"{slug}\t–\tFehlerhaft")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kurort-app", description="KurortEngine staff web application"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_wait = sub.add_parser("wait-db", help="block until the database answers")
    p_wait.add_argument("--timeout", type=float, default=60.0)
    sub.add_parser("migrate", help="apply database migrations (alembic upgrade head)")
    p_seed = sub.add_parser("seed", help="load demo data (rooms, guests, reservations)")
    p_seed.add_argument(
        "--if-empty", action="store_true", help="skip when reservations already exist"
    )
    p_seed.add_argument("--reset", action="store_true", help="delete all front-desk data first")
    p_serve = sub.add_parser("serve", help="run the web server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    p_serve.add_argument("--reload", action="store_true")
    p_apps = sub.add_parser("apps", help="list, validate or install hotel apps")
    app_sub = p_apps.add_subparsers(dest="apps_cmd", required=True)
    app_sub.add_parser("list")
    p_validate = app_sub.add_parser("validate")
    p_validate.add_argument("paths", nargs="*")
    p_install = app_sub.add_parser("install")
    p_install.add_argument("slug")
    args = parser.parse_args(argv)

    if args.cmd == "apps":
        return _apps(args)

    if args.cmd == "wait-db":
        return _wait_db(args.timeout)
    if args.cmd == "migrate":
        return _migrate()
    if args.cmd == "seed":
        return _seed(args.if_empty, args.reset)
    return _serve(args.host, args.port, args.reload)


if __name__ == "__main__":
    raise SystemExit(main())
