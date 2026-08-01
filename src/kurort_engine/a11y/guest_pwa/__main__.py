"""PEP 338 CLI entry point for kurort_engine.a11y.guest_pwa (BFSG-EAA §3(1)).

Invoked via:
  * ``python -m kurort_engine.a11y.guest_pwa`` (PEP 338, in-repo)
  * ``guest-pwa`` (after ``pip install -e .[dev]`` registers the
    ``[project.scripts] guest-pwa = "kurort_engine.a11y.guest_pwa.__main__:main"``
    console-script entry point — see ``repo/pyproject.toml``).

Per ``spec/a11y_guest_pwa/spec.yaml`` AC-3 EARS, this entry point shall:
  1. print ``kurort_engine.a11y.guest_pwa <SELF_ATTESTATION_TS> (WCAG 2.1 AA,
     EN 301 549 V3.2.1, BFSG-EAA §3(1) self-attestation tenant)`` to stdout,
  2. append exactly one ``AuditEntry`` with ``actor="a11y.guest_pwa.cli"`` and
     ``payload`` containing ``{"event": "cli_invocation", "ts":
     <SELF_ATTESTATION_TS>}`` to the SHIPPED
     ``kurort_engine.audit.AuditLog._shared_entries`` singleton,
  3. exit 0 on success.

``BFSGComplianceError`` is caught and converted to exit 1 (graceful failure
mode per spec.yaml AC-3 implicit contract — no stack trace to operators).
"""
from __future__ import annotations

import sys

# Local package import — this also triggers the package-level
# SELF_ATTESTATION_TS constant + first-import audit-log self_attestation event
# defined in ``kurort_engine.a11y.guest_pwa.__init__``.
from kurort_engine.a11y.guest_pwa import (
    SELF_ATTESTATION_TS,
    BFSGComplianceError,
)
from kurort_engine.audit import AuditEntry, AuditLog


def main() -> int:
    """PEP 338 entry point. Returns process exit code (0 success, 1 error)."""
    try:
        # Post-condition 1: print the self-attestation banner to stdout.
        print(
            f"kurort_engine.a11y.guest_pwa {SELF_ATTESTATION_TS} "
            "(WCAG 2.1 AA, EN 301 549 V3.2.1, BFSG-EAA §3(1) "
            "self-attestation tenant)"
        )

        # Post-condition 2: append exactly one cli_invocation AuditEntry.
        # ``AuditLog`` is a SHIPPED (iter-12) class-level append-only store.
        # ``AuditEntry`` is a SHIPPED (iter-12) ``frozen=True`` +
        # ``kw_only=True`` dataclass — content_hash is auto-computed in
        # ``__post_init__`` from canonical-JSON of
        # ``(recorded_at, actor, payload)`` per AuditEntry contract.
        AuditLog._shared_entries.append(  # type: ignore[attr-defined]
            AuditEntry(
                actor="a11y.guest_pwa.cli",
                payload={
                    "event": "cli_invocation",
                    "ts": SELF_ATTESTATION_TS,
                },
            )
        )

        # Post-condition 3: exit 0 on success.
        return 0
    except BFSGComplianceError as exc:
        # Graceful failure: convert domain error to exit 1 with a short
        # operator-facing message (no stack trace, no internal paths).
        print(f"BFSG-EAA compliance failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())