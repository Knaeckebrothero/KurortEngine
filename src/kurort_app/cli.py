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
    from kurort_app.migrate import upgrade

    upgrade()
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

    uvicorn.run(
        "kurort_app.main:app",
        host=host,
        port=port,
        reload=reload,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
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
    args = parser.parse_args(argv)

    if args.cmd == "wait-db":
        return _wait_db(args.timeout)
    if args.cmd == "migrate":
        return _migrate()
    if args.cmd == "seed":
        return _seed(args.if_empty, args.reset)
    return _serve(args.host, args.port, args.reload)


if __name__ == "__main__":
    raise SystemExit(main())
