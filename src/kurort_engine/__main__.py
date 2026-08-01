"""kurort_engine operator CLI entry point.

Invoked via ``python -m kurort_engine`` (PEP 338) or, after
``pip install -e .[dev]``, via the ``kurort-engine`` CLI binary
(declared in ``[project.scripts]`` of ``pyproject.toml``).

Closes Resavio gap **F1** (no operator-facing entry point) and
satisfies **AC-3** of the F1+F2+F3 bundle per
``iter-8-spec-input-synthesis-f1f2f3-bundle-operator-facing-entry-points``.

Subcommands
-----------

- ``--version`` / ``-V``            prints package version
- ``demo``                         runs the synthetic Bad Orb month demo
- ``version``                      prints the package version (alternative to ``-V``)
- ``meldeschein check-in``         BMG §30 Meldeschein PDF emitter (F5 AC-1)
- ``kurtaxe charge``               per-reservation Kurtaxe ledger (F5 AC-2)
- ``remittance generate``          Hessen KAG 12-column CSV (F5 AC-3)
- ``arrival bundle``               arrival-bundle orchestrator (F5 AC-4)
- ``avv attest``                   DSK-KP13 attestation packet (avv_kaskade AC-3)
- ``avv geeignetheitspruefung``    Geeignetheitspruefung report (avv_kaskade AC-2)
- ``avv version``                  avv_kaskade version + AC status summary
- ``--help`` / ``-h``              prints argparse usage (default)

Exit codes
----------

- 0          success
- non-zero   failure (argparse already returns 2 for unknown args)
"""
from __future__ import annotations

import argparse

import kurort_engine
from kurort_engine import __version__


def _cmd_demo(_args: argparse.Namespace) -> int:
    """Run the synthetic Bad Orb month demo (100 reservations -> CSV)."""
    from kurort_engine.demos import synthetic_bad_orb_month
    return synthetic_bad_orb_month.main()


