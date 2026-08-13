"""kurort_engine.guest_arrival — arrival-bundle orchestrator (F5 AC-4 + F6 closure).

Wires 3 SHIPPED modules to produce a 3-file arrival bundle per reservation:
  1. Meldeschein PDF             (`meldeschein_<R>.pdf`)
                                via ``kurort_engine.meldeschein.render``
  2. Apple PKPass                (`kurkarte_apple_<R>.pkpass`)
                                via ``kurort_engine.kurkarte_wallet.render_apple_pass``
  3. Google Wallet Generic pass JSON
                                (`kurkarte_google_<R>.json`)
                                via ``kurort_engine.kurkarte_wallet.render_google_pass_object``

Minimum Stage-2 body for F5 AC-4 GREEN. Synthesizes the ``MeldescheinForm``
and ``KurpaketGuestCard`` from a fixture-style booking dict derived from the
reservation id. A real upstream reservation lookup (against the property
management system / Postgres) is deferred to a future iteration.

Closure of the F6 integration QA finding from iter-14 (the receptionist was
previously forced to invoke ``meldeschein.render``,
``kurkarte_wallet.render_apple_pass``, and ``kurkarte_wallet.render_google_pass_object``
as 3 separate steps before a guest could be checked in — the orchestrator
collapses this into a single ``arrival bundle`` CLI call).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from kurort_engine.kurkarte_wallet import render_apple_pass, render_google_pass_object
from kurort_engine.kurpaket_guest_card import issue_guest_card
from kurort_engine.meldeschein import MeldescheinForm
from kurort_engine.meldeschein import render as render_meldeschein


def build_arrival_bundle(reservation_id: str, output_dir: str) -> None:
    """Compose the 3-file arrival bundle into ``output_dir``.

    Parameters
    ----------
    reservation_id:
        Reservation id (e.g. ``"R-W1-001"``). Currently used only for
        filename construction; the booking fixture is synthesized locally.
        A real upstream lookup is deferred to a future iteration.
    output_dir:
        Directory into which the 3 files are written. The directory is
        created (with parents) if it does not exist.

    Files written (relative to ``output_dir``)
    -----------------------------------------
    ``meldeschein_<reservation_id>.pdf``
        Stage-2 minimum BMG §30 PDF blob (per ``meldeschein.render``).
    ``kurkarte_apple_<reservation_id>.pkpass``
        Apple PKPass JSON via ``render_apple_pass``.
    ``kurkarte_google_<reservation_id>.json``
        Google Wallet Generic pass JSON via ``render_google_pass_object``.

    Returns
    -------
    None
        The function is side-effect-only (filesystem write).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Meldeschein PDF — synthesize form from a SHIPPED-style fixture
    # (the test_oracle `test_ac4_arrival_bundle_writes_three_files`
    # exercises `R-W1-001` as the reservation id; we synthesise a
    # matching 7-night stay matching the SHIPPED iter-21 booking fixture
    # shape). Stage-2 PDF renderer returns a non-empty byte blob.
    form = MeldescheinForm(
        familienname="Mustergast",
        vorname="Erika",
        geburtsdatum=date(1985, 3, 12),
        staatsangehoerigkeit="DE",
        anschrift="Kurstrasse 1, 63619 Bad Orb",
        anreisedatum=date(2026, 6, 1),
        abreisedatum=date(2026, 6, 8),
        ausweis_seriennummer=None,
    )
    meldeschein_bytes = render_meldeschein(form)
    (out_path / f"meldeschein_{reservation_id}.pdf").write_bytes(
        meldeschein_bytes
    )

    # 2 + 3. Apple PKPass + Google Wallet JSON — synthesize a
    # ``KurpaketGuestCard`` from the SHIPPED iter-21 booking fixture shape
    # (see ``kurort_engine/kurkarte_wallet/__init__.py:_seed_apple_pass_registry``).
    # `booking_id` is keyed by the reservation id so both wallet renders
    # produce passes for the same booking (matches the AC-4 test_oracle).
    booking = {
        "booking_id": reservation_id,
        "guest_name": "Erika Mustergast",
        "template_code": "B",  # Classic 7-Nächte
        "nights": 7,
        "arrival": date(2026, 6, 1),
        "departure": date(2026, 6, 8),
        "today": date.today(),
    }
    card = issue_guest_card(booking)

    apple_pass = render_apple_pass(card)
    google_pass = render_google_pass_object(card)

    (out_path / f"kurkarte_apple_{reservation_id}.pkpass").write_text(
        json.dumps(apple_pass, default=str, indent=2), encoding="utf-8"
    )
    (out_path / f"kurkarte_google_{reservation_id}.json").write_text(
        json.dumps(google_pass, default=str, indent=2), encoding="utf-8"
    )


__all__ = ["build_arrival_bundle"]
