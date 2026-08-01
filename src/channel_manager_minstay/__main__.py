"""CLI entry point for the channel_manager_minstay package (AC-7).

Enables the invocation:

    python -m channel_manager_minstay push --profile hessen_bad_orb --dry-run

The CLI is a thin wrapper around :class:`MinLosScheduler` that loads the
appropriate MinLOS profile from the package's YAML fixtures and runs the
full push pipeline (Booking.com + HRS).

The CLI has two modes:
    ``--dry-run`` (default): runs the pipeline WITHOUT any network IO and
    prints the captured Booking.com OTA_HotelAvailNotif XML envelope to
    stdout. Exits 0 on success.

    ``--execute``: would push to live Booking.com + HRS endpoints. Per the
    AC-7 contract, this mode is gated on the presence of the
    ``BOOKING_CLIENT_ID`` and ``BOOKING_CLIENT_SECRET`` environment
    variables (so the user never accidentally pushes to a live OTA in
    CI). If the env vars are missing, the CLI prints a structured error
    to stderr and exits 1. If the env vars are present, the CLI raises
    :class:`NotImplementedError` (live push is deferred â out of
    scope for AC-7).
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence


def _parse_profile_name(profile_arg: str) -> tuple[str, str]:
    """Parse a ``<bundesland>_<kurort>`` profile name into its parts.

    The profile name encodes the Bundesland + Kurort pair joined by an
    underscore (e.g. ``hessen_bad_orb`` â ``(hessen, bad_orb)``).
    Multi-word Kurort names are preserved by splitting on the FIRST
    underscore only.

    Examples::

        >>> _parse_profile_name("hessen_bad_orb")
        ("hessen", "bad_orb")
        >>> _parse_profile_name("baden_wuerttemberg_bad_mergentheim")
        ("baden_wuerttemberg", "bad_mergentheim")
    """
    parts = profile_arg.split("_", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid profile name {profile_arg!r}: expected "
            f"'<bundesland>_<kurort>' (e.g. 'hessen_bad_orb')"
        )
    bundesland, kurort = parts
    return (bundesland, kurort)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the CLI.

    The parser uses subcommands so the CLI is extensible (future
    subcommands: ``validate``, ``pull``, etc.). Currently only ``push``
    is implemented.
    """
    parser = argparse.ArgumentParser(
        prog="python -m channel_manager_minstay",
        description=(
            "Kurort-native channel-manager MinLOS push CLI. "
            "Dry-run is the default mode (no network IO)."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    push_parser = subparsers.add_parser(
        "push",
        help="Push MinLOS rules to Booking.com + HRS channels",
    )
    push_parser.add_argument(
        "--profile",
        type=str,
        required=True,
        help=(
            "Profile name in the form '<bundesland>_<kurort>' "
            "(e.g. 'hessen_bad_orb'). The profile YAML must exist at "
            "src/channel_manager_minstay/profiles/<profile>_minlos.yaml."
        ),
    )
    # --execute and --dry-run are mutually exclusive; --execute wins
    # when both are set (matching the AC-7 contract).
    push_parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help=(
            "Push to live Booking.com + HRS endpoints. Requires "
            "BOOKING_CLIENT_ID and BOOKING_CLIENT_SECRET env vars. "
            "Currently raises NotImplementedError (deferred)."
        ),
    )
    push_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help=(
            "Run the pipeline WITHOUT any network IO; print captured "
            "Booking.com XML envelope to stdout. DEFAULT mode."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (AC-7).

    Returns 0 on successful dry-run, 1 on credential-gate failure or
    parser error, or propagates :class:`NotImplementedError` for live
    push (deferred per AC-7 contract).
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.subcommand != "push":
        parser.print_help()
        return 1

    # --execute overrides --dry-run (matches the AC-7 contract).
    dry_run = not args.execute

    # Parse the profile name.
    try:
        bundesland, kurort = _parse_profile_name(args.profile)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Load the profile + run the pipeline.
    from channel_manager_minstay import (
        MinLosScheduler,
        load_minlos_profile,
    )
    profile = load_minlos_profile(bundesland, kurort)
    scheduler = MinLosScheduler()
    result = scheduler.push(profile, dry_run=dry_run)

    # In --execute mode, gate on credentials.
    if args.execute:
        client_id = os.environ.get("BOOKING_CLIENT_ID", "")
        client_secret = os.environ.get("BOOKING_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            print(
                "Error: --execute mode requires BOOKING_CLIENT_ID + "
                "BOOKING_CLIENT_SECRET environment variables",
                file=sys.stderr,
            )
            return 1
        # Env vars are set but live push is deferred.
        raise NotImplementedError(
            "Live push is deferred (out of scope for AC-7). Use --dry-run "
            "to capture the payloads without network IO. Live push will "
            "be implemented in a future iteration per NI-1 (Booking.com "
            "partner onboarding) and NI-2 (HRS Channel Manager agreement)."
        )

    # Dry-run mode: print the captured Booking.com XML envelope to stdout.
    print(result.booking_com_xml)
    return 0


if __name__ == "__main__":
    sys.exit(main())