def _cmd_version(_args: argparse.Namespace) -> int:
    """Print the package version."""
    print(f"kurort_engine {__version__}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with version flag + subcommands (incl. F5 + avv).

    The SHIPPED iter-8 subcommands (``demo``, ``version``) are preserved
    verbatim. The four new F5 Tier-1 subcommands are registered per
    ``spec.yaml:88-152`` AC-1..AC-4; their handler implementations live
    in ``kurort_engine/__init__.py`` and are dispatched to by
    ``kurort_engine.parse_subcommand(argv)`` at the top of ``main``.

    The three new avv_kaskade subcommands (Phase 5 refactor) are registered
    here and dispatched to the `_handle_avv_*` handlers in `__init__.py`.
    """
    parser = argparse.ArgumentParser(
        prog="kurort-engine",
        description=(
            "kurort_engine operator CLI \u2014 Kurort-vertical ERP for "
            "Hotel Rheinland Bad Orb (Hessen KAG, Kurbeitragssatzung "
            "effective 2020-07-01)."
        ),
    )
    parser.add_argument(
        "--version", "-V",
        action="store_true",
        help="Print the package version and exit",
    )
    sub = parser.add_subparsers(dest="subcommand")

    # SHIPPED subcommands (iter-8 F1+F2+F3).
    sub.add_parser(
        "demo",
        help="Run the synthetic Bad Orb month demo (100 reservations -> CSV)",
    )
    sub.add_parser(
        "version",
        help="Print the package version",
    )

    # F5 receptionist-subcommands (iter-16 Phase 4 GREEN).

    # AC-1: meldeschein check-in — stdin JSON, --output-file optional.
    sp_meldeschein = sub.add_parser(
        "meldeschein",
        help="BMG §30 Meldeschein registration form commands (F5 AC-1)",
    )
    sp_meldeschein_sub = sp_meldeschein.add_subparsers(dest="meldeschein_cmd")
    sp_meldeschein_checkin = sp_meldeschein_sub.add_parser(
        "check-in",
        help="Read JSON-stdin Meldeschein, write BMG §30 PDF to --output-file",
    )
    sp_meldeschein_checkin.add_argument(
        "--output-file", default=None,
        help="Output PDF path (default: ./meldeschein.pdf)",
    )

    # AC-2: kurtaxe charge — stdin JSON, no further args.
    sp_kurtaxe = sub.add_parser(
        "kurtaxe",
        help="Kurtaxe commands (F5 AC-2)",
    )
    sp_kurtaxe_sub = sp_kurtaxe.add_subparsers(dest="kurtaxe_cmd")
    sp_kurtaxe_sub.add_parser(
        "charge",
        help="Read JSON-stdin per-reservation payload, print Kurtaxe ledger",
    )

    # AC-3: remittance generate --year --month --output-file.
    sp_remittance = sub.add_parser(
        "remittance",
        help="Hessen KAG monthly remittance commands (F5 AC-3)",
    )
    sp_remittance_sub = sp_remittance.add_subparsers(dest="remittance_cmd")
    sp_remittance_generate = sp_remittance_sub.add_parser(
        "generate",
        help="Generate Hessen KAG 12-column CSV for (year, month) period",
    )
    sp_remittance_generate.add_argument(
        "--year", required=True, help="Calendar year (e.g. 2025)",
    )
    sp_remittance_generate.add_argument(
        "--month", required=True, help="Calendar month, 1-12",
    )
    sp_remittance_generate.add_argument(
        "--output-file", required=True, help="Output CSV path",
    )

    # AC-4: arrival bundle --reservation --output-dir.
    sp_arrival = sub.add_parser(
        "arrival",
        help="Arrival-bundle orchestrator commands (F5 AC-4)",
    )
    sp_arrival_sub = sp_arrival.add_subparsers(dest="arrival_cmd")
    sp_arrival_bundle = sp_arrival_sub.add_parser(
        "bundle",
        help="Write 3-file arrival bundle (Meldeschein PDF + Apple PKPass + Google Wallet JSON)",
    )
    sp_arrival_bundle.add_argument(
        "--reservation", required=True, help="Reservation id (e.g. R-W1-001)",
    )
    sp_arrival_bundle.add_argument(
        "--output-dir", required=True, help="Output directory path",
    )

    # avv_kaskade subcommands (iter-28 Phase 5 refactor).
    sp_avv = sub.add_parser(
        "avv",
        help="DSGVO Art. 28 cascade-audit commands (avv_kaskade — 7/7 ACs green)",
    )
    sp_avv_sub = sp_avv.add_subparsers(dest="avv_cmd")
    sp_avv_sub.add_parser(
        "attest",
        help="Emit DSK-Kurzpapier Nr. 13 attestation packet (AC-3)",
    )
    sp_avv_geeignetheitspruefung = sp_avv_sub.add_parser(
        "geeignetheitspruefung",
        help="Emit Geeignetheitspruefung report for a registered processor (AC-2/AC-2.1)",
    )
    sp_avv_geeignetheitspruefung.add_argument(
        "--processor-id", default="cm-booking-com",
        help="Processor id to report on (default: cm-booking-com)",
    )
    sp_avv_sub.add_parser(
        "version",
        help="Print avv_kaskade version + AC status summary",
    )

    # F5 receptionist-subcommands Tier-2 subparsers (iter-24 Phase 3 GREEN).
    # Nested subparsers pattern matching iter-16 Tier-1 (sp_meldeschein / sp_kurtaxe / etc.).
    sp_rechnung = sub.add_parser(
        "rechnung",
        help="§23 SGB V Badekur Rechnung commands (F5 Tier-2 AC-1)",
    )
    sp_rechnung_sub = sp_rechnung.add_subparsers(dest="rechnung_cmd")
    sp_rechnung_issue = sp_rechnung_sub.add_parser(
        "issue",
        help="Issue a Badekur Rechnung from JSON payload (AC-1)",
    )
    sp_rechnung_issue.add_argument(
        "--input-file",
        default=None,
        help="Path to JSON payload file (alternative to stdin)",
    )

    sp_dsgvo = sub.add_parser(
        "dsgvo",
        help="DSGVO Art. 17 in-house cascade commands (F5 Tier-2 AC-2)",
    )
    sp_dsgvo_sub = sp_dsgvo.add_subparsers(dest="dsgvo_cmd")
    sp_dsgvo_cascade = sp_dsgvo_sub.add_parser(
        "cascade",
        help="Run in-house retention cascade for a guest_id (AC-2)",
    )
    sp_dsgvo_cascade.add_argument(
        "guest_id",
        help="Guest identifier (in-house only)",
    )

    sp_predicate = sub.add_parser(
        "predicate",
        help="Heilbad predicate filing commands (F5 Tier-2 AC-3)",
    )
    sp_predicate_sub = sp_predicate.add_subparsers(dest="predicate_cmd")
    sp_predicate_file = sp_predicate_sub.add_parser(
        "file",
        help="Generate predicate filing packet (AC-3)",
    )
    sp_predicate_file.add_argument(
        "year",
        type=int,
        help="Filing year (e.g. 2026)",
    )
    sp_predicate_file.add_argument(
        "heilbad_code",
        help="Heilbad code (e.g. BAD_ORB)",
    )
    sp_predicate_file.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: cwd)",
    )


    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0 = success, non-zero = error).

    Routes F5 receptionist + avv_kaskade subcommands through
    ``kurort_engine.parse_subcommand`` FIRST; if that function returns an
    int, propagate it. Otherwise fall through to the SHIPPED iter-8
    ``version`` / ``demo`` handlers. This keeps the F5 + avv Tier-1
    wiring isolated from the SHIPPED CLI surface (parse_subcommand is
    the single source of truth for F5 + avv routing).
    """
    # F5 + avv receptionist-subcommands: delegate to the package-level dispatcher
    # FIRST. `parse_subcommand` returns int if matched, None to fall through
    # to the SHIPPED `version`/`demo` handlers below.
    try:
        exit_code = kurort_engine.parse_subcommand(argv)
    except SystemExit:
        # argparse exits via `parser.exit(0)` -> `sys.exit(0)` -> `SystemExit`;
        # argparse will have already printed --help and flushed stdout. Re-raise
        # so the subprocess's exit code is preserved verbatim.
        raise
    if exit_code is not None:
        return exit_code

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return _cmd_version(args)

    if args.subcommand == "demo":
        return _cmd_demo(args)
    if args.subcommand == "version":
        return _cmd_version(args)

    # No subcommand + no --version: argparse already printed usage; print help
    # and exit 0 so `python -m kurort_engine` (no args) still shows the user
    # what they can do.
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())