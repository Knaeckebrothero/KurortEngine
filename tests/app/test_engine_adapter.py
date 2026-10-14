"""kurort_app.services.engine — the bridge from stored stays to kurort_engine."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from kurort_app.models import (
    MELDESCHEIN_GENERATED,
    MELDESCHEIN_SIGNED,
    Guest,
    KurtaxeAssessment,
    Reservation,
    ReservationGuest,
    Room,
)
from kurort_app.services import engine
from kurort_app.services.checkin_qr import qr_matrix, qr_svg
from tests.app.conftest import BUSINESS_DATE


def _age(years: int) -> date:
    return date(BUSINESS_DATE.year - years, 3, 1)


def make_stay(db, guests, *, nights=7, arrival=BUSINESS_DATE, package="B", code="R-TEST-0001"):
    room = db.scalar(select(Room).where(Room.number == "204"))
    if room is None:
        room = Room(
            number="204",
            category="Doppelzimmer",
            floor=2,
            max_occupancy=3,
            nightly_rate=Decimal("129.00"),
            features="Balkon",
        )
        db.add(room)
    res = Reservation(
        code=code,
        room=room,
        arrival=arrival,
        departure=arrival + timedelta(days=nights),
        rate_total=Decimal("129.00") * nights,
        package_code=package,
    )
    for pos, spec in enumerate(guests):
        g = Guest(
            first_name=spec.get("first", f"Gast{pos}"),
            last_name=spec.get("last", "Weber"),
            birth_date=spec.get("birth", _age(60)),
            nationality=spec.get("nationality", "DE"),
            street=spec.get("street", "Lindenallee 4"),
            postal_code="63571",
            city="Gelnhausen",
            country=spec.get("country", "DE"),
            id_document_number=spec.get("id_doc"),
            disability_pct=spec.get("gdb"),
        )
        res.guests.append(
            ReservationGuest(
                guest=g,
                is_primary=pos == 0,
                position=pos,
                exemption_category=spec.get("exemption"),
                exemption_evidence=spec.get("evidence"),
            )
        )
    db.add(res)
    db.commit()
    return res


# --- Kurtaxe -------------------------------------------------------------------


def test_adult_pays_the_satzung_rate_per_night(db):
    res = make_stay(db, [{"birth": _age(45)}])
    result = engine.kurtaxe_preview(res)
    assert result.ok
    (line,) = result.lines
    assert (line.band, line.rate_per_day, line.days) == ("adult", Decimal("2.50"), 7)
    assert result.total == Decimal("17.50")


@pytest.mark.parametrize(
    ("birth", "gdb", "band", "amount"),
    [
        (_age(4), None, "child", "0.00"),
        (_age(12), None, "youth", "7.00"),
        (_age(12), 80, "youth_disabled_70", "3.50"),
        (_age(70), 80, "adult_disabled_70", "8.75"),
        (
            _age(70),
            100,
            "adult_disabled_70",
            "8.75",
        ),  # GdB 100 without exemption: reduced, not free
    ],
)
def test_bands_follow_age_and_disability(db, birth, gdb, band, amount):
    res = make_stay(db, [{"birth": birth, "gdb": gdb}])
    (line,) = engine.kurtaxe_preview(res).lines
    assert line.band == band
    assert line.amount == Decimal(amount)


def test_exemption_with_evidence_zeroes_that_guest_only(db):
    res = make_stay(
        db,
        [
            {
                "first": "Doris",
                "birth": _age(55),
                "exemption": "geschaeftsreisender",
                "evidence": "Bescheinigung Firma Weber GmbH vom 01.10.2026",
            },
            {"first": "Uwe", "birth": _age(57)},
        ],
    )
    result = engine.kurtaxe_preview(res)
    assert result.ok
    doris, uwe = result.lines
    assert doris.exempt and doris.amount == Decimal("0.00")
    assert not uwe.exempt and uwe.amount == Decimal("17.50")
    assert result.total == Decimal("17.50")
    assert result.exempt_count == 1


def test_exemption_without_evidence_is_a_blocker_and_still_charged(db):
    res = make_stay(db, [{"birth": _age(55), "exemption": "geschaeftsreisender", "evidence": "  "}])
    result = engine.kurtaxe_preview(res)
    assert not result.ok
    assert "Befreiungsnachweis fehlt" in result.blockers[0].message
    assert result.lines[0].amount == Decimal("17.50")  # the consequence staff see
    with pytest.raises(engine.KurtaxeBlockedError):
        engine.assess_kurtaxe(db, res)


def test_gdb100_exemption_requires_a_recorded_gdb_of_100(db):
    res = make_stay(
        db,
        [
            {
                "birth": _age(66),
                "gdb": 80,
                "exemption": "schwerbehindert_100",
                "evidence": "Ausweis 123456",
            }
        ],
    )
    result = engine.kurtaxe_preview(res)
    assert not result.ok
    assert "GdB" in result.blockers[0].message


def test_missing_birth_date_blocks_assessment(db):
    res = make_stay(db, [{"birth": None}])
    result = engine.kurtaxe_preview(res)
    assert result.total is None
    assert "Geburtsdatum fehlt" in result.blockers[0].message
    with pytest.raises(engine.MissingBirthDateError):
        engine.assess_kurtaxe(db, res)


def test_overrides_preview_unsaved_exemptions(db):
    res = make_stay(db, [{"birth": _age(50)}])
    rg = res.guests[0]
    result = engine.kurtaxe_preview(res, {rg.id: ("schwerbehindert_100", "Ausweis 1")})
    assert not result.ok  # GdB not recorded
    result = engine.kurtaxe_preview(res, {rg.id: ("geschaeftsreisender", "Bescheinigung")})
    assert result.ok and result.total == Decimal("0.00")
    assert rg.exemption_category is None  # nothing persisted


def test_breakdown_sums_to_engine_total_and_assessment_upserts(db):
    res = make_stay(
        db,
        [
            {
                "first": "Anja",
                "birth": _age(71),
                "gdb": 100,
                "exemption": "schwerbehindert_100",
                "evidence": "Schwerbehindertenausweis Nr. 482913",
            },
            {"first": "Dieter", "birth": _age(73)},
            {"first": "Mia", "birth": _age(9)},
        ],
        nights=10,
    )
    first = engine.assess_kurtaxe(db, res)
    db.commit()
    assert first.amount == Decimal("35.00")  # 25.00 adult + 10.00 youth + 0 exempt
    assert sum(Decimal(line["amount"]) for line in first.breakdown) == first.amount
    assert [line["exempt"] for line in first.breakdown] == [True, False, False]
    assert first.satzung_label.startswith("Kurbeitragssatzung Bad Orb")

    res.guests[2].guest.birth_date = _age(4)  # child band now
    second = engine.assess_kurtaxe(db, res)
    db.commit()
    assert second.id == first.id
    assert second.amount == Decimal("25.00")
    assert db.scalar(
        select(KurtaxeAssessment).where(KurtaxeAssessment.reservation_id == res.id)
    ).amount == Decimal("25.00")


# --- Meldeschein ---------------------------------------------------------------


def test_meldeschein_renders_a_real_pdf(db):
    res = make_stay(
        db,
        [
            {
                "first": "Łucja",
                "last": "Wiśniewska",
                "nationality": "PL",
                "country": "PL",
                "id_doc": "AB1234567",
            }
        ],
    )
    rg = res.guests[0]
    pdf = engine.generate_meldeschein(db, rg)
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    assert len(pdf) > 1500
    assert rg.meldeschein_status == MELDESCHEIN_GENERATED
    assert rg.meldeschein_form_id.startswith("msch-")


def test_foreign_guest_needs_an_id_document(db):
    res = make_stay(db, [{"nationality": "NL", "country": "NL"}])
    with pytest.raises(engine.MeldescheinIncompleteError) as exc:
        engine.generate_meldeschein(db, res.guests[0])
    assert "id_document_number" in exc.value.errors


def test_sign_requires_a_generated_form(db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    with pytest.raises(engine.CheckinError):
        engine.sign_meldeschein(db, rg)
    engine.generate_meldeschein(db, rg)
    engine.sign_meldeschein(db, rg)
    assert rg.meldeschein_status == MELDESCHEIN_SIGNED and rg.meldeschein_signed_at


def test_pdf_is_rerendered_when_only_the_form_id_survived(db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    rg.meldeschein_form_id, rg.meldeschein_status = "MS-SEED-1", MELDESCHEIN_SIGNED
    assert engine.meldeschein_pdf(db, rg).startswith(b"%PDF-")


# --- Kurkarte, readiness, QR ----------------------------------------------------


def test_kurkarte_carries_the_engine_qr_payload(db):
    res = make_stay(db, [{"first": "Claudia", "last": "Wolf"}], package="B")
    view = engine.issue_kurkarte(db, res.guests[0], BUSINESS_DATE)
    assert view.code == "KK-R-TEST-0001-1"
    assert view.qr_payload.startswith("GAESTEKARTE|KK-R-TEST-0001-1|Claudia Wolf|template=B")
    assert view.template_name == "Classic-Kurpaket"
    assert view.heilbad_badge == "Heilbad 2026"
    assert view.wallet["lang"] == "de"


def test_readiness_walks_through_the_steps(db):
    res = make_stay(db, [{}])
    assert engine.first_open_step(res) == "meldeschein"
    rg = res.guests[0]
    engine.generate_meldeschein(db, rg)
    assert engine.first_open_step(res) == "meldeschein"  # still needs the signature
    engine.sign_meldeschein(db, rg)
    assert engine.first_open_step(res) == "kurtaxe"
    engine.assess_kurtaxe(db, res)
    assert engine.first_open_step(res) == "kurkarte"
    engine.issue_kurkarte(db, rg)
    assert engine.first_open_step(res) == "abschluss"
    assert not any(engine.readiness(res).values())


def test_qr_svg_is_a_full_symbol():
    matrix = qr_matrix(b"KK-R-2610-1")  # 11 bytes fit version 1-M (max 14)
    assert len(matrix) == 21  # version 1
    finder_row = [True] * 7
    assert (
        matrix[0][:7] == finder_row
        and matrix[0][-7:] == finder_row
        and matrix[-1][:7] == finder_row
    )
    svg = qr_svg("GAESTEKARTE|KK-R-2610-0001-1|Marianne von der Lindenberg-Steinberg|template=E")
    assert svg.startswith("<svg") and 'aria-label="QR-Code"' in svg
