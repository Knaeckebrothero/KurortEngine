"""A local Postgres for running the app where podman is not available.

Starts an embedded server from the ``pgserver`` package (``test-pg`` extra),
keeps its data in ``.pgdata/`` (gitignored) and prints the database URL.
Runs in the foreground; Ctrl+C or ``kill`` stops the server, the data stays.

    .venv/bin/python scripts/dev_postgres.py
    export KURORT_DATABASE_URL=<printed URL>
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

DATA_DIR = Path(__file__).resolve().parent.parent / ".pgdata"
DATABASE = "kurort"


def main() -> int:
    try:
        import pgserver
    except ImportError:
        print('pgserver is missing: pip install -e ".[web,dev,test-pg]"', file=sys.stderr)
        return 1
    # Stopped explicitly below: pgserver's own reference counting keeps the
    # server running forever once a previous run was killed without cleanup.
    server = pgserver.get_server(DATA_DIR, cleanup_mode=None)
    socket_dir = make_url(server.get_uri()).query["host"]
    url = f"postgresql+psycopg://postgres@/{DATABASE}?host={socket_dir}"
    admin = create_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": DATABASE}):
            conn.execute(text(f'CREATE DATABASE "{DATABASE}"'))
    admin.dispose()
    print(f"KURORT_DATABASE_URL={url}", flush=True)
    # A background job ignores SIGINT by default, so install both handlers.
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while True:
            time.sleep(3600)
    finally:
        pgserver.pg_ctl(["-w", "-m", "fast", "stop"], pgdata=DATA_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
