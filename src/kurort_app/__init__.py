"""kurort_app — the staff web application on top of ``kurort_engine``.

The engine stays a pure library (tourist tax, Meldeschein, Kurkarte, ...);
this package adds persistence (Postgres via SQLAlchemy/Alembic), an HTTP
surface (FastAPI) and server-rendered screens (Jinja2 + htmx).
"""

__version__ = "0.2.0"
