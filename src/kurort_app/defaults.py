"""Default rows a fresh installation needs: business settings staff edit later.

Payment methods, e-mail templates, seminar room prices and the like are
data, not schema, so migrations do not insert them. A feature lists its
idempotent ``ensure_*`` function here as ``"module:function"``. Each function
inserts only what is missing and never overwrites rows staff have changed.
``kurort-app migrate`` runs them after the upgrade; the demo seed runs them
after a reset.
"""

from __future__ import annotations

import importlib

from sqlalchemy.orm import Session

DEFAULTS: list[str] = [
    "kurort_app.services.seminar:ensure_function_spaces",
    "kurort_app.services.payments:ensure_payment_methods",
]


def ensure_defaults(session: Session) -> None:
    for path in DEFAULTS:
        module, _, name = path.partition(":")
        getattr(importlib.import_module(module), name)(session)
    session.commit()
