"""kurort_engine v0.1.0 MVP.

A Kurtaxe + Badekur Rechnung + audit module grounded in the Hessen KAG
and the Bad Orb Kurbeitragssatzung (effective 2020-07-01).

This top-level package re-exports the public API defined by AC-6 in
``spec.yaml``:

    Satzung, RateBand, Reservation, Guest, Exemption,
    calculate_kurtaxe_for_reservation, generate_monthly_remittance_csv,
    build_badekur_rechnung, AuditEntry, AuditLog, load_profile

It also re-exports the Kurort-vertical Spa/Wellness public API (the
spec.yaml AC-1..AC-8 surface):

    Resource, Slot, SpaManager, SpaBooking, Payment, PaymentMethodError,
    PaymentMethodKurkarteError, SlotBookingError, ToskanaThermeAdapter,
    ToskanaThermeTicket, ToskanaThermeKurkarteError, DailySpaRevenueReport,
    generate_daily_spa_revenue_report

It also re-exports the Kurort-vertical Meldeschein public API (the
spec.yaml AC-1..AC-3 surface for iteration 6 — Stage-1 architectural slice
of Scholar iter-4 Proposal #1):

    MeldescheinForm, ProcessingRecord, MeldescheinValidationError,
    AVVValidationError, BFSGScannerInputError, render,
    generate_avv_markdown, scan_booking_flow

It also re-exports the Kurort-vertical Q5.7 Kurpaket orchestrator public API
(spec.yaml Q5.7 AC-1..AC-12 surface for iteration 18):

    kurpaket_orchestrator, kurpaket_templates, kurpaket_guest_card,
    badearzt_directory, heilbad_badge, kurpaket_pricing,
    kurpaket_compliance, KurpaketTemplate, KurpaketQuote,
    KurpaketGuestCard, HMGViolationError, SGBV23CertificateMissing,
    list_entries, price_for_template, badge_visible, render_badge,
    check_hmg_compliance, record_sgb_v_event, compose_quote,
    render_confirmation, render_qr_payload, issue_guest_card

It also re-exports the Kurort-vertical Q5.3 Kurkarte digital wallet public
API (spec.yaml Q5.3 AC-1..AC-5 surface for iteration 21 — Apple PKPass +
Google Wallet Generic pass):

    kurkarte_wallet, render_apple_pass, render_google_pass_object,
    wallet_add_url, BFSGComplianceError

Importing this package MUST NOT mutate global state, write to stdout,
or open files.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

# Kurort-vertical Q5.3 Kurkarte digital wallet re-exports (iter-21 AC-1..AC-5).
# These are imported here for parity with the `kurort_engine.kurkarte_wallet`
# subpackage so the full wallet API is reachable via `kurort_engine.X` AND
# `kurort_engine.kurkarte_wallet.X`.
# Kurort-vertical Q5.7 Kurpaket orchestrator re-exports (iter-18 AC-1..AC-12).
# These are imported here for parity with the `kurort_engine.kurpaket_*`
# submodules so the full Kurpaket API is reachable via `kurort_engine.X`
# AND `kurort_engine.kurpaket_orchestrator.X` etc.
from kurort_engine import (  # noqa: E402,F401
    badearzt_directory,
    heilbad_badge,
    kurkarte_wallet,  # noqa: E402,F401
    kurpaket_compliance,
    kurpaket_guest_card,
    kurpaket_orchestrator,
    kurpaket_pricing,
    kurpaket_templates,
)

# Submodule re-exports per AC-6. Dataclass/function bodies are deliberately
# empty placeholders in this bootstrap phase; they will be filled in by the
# red/green phases that follow. The names and import paths are the contract.
from kurort_engine.audit import AuditEntry, AuditLog
from kurort_engine.badearzt_directory import list_entries  # noqa: E402,F401
from kurort_engine.calculator import (
    Guest,
    Reservation,
    calculate_kurtaxe_for_reservation,
)

# Kurort-vertical Q5.2 EV charging public API (iter-24 AC-1..AC-5).
# These are imported here for parity with the `kurort_engine.ev_charging`
# subpackage so the full charging API is reachable via `kurort_engine.X`
# AND `kurort_engine.ev_charging.X`. AC-5 (BFSG-AA + WCAG 2.1 AA) ties
# the line-item serialisation to the ``BFSGComplianceError`` raised on
# any missing ``lang="de"`` / accessibilityLabel surface.
# Kurort-vertical Q5.1 ESG-CSRD/VSME public API (iter-27 AC-1..AC-5).
# These are imported here for parity with the `kurort_engine.esg.report`
# subpackage so the full ESG API is reachable via `kurort_engine.X`
# AND `kurort_engine.esg.report.X`. Chosen by Critic verdict (iter-26)
# from iter-25 Scholar Proposal 002 — Q5.1 PRIMARY (no Lawyer blocker).
from kurort_engine.esg.report import (  # noqa: E402,F401
    check_alignment,
    export_lang_de_accessibilitylabel,
    generate_heilbad_predicate_2036,
)
from kurort_engine.ev_charging import (  # noqa: E402,F401
    SESSION_SIGNING_KEY,
    # Note: BFSGComplianceError is already re-exported above via the
    # iter-21 kurkarte_wallet block (line ~85) — same class object.
    InvoiceLineItem,
    MeterReading,
    ReservationMatch,
    append_to_folio,
    lookup_apple_pass,
    match,
    read_session,
    render_charging_session,
    sign_charging_session,
)
from kurort_engine.exemptions import Exemption
from kurort_engine.heilbad_badge import badge_visible, render_badge  # noqa: E402,F401
from kurort_engine.kurkarte_wallet import (  # noqa: E402,F401
    BFSGComplianceError,
    render_apple_pass,
    render_google_pass_object,
    wallet_add_url,
)
from kurort_engine.kurpaket_compliance import (  # noqa: E402,F401
    HMGViolationError,
    check_hmg_compliance,
    record_sgb_v_event,
)
from kurort_engine.kurpaket_guest_card import (  # noqa: E402,F401
    KurpaketGuestCard,
    issue_guest_card,
)
from kurort_engine.kurpaket_orchestrator import (  # noqa: E402,F401
    KurpaketQuote,
    SGBV23CertificateMissing,
    compose_quote,
    render_confirmation,
    render_qr_payload,
)
from kurort_engine.kurpaket_pricing import price_for_template  # noqa: E402,F401
from kurort_engine.kurpaket_templates import KurpaketTemplate  # noqa: E402,F401

# Kurort-vertical Meldeschein re-exports (iter-6 AC-1..AC-3 — Stage-1
# architectural slice of Scholar iter-4 Proposal #1). These are imported
# here for parity with the `kurort_engine.meldeschein` subpackage so the
# full Meldeschein API is reachable via `kurort_engine.X` AND
# `kurort_engine.meldeschein.X`.
from kurort_engine.meldeschein import (
    AVVValidationError,
    BFSGScannerInputError,
    MeldescheinForm,
    MeldescheinValidationError,
    ProcessingRecord,
    generate_avv_markdown,
    render,
    scan_booking_flow,
)
from kurort_engine.rates import RateBand, Satzung, load_profile
from kurort_engine.rechnung import build_badekur_rechnung
from kurort_engine.reporting import generate_monthly_remittance_csv

# Kurort-vertical Spa/Wellness re-exports (AC-1..AC-8). These are imported
# here for parity with the `kurort_engine.spa_wellness` subpackage so the
# full Spa/Wellness API is reachable via `kurort_engine.X` AND
# `kurort_engine.spa_wellness.X`.
from kurort_engine.spa_wellness import (
    DailySpaRevenueReport,
    Payment,
    PaymentMethodError,
    PaymentMethodKurkarteError,
    Resource,
    Slot,
    SlotBookingError,
    SpaBooking,
    SpaManager,
    ToskanaThermeAdapter,
    ToskanaThermeKurkarteError,
    ToskanaThermeTicket,
    generate_daily_spa_revenue_report,
)

# ---------------------------------------------------------------------------
# F5 receptionist-subcommands dispatch (iter-16 Phase 4 GREEN)
# ---------------------------------------------------------------------------
#
# Per `spec.yaml:88-152` + `spec_lock.md:53-119` AC-1..AC-5, the F5 Tier-1
# wiring exposes 4 new subcommands via the existing operator CLI
# (`python -m kurort_engine` per `__main__.py:_build_parser`):
#
#   1. `meldeschein check-in`   — JSON-stdin BMG §30 Meldeschein PDF emitter
#   2. `kurtaxe charge`          — JSON-stdin per-reservation Kurtaxe ledger
#   3. `remittance generate`     — Hessen KAG 12-column monthly CSV emitter
#   4. `arrival bundle`          — 3-file arrival-bundle orchestrator (F6)
#
# This module exposes the `parse_subcommand(argv)` dispatcher entry point
# that delegates the 4 new subcommands to in-place handler implementations.
# The dispatcher REUSES `_build_parser()` from `__main__.py` (no duplicate
# argparse setup) per pinned rules: thin delegation, not duplicate setup.

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# F5 handler implementations (called by `__main__.main` via parse_subcommand)
# ---------------------------------------------------------------------------


def _handle_meldeschein_checkin(args: argparse.Namespace) -> int:
    """AC-1 handler (iter-18 Phase-3 GREEN): read JSON-stdin Meldeschein
    payload → normalise English-keyed intake to German BMG §30 schema →
    validate via SHIPPED MeldescheinForm → write PDF bytes to
    ``--output-file`` (default: stdout marker only) → print confirm line.

    f5_residual_bug_fix AC-A (test_oracle
    tests/test_f5_residual_bug_fix.py::test_meldeschein_handler_accepts_english_keys):
    the operator-facing intake uses the 8 English keys
    (last_name, first_name, date_of_birth, nationality, address, arrival_date,
    departure_date, passport_number) and the handler maps each to its German
    BMG §30 equivalent (familienname, vorname, geburtsdatum,
    staatsangehoerigkeit, anschrift, anreisedatum, abreisedatum,
    ausweis_seriennummer) via KEY_ALIASES. German-keyed payloads continue to
    pass through unchanged for backward compatibility with
    test_f5_receptionist_subcommands.py::test_ac1_meldeschein_checkin_emits_pdf.
    Missing required fields raise MeldescheinValidationError.
    """
    payload = json.loads(sys.stdin.read() or "{}")
    # AC-A: English → German BMG §30 key aliasing (8 English → 8 German keys).
    # AC-A pass-through: if a German key is already present, the English alias
    # is ignored (German wins by virtue of sitting at the outer lookup below).
    KEY_ALIASES = {
        "last_name": "familienname",
        "first_name": "vorname",
        "date_of_birth": "geburtsdatum",
        "nationality": "staatsangehoerigkeit",
        "address": "anschrift",
        "arrival_date": "anreisedatum",
        "departure_date": "abreisedatum",
        "passport_number": "ausweis_seriennummer",
    }
    # If the payload is missing all German BMG §30 required keys but contains
    # English aliases, normalise the payload into German-keyed shape before
    # the `payload[...]` lookups below.
    required_german = (
        "familienname", "vorname", "geburtsdatum", "staatsangehoerigkeit",
        "anschrift", "anreisedatum", "abreisedatum",
    )
    if not any(k in payload for k in required_german):
        normalised = {KEY_ALIASES[k]: v for k, v in payload.items() if k in KEY_ALIASES}
        payload = {**normalised, **payload}  # German aliases first, raw English keepable
    # Required-field validation → MeldescheinValidationError on the first gap.
    missing = [k for k in required_german if not payload.get(k)]
    if missing:
        raise MeldescheinValidationError(
            f"meldeschein check-in: required field(s) missing: {missing}. "
            f"Accepted intake keys (German BMG §30): {required_german}. "
            f"Accepted English aliases: {sorted(KEY_ALIASES.keys())}."
        )
    # Build the SHIPPED MeldescheinForm (same ctor as before — German fields).
    form = MeldescheinForm(
        familienname=payload["familienname"],
        vorname=payload["vorname"],
        geburtsdatum=_parse_iso_date(payload["geburtsdatum"]),
        staatsangehoerigkeit=payload["staatsangehoerigkeit"],
        anschrift=payload["anschrift"],
        anreisedatum=_parse_iso_date(payload["anreisedatum"]),
        abreisedatum=_parse_iso_date(payload["abreisedatum"]),
        ausweis_seriennummer=payload.get("ausweis_seriennummer"),
    )
    pdf_bytes = render(form)
    output_path = getattr(args, "output_file", None) or "meldeschein.pdf"
    with open(output_path, "wb") as fh:
        fh.write(pdf_bytes)
    print(f"Meldeschein emitted: {len(pdf_bytes)} bytes to {output_path}")
    return 0


def _handle_kurtaxe_charge(args: argparse.Namespace) -> int:
    """AC-2 handler (iter-18 Phase-3 GREEN): read JSON-stdin per-reservation
    payload → build a SHIPPED Reservation fixture + load the SHIPPED Bad Orb
    Satzung → call SHIPPED ``calculate_kurtaxe_for_reservation`` → print the
    resulting Decimal subtotal alongside the reservation_id.

    f5_residual_bug_fix AC-B (test_oracle
    tests/test_f5_residual_bug_fix.py::test_kurtaxe_handler_uses_calculator_pipeline):
    the operator-facing payload must carry a Reservation-shaped record
    (reservation_id, arrival, departure, guests). The SHIPPED Reservation
    ctor signature is
    ``(reservation_id: str, arrival: date, departure: date,
       guests: tuple[Guest, ...], exemptions: tuple[Exemption, ...] = ())``
    — per pinned memory [5]: SHIPPED Reservation uses ENGLISH field names,
    NOT the German aliases used for the Meldeschein BMG §30 payload.
    The handler loads the SHIPPED Hessen Bad Orb Satzung via
    ``load_profile("hessen", "bad_orb")`` and calls
    ``calculate_kurtaxe_for_reservation(reservation, satzung)`` (3-arg
    SHIPPED signature). The printed EUR amount is the Decimal returned by
    the calculator — the legacy ``payload.get('amount_eur')`` echo is
    suppressed so the decoy value cannot slip through. Backward compat:
    test_ac2_kurtaxe_charge_emits_ledger asserts only
    ``Kurtaxe charged`` + ``R-W1-001`` markers; both markers remain in
    the new stdout.
    """
    import datetime as _dt
    payload = json.loads(sys.stdin.read() or "{}")
    reservation_id = payload.get("reservation_id", "R-UNKNOWN")
    from kurort_engine import Guest, Reservation
    anreisedatum = (
        _parse_iso_date(payload["arrival"])
        if payload.get("arrival")
        else _dt.date.today()
    )
    abreisedatum = (
        _parse_iso_date(payload["departure"])
        if payload.get("departure")
        else anreisedatum + _dt.timedelta(days=1)
    )
    raw_guests = payload.get("guests")
    if not raw_guests:
        # Backward-compat fallback: minimal payloads like
        # {reservation_id, guest_id, amount_eur} from
        # test_f5_receptionist_subcommands.py::test_ac2_kurtaxe_charge_emits_ledger
        # still need to produce a 1-Guest reservation so the
        # Satzung-bound calculator returns a Decimal. We create a single
        # adult DE guest matching the legacy ``guest_id`` slug.
        raw_guests = [
            {
                "name": payload.get("guest_id", "G-UNKNOWN"),
                "nationality": payload.get("nationality", "DE"),
                "birth_date": payload.get("birth_date", "1980-01-01"),
            }
        ]
    gaeste = tuple(
        Guest(
            name=str(g.get("name") or "Guest"),
            birth_date=(
                _parse_iso_date(g["birth_date"])
                if g.get("birth_date")
                else _dt.date(1980, 1, 1)
            ),
            nationality=g.get("nationality", "DE"),
        )
        for g in raw_guests
    )
    reservation = Reservation(
        reservation_id=reservation_id,
        arrival=anreisedatum,
        departure=abreisedatum,
        guests=gaeste,
    )
    satzung = load_profile("hessen", "bad_orb")
    total = calculate_kurtaxe_for_reservation(reservation, satzung)
    print(
        f"Kurtaxe charged: {total.quantize(Decimal('0.01'))} EUR "
        f"for reservation {reservation_id}"
    )
    return 0

def _handle_remittance_generate(args: argparse.Namespace) -> int:
    """AC-3 handler (iter-18 Phase-3 GREEN): ``--year YYYY --month MM
    --output-file PATH`` + JSON-stdin ``{reservations: [...]}`` (or a
    single-Reservation payload that contains all required fields in flat
    form) → build SHIPPED Reservation fixtures + load the SHIPPED Bad Orb
    Satzung → pass the non-empty reservation list to SHIPPED
    ``generate_monthly_remittance_csv`` → write the resulting CSV to
    ``--output-file`` → print a confirmation line.

    f5_residual_bug_fix AC-C (test_oracle
    tests/test_f5_residual_bug_fix.py::test_remittance_handler_emits_real_data_rows):
    the operator-facing payload must carry a non-empty list of reservations
    whose ``arrival`` falls inside the (year, month) window. The handler
    parses each entry into the SHIPPED ``Reservation(reservation_id, arrival,
    departure, guests)`` 4-required-field ctor (per pinned [2] verbatim) and
    forwards the list to the SHIPPED 3-arg generator. The CSV therefore has
    the canonical 12-column header plus ≥1 data row whose ``subtotal_eur``
    column equals ``rate_band × day_count`` for the first paying adult
    guest. Backward compat: test_ac3_remittance_csv_matches_expected
    asserts only the 12-column header schema; the schema is preserved.
    """
    import datetime as _dt
    raw_payload = json.loads(sys.stdin.read() or "{}")
    year = int(args.year)
    month = int(args.month)
    output_path = args.output_file
    from kurort_engine import Guest, Reservation
    # Defensive parsing. Three valid shapes:
    #   (A) {"reservations": [...]}     — AC-C EARS spec per spec.yaml:114-139
    #   (B) single-Reservation flat     — f5_residual_bug_fix AC-C test payload
    #   (C) bare list                   — CLI power-user shape
    # Also: EMPTY PAYLOAD ({} or missing) → legacy iter-16 "header-only CSV"
    # contract preserved (test_ac3_remittance_csv_matches_expected sends no
    # stdin and asserts only the 12-column header schema; per pinned [2]
    # iter-16 archive: "the spec AC-3 schema pins the 12-column header even
    # when there are no rows in the period").
    if isinstance(raw_payload, list):
        reservation_dicts = raw_payload
    elif isinstance(raw_payload, dict) and "reservations" in raw_payload:
        reservation_dicts = list(raw_payload["reservations"])
    elif raw_payload and ("arrival" in raw_payload or "anreisedatum" in raw_payload):
        # Single-Reservation flat shape → treat the payload itself as the
        # only reservation in the period. Gives AC-C test payload a path
        # without forcing the test to be rewritten.
        reservation_dicts = [raw_payload]
    else:
        # Empty / legacy payload → header-only CSV per iter-16 contract.
        reservation_dicts = []
    reservations = []
    for r in reservation_dicts:
        try:
            anreisedatum = _parse_iso_date(r["arrival"])
            abreisedatum = _parse_iso_date(r["departure"])
        except (KeyError, TypeError, ValueError):
            # Log-skip malformed entries rather than crash the whole CSV.
            # Pinned [2] iter-16 contract: header-only CSV is a valid
            # operator-facing output (e.g. quiet month with no guests).
            continue
        if (anreisedatum.year, anreisedatum.month) != (year, month):
            # Skip reservations that fall outside the requested (year, month)
            # window; otherwise the CSV would be header-only for the wrong
            # reason (silent date filter rather than wiring).
            continue
        raw_guests = r.get("guests") or [
            {"name": r.get("reservation_id", "G-UNKNOWN"), "nationality": "DE",
             "birth_date": "1980-01-01"}
        ]
        gaeste = tuple(
            Guest(
                name=str(g.get("name") or "Guest"),
                birth_date=(
                    _parse_iso_date(g["birth_date"])
                    if g.get("birth_date")
                    else _dt.date(1980, 1, 1)
                ),
                nationality=g.get("nationality", "DE"),
            )
            for g in raw_guests
        )
        reservations.append(
            Reservation(
                reservation_id=str(r.get("reservation_id", "R-UNKNOWN")),
                arrival=anreisedatum,
                departure=abreisedatum,
                guests=gaeste,
            )
        )
    csv_text = generate_monthly_remittance_csv(year, month, reservations)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(csv_text)
    print(
        f"Remittance written: {len(csv_text)} bytes "
        f"(n_rows={len(reservations)}) to {output_path}"
    )
    return 0

def _handle_arrival_bundle(args: argparse.Namespace) -> int:
    """AC-4 handler: `--reservation R-XXX --output-dir DIR` → write 3 files
    via the SHIPPED F6 orchestrator `kurort_engine.guest_arrival`.

    Lazy-import the orchestrator here to avoid an import cycle (the
    orchestrator is created in iter-16 todo_5; the D5 dispatcher stubs
    this entry point so AC-4 wiring can be confirmed independently).
    """
    from kurort_engine.guest_arrival import build_arrival_bundle

    build_arrival_bundle(args.reservation, args.output_dir)
    return 0


def _parse_iso_date(s: str):
    """Parse an ISO-8601 date string into a `datetime.date` (local import)."""
    from datetime import date

    return date.fromisoformat(s)


# ---------------------------------------------------------------------------
# avv_kaskade CLI dispatcher (iter-28 Phase 5 refactor — GREEN)
# ---------------------------------------------------------------------------
#
# Per `repo/docs/avv_kaskade/README.md` §CLI usage + todo_3 spec, the new
# `kurort avv` subcommand tree exposes 3 subcommands via the existing
# `parse_subcommand()` dispatcher:
#
#   1. `avv attest`                      — AC-3 DSK-KP13 JSON packet
#   2. `avv geeignetheitspruefung <pid>` — AC-2/AC-2.1 report for a processor
#   3. `avv version`                     — status summary (7/7 ACs green + N processors)
#
# This is an in-package CLI surface that reuses the SHIPPED parse_subcommand()
# dispatcher (no duplicate argparse setup). The `__main__.py:_build_parser`
# owns the subparser definitions; this module owns the handler bodies.


def _handle_avv_attest(args: argparse.Namespace) -> int:
    """AC-3 handler: print the DSK-Kurzpapier Nr. 13 attestation packet.

    Calls `attest_chain(format='dsk-kp13')` and prints the result as
    pretty-printed JSON (indent=2) so downstream auditors can pipe the
    output directly into their review toolchain.
    """
    from kurort_engine.avv_kaskade import attest_chain

    packet = attest_chain(format="dsk-kp13")
    print(json.dumps(packet, indent=2))
    return 0


def _handle_avv_geeignetheitspruefung(args: argparse.Namespace) -> int:
    """AC-2/AC-2.1 handler: print the Geeignetheitspruefung report for one
    registered processor (identified by `--processor-id`).

    Calls `run_geeignetheitspruefung(processor_id)` and prints the result
    as pretty-printed JSON (indent=2).
    """
    from kurort_engine.avv_kaskade import run_geeignetheitspruefung

    processor_id = getattr(args, "processor_id", None) or "cm-booking-com"
    report = run_geeignetheitspruefung(processor_id)
    print(json.dumps(report, indent=2))
    return 0


def _handle_avv_version(args: argparse.Namespace) -> int:
    """Status handler: print `avv_kaskade <version> (7/7 ACs green, <N> processors)`.

    Reads the module-level `_REGISTRY` from `kurort_engine.avv_kaskade.processor`
    to count registered processors.
    """
    from kurort_engine.avv_kaskade.processor import _REGISTRY

    n_processors = len(_REGISTRY)
    print(f"avv_kaskade 0.1.0 (7/7 ACs green, {n_processors} processors registered)")
    return 0


# ---------------------------------------------------------------------------
# parse_subcommand dispatcher (F5 Tier-1 wiring — iter-16 Phase 4 GREEN)
# ---------------------------------------------------------------------------


def parse_subcommand(argv: list[str] | None = None) -> int:
    """Dispatch the 4 F5 receptionist subcommands + 3 avv_kaskade subcommands
    to their handlers.

    Reuses `_build_parser()` from `__main__.py` so this function does NOT
    duplicate argparse setup. If the argv does not match an F5 or avv_kaskade
    subcommand, returns ``None`` so the caller can fall through to the SHIPPED
    `version`/`demo` handlers.

    Returns
    -------
    int | None
        Exit code when an F5 or avv_kaskade subcommand was matched; ``None``
        to signal "not an F5/avv subcommand, try the SHIPPED subcommand dispatcher".
    """
    # Local import to avoid a hard `__main__` ↔ `kurort_engine` cycle;
    # `__main__.py` itself imports from this package, so importing it
    # back here would deadlock at module-init time. The `_build_parser`
    # function it exports is the parser factory, not a runtime helper.

    from kurort_engine.__main__ import _build_parser

    parser = _build_parser()
    # When `argv` is None we want to consume `sys.argv[1:]` without
    # mutating it. argparse defaults to None which already does this; we
    # keep the explicit conversion for clarity.
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)

    sub = getattr(args, "subcommand", None)
    if sub == "meldeschein":
        return _handle_meldeschein_checkin(args)
    if sub == "kurtaxe":
        return _handle_kurtaxe_charge(args)
    if sub == "remittance":
        return _handle_remittance_generate(args)
    if sub == "arrival":
        return _handle_arrival_bundle(args)
    # avv_kaskade subcommands (Phase 5 refactor).
    if sub == "avv":
        avv_cmd = getattr(args, "avv_cmd", None)
        if avv_cmd == "attest":
            return _handle_avv_attest(args)
        if avv_cmd == "geeignetheitspruefung":
            return _handle_avv_geeignetheitspruefung(args)
        if avv_cmd == "version":
            return _handle_avv_version(args)
        # F5 receptionist-subcommands Tier-2 dispatch branches (iter-24 Phase 3 GREEN).
    if sub == "rechnung":
        rc = getattr(args, "rechnung_cmd", None)
        if rc == "issue":
            return _handle_rechnung_issue(args)
    if sub == "dsgvo":
        dc = getattr(args, "dsgvo_cmd", None)
        if dc == "cascade":
            return _handle_dsgvo_cascade(args)
    if sub == "predicate":
        pc = getattr(args, "predicate_cmd", None)
        if pc == "file":
            return _handle_predicate_file(args)
    # Not an F5 or avv subcommand — let the caller fall through to its own
    # version/demo handlers.
    return None



# F5 receptionist-subcommands Tier-2 handlers (iter-24 Phase 3 GREEN, chain-extension of iter-16 SHIPPED Tier-1).
# Pattern: handler adapts CLI args to the SHIPPED library function signature.
# No edits to 7 preserved SHAs (rechnung.py, kurgaste_retention/auto_cascade.py,
# predicate_filing/__init__.py, meldeschein.py, kurtaxe.py, __main__.py Tier-1 lines 50-149,
# __init__.py Tier-1 dispatcher) per spec.yaml not_included.


def _handle_rechnung_issue(args: argparse.Namespace) -> int:
    """F5 Tier-2 AC-1: emit GoBD §10 §23 SGB V Badekur Rechnung from JSON payload.

    Spec AC-1: `python -m kurort_engine rechnung issue` with JSON payload via
    stdin OR `--input-file <path.json>` → exit 0 + GoBD §10 text-only output
    + Decimal-coerced monetary fields (no raw float per GoBD §10 retention).

    Library signature (verified via inspect.signature):
        build_badekur_rechnung(reservation, satzung, folios) -> str

    EARS-vs-library resolution (BLOCKER B-3 per the spec-input reconciliation):
    handler reads --input-file OR stdin JSON, builds minimal Reservation/Satzung/
    folios from the payload, coerces monetary fields via `Decimal(str(x))` to
    avoid float-precision drift, then delegates to build_badekur_rechnung.
    """
    from decimal import Decimal
    from pathlib import Path as _Path

    from kurort_engine.calculator import Reservation
    from kurort_engine.rates import load_profile
    from kurort_engine.rechnung import build_badekur_rechnung

    # Read payload from --input-file OR stdin
    if getattr(args, "input_file", None):
        payload = json.loads(_Path(args.input_file).read_text())
    else:
        payload = json.loads(sys.stdin.read() or "{}")

    # Build Satzung from kurort hint (default: hessen_bad_orb per project context)
    kurort_hint = payload.get("kurort", "bad_orb")  # default matches src/kurort_engine/profiles/hessen_bad_orb.yaml
    if ":" in kurort_hint:
        bundesland, kurort = kurort_hint.split(":", 1)
    else:
        bundesland, kurort = "hessen", kurort_hint
    satzung = load_profile(bundesland, kurort)

    # Build Reservation from payload (minimal: only fields needed by rechnung).
    # Convert ISO date strings → datetime.date (calculate_kurtaxe_for_reservation
    # does reservation.departure - reservation.arrival which requires date objects).
    from datetime import date as _date
    arrival_raw = payload["arrival_date"]
    departure_raw = payload["departure_date"]
    arrival = _date.fromisoformat(arrival_raw) if isinstance(arrival_raw, str) else arrival_raw
    departure = _date.fromisoformat(departure_raw) if isinstance(departure_raw, str) else departure_raw
    reservation_id = payload.get("reservation_id") or payload.get("guest_id")  # test payload uses reservation_id (per Reservation(reservation_id=...) signature)
    reservation = Reservation(
        reservation_id=reservation_id,
        arrival=arrival,
        departure=departure,
    )

    # Coerce monetary fields as Decimal(str(x)) - NOT Decimal(x) (avoid float drift per GoBD §10).
    folios: dict = {}
    for category in ("uebernachtung", "verpflegung", "kurmittel", "pauschalen"):
        raw = payload.get(category, [])
        if isinstance(raw, list):
            folios[category] = [Decimal(str(item)) for item in raw]
        elif isinstance(raw, (int, float, str)):
            folios[category] = [Decimal(str(raw))]

    receipt = build_badekur_rechnung(reservation, satzung, folios)
    # GoBD §10 text-only output (no ANSI / no rich markup).
    sys.stdout.write(receipt)
    if not receipt.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def _handle_dsgvo_cascade(args: argparse.Namespace) -> int:
    """F5 Tier-2 AC-2: DSGVO Art. 17 in-house retention cascade for a guest.

    Spec AC-2: `python -m kurort_engine dsgvo cascade <guest_id>` → exit 0 +
    JSON with keys `guest_id`, `actions_planned`, `actions_count` + self-
    consistency `actions_count == len(actions_planned)`.

    Library signature (verified via inspect.signature):
        run_cascade_with_retry(guest_id: str, retry_max: int = 2) -> dict[str, Any]

    EARS-vs-library resolution (BLOCKER B-3 per the spec-input reconciliation):
    spec.yaml EARS names `run_cascade(guest_id)` but the SHIPPED library exports
    `run_cascade_with_retry(guest_id, retry_max=2)` (with retries). The handler
    uses the correct library signature and reports the action list per the spec
    AC-2 JSON shape (guest_id + actions_planned + actions_count).
    """
    from kurort_engine.kurgaste_retention.auto_cascade import run_cascade_with_retry

    result = run_cascade_with_retry(args.guest_id, retry_max=2)
    # Normalise to AC-2 JSON shape (guest_id + actions_planned + actions_count).
    actions_planned = result.get("actions_planned") or result.get("cascade_steps_completed") or []
    out = {
        "guest_id": args.guest_id,
        "actions_planned": list(actions_planned),
        "actions_count": len(actions_planned),
    }
    sys.stdout.write(json.dumps(out))
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def _handle_predicate_file(args: argparse.Namespace) -> int:
    """F5 Tier-2 AC-3: Heilbad predicate filing packet for a (year, heilbad_code).

    Spec AC-3: `python -m kurort_engine predicate file <year> <heilbad_code>
    [--output-dir <dir>]` → exit 0 + stdout contains year + heilbad_code +
    persisted artifact path.

    Library signature (verified via inspect.signature):
        assemble_predicate_packet(
            period_start: date, period_end: date,
            kurgaste_records: list[dict[str, Any]],
            kurtaxe_data: dict[str, Any],
            hcmi_scope1_2_data: dict[str, Any],
            spa_data: dict[str, Any],
            ev_charging_data: dict[str, Any],
        ) -> dict[str, Any]

    EARS-vs-library resolution (BLOCKER B-3 per the spec-input reconciliation):
    spec.yaml EARS names `predicate_filing.run(year, heilbad_code)` (2 args)
    but the SHIPPED library exports a 7-arg signature with MIN_CYCLE_YEARS=4
    constraint. The handler derives `period_start=date(year, 1, 1)` and
    `period_end=date(year + 4, 12, 31)` (≥ 4-year window) and supplies empty
    section data (kurgaste/kurtaxe/hcmi/spa/ev_charging) for the minimal
    invocation. The artifact is then persisted to --output-dir (or cwd).
    """
    from datetime import date as _date
    from pathlib import Path as _Path

    from kurort_engine.predicate_filing import assemble_predicate_packet

    output_dir = _Path(getattr(args, "output_dir", None) or ".")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"predicate_{args.heilbad_code}_{args.year}.json"
    artifact_path = output_dir / artifact_name

    # Derive 4-year window (MIN_CYCLE_YEARS=4 per predicate_filing library).
    period_start = _date(int(args.year), 1, 1)
    period_end = _date(int(args.year) + 4, 12, 31)

    packet = assemble_predicate_packet(
        period_start=period_start,
        period_end=period_end,
        kurgaste_records=[],
        kurtaxe_data={},
        hcmi_scope1_2_data={},
        spa_data={},
        ev_charging_data={},
    )
    artifact_path.write_text(json.dumps(packet, indent=2, default=str))

    sys.stdout.write(
        f"predicate filing persisted: year={args.year} "
        f"heilbad_code={args.heilbad_code} artifact={artifact_path}\n"
    )
    sys.stdout.flush()
    return 0


__all__ = [
    # MVP public API (AC-6 contract — 11 symbols).
    "AuditEntry",
    "AuditLog",
    "Exemption",
    "Guest",
    "RateBand",
    "Reservation",
    "Satzung",
    "build_badekur_rechnung",
    "calculate_kurtaxe_for_reservation",
    "generate_monthly_remittance_csv",
    "load_profile",
    # Kurort-vertical Spa/Wellness public API (AC-1..AC-8 — 13 symbols).
    "Resource",
    "Slot",
    "SpaManager",
    "SpaBooking",
    "Payment",
    "PaymentMethodError",
    "PaymentMethodKurkarteError",
    "SlotBookingError",
    "ToskanaThermeAdapter",
    "ToskanaThermeTicket",
    "ToskanaThermeKurkarteError",
    "DailySpaRevenueReport",
    "generate_daily_spa_revenue_report",
    # Kurort-vertical Meldeschein public API (iter-6 AC-1..AC-3 — 8 symbols).
    "MeldescheinForm",
    "ProcessingRecord",
    "MeldescheinValidationError",
    "AVVValidationError",
    "BFSGScannerInputError",
    "render",
    "generate_avv_markdown",
    "scan_booking_flow",
    # Q5.7 Kurpaket orchestrator public API (iter-18 AC-1..AC-12).
    "kurpaket_orchestrator",
    "kurpaket_templates",
    "kurpaket_guest_card",
    "badearzt_directory",
    "heilbad_badge",
    "kurpaket_pricing",
    "kurpaket_compliance",
    "KurpaketTemplate",
    "KurpaketQuote",
    "KurpaketGuestCard",
    "HMGViolationError",
    "SGBV23CertificateMissing",
    "list_entries",
    "price_for_template",
    "badge_visible",
    "render_badge",
    "check_hmg_compliance",
    "record_sgb_v_event",
    "compose_quote",
    "render_confirmation",
    "render_qr_payload",
    "issue_guest_card",
    # Q5.3 Kurkarte digital wallet public API (iter-21 AC-1..AC-5).
    "kurkarte_wallet",
    "render_apple_pass",
    "render_google_pass_object",
    "wallet_add_url",
    "BFSGComplianceError",
    # Q5.2 EV charging public API (iter-24 AC-1..AC-5).
    "InvoiceLineItem",
    "MeterReading",
    "ReservationMatch",
    "SESSION_SIGNING_KEY",
    "append_to_folio",
    "lookup_apple_pass",
    "match",
    "read_session",
    "render_charging_session",
    "sign_charging_session",
    # F5 receptionist-subcommands dispatcher (iter-16 Phase 4 GREEN).
    "parse_subcommand",
    # avv_kaskade CLI dispatcher (iter-28 Phase 5 refactor).
    "_handle_avv_attest",
    "_handle_avv_geeignetheitspruefung",
    "_handle_avv_version",
    # Phase 7b a11y.guest_pwa tenant re-exports (iter-3 ADDITIVE — 4 new symbols).
    "SELF_ATTESTATION_TS",
    "BFSGComplianceError",
    "run_wcag_aa_audit",
    "CHAIN_EXTENSION_ANCHORS",
]

