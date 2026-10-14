"""Adapter between the persisted front desk and the ``kurort_engine`` library.

Every regulatory number and check comes from the engine: the tourist tax
(``calculator.calculate_kurtaxe_for_reservation`` under the Bad Orb
Satzung), the Meldeschein Pflichtangaben (``meldeschein.MeldescheinForm``),
exemption recognition (``exemptions.is_exempt``) and the Kurkarte
(``kurpaket_guest_card.issue_guest_card`` + ``kurkarte_wallet``).

The functions work on ORM objects: they ``flush`` but never commit, so
the router decides the transaction boundary.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app import audit
from kurort_app.config import get_settings
from kurort_app.config import today as business_today
from kurort_app.models import (
    CHECKED_IN,
    CHECKED_OUT,
    MELDESCHEIN_GENERATED,
    MELDESCHEIN_OPEN,
    MELDESCHEIN_SIGNED,
    KurtaxeAssessment,
    Reservation,
    ReservationGuest,
)
from kurort_app.services.checkin_pdf import render_meldeschein_pdf
from kurort_engine import calculator
from kurort_engine.calculator import Guest as EngineGuest
from kurort_engine.calculator import Reservation as EngineReservation
from kurort_engine.calculator import calculate_kurtaxe_for_reservation
from kurort_engine.exemptions import Exemption, is_exempt
from kurort_engine.kurkarte_wallet import render_apple_pass
from kurort_engine.kurpaket_guest_card import issue_guest_card
from kurort_engine.kurpaket_templates import TEMPLATES as PACKAGE_TEMPLATES
from kurort_engine.meldeschein import MeldescheinForm, MeldescheinValidationError
from kurort_engine.meldeschein import _form_id as engine_form_id
from kurort_engine.rates import Satzung, load_profile

# The engine resets and appends to a module-level audit list inside every
# Kurtaxe call; serialise calls so concurrent requests cannot interleave.
_ENGINE_LOCK = threading.Lock()

STEPS: tuple[tuple[str, str], ...] = (
    ("gaeste", "Gäste & Daten"),
    ("meldeschein", "Meldeschein"),
    ("kurtaxe", "Kurtaxe"),
    ("kurkarte", "Kurkarte"),
    ("abschluss", "Abschluss"),
)
STEP_KEYS = tuple(key for key, _ in STEPS)

BAND_LABELS = {
    "adult": "Erwachsene ab 16",
    "adult_disabled_70": "Erwachsene, GdB ab 70",
    "youth": "Jugendliche 6–15",
    "youth_disabled_70": "Jugendliche 6–15, GdB ab 70",
    "child": "Kinder bis 5",
}
EXEMPTION_LABELS = {
    "geschaeftsreisender": "Geschäftsreise",
    "schwerbehindert_100": "Schwerbehindert (GdB 100)",
}
EXEMPTION_SHORT = {"geschaeftsreisender": "Geschäftsreise", "schwerbehindert_100": "GdB 100"}
EVIDENCE_HINTS = {
    "geschaeftsreisender": "Arbeitgeberbescheinigung auf Briefkopf, z. B. „Bescheinigung Firma … vom …“",
    "schwerbehindert_100": "Nummer des Schwerbehindertenausweises (GdB 100)",
}
# Field name in MeldescheinForm → (Guest attribute, German label).
MELDESCHEIN_FIELDS = {
    "familienname": ("last_name", "Familienname"),
    "vorname": ("first_name", "Vorname"),
    "geburtsdatum": ("birth_date", "Geburtsdatum"),
    "staatsangehoerigkeit": ("nationality", "Staatsangehörigkeit"),
    "anschrift": ("street", "Anschrift"),
    "anreisedatum": (None, "Anreisedatum"),
    "abreisedatum": (None, "Abreisedatum"),
}


# ---------------------------------------------------------------------------
# Errors and blockers
# ---------------------------------------------------------------------------


class CheckinError(Exception):
    """A domain rule stopped an action; ``message`` is staff-facing German."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MissingBirthDateError(CheckinError):
    def __init__(self, names: list[str]) -> None:
        super().__init__(f"Geburtsdatum fehlt: {', '.join(names)}. In Schritt 1 ergänzen.")
        self.names = names


class KurtaxeBlockedError(CheckinError):
    def __init__(self, blockers: list[Blocker]) -> None:
        super().__init__(" ".join(b.message for b in blockers))
        self.blockers = blockers


class MeldescheinIncompleteError(CheckinError):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Meldeschein unvollständig: " + "; ".join(errors.values()))
        self.errors = errors


@dataclass(frozen=True)
class Blocker:
    step: str
    message: str
    reservation_guest_id: int | None = None
    field: str | None = None


# ---------------------------------------------------------------------------
# Satzung
# ---------------------------------------------------------------------------


@lru_cache
def satzung() -> Satzung:
    settings = get_settings()
    return load_profile(settings.kurtaxe_bundesland, settings.kurtaxe_kurort)


def satzung_label() -> str:
    s = satzung()
    effective = date.fromisoformat(str(s.satzung_date))
    city = get_settings().hotel_city
    return f"Kurbeitragssatzung {city} vom {effective:%d.%m.%Y}"


# ---------------------------------------------------------------------------
# Guest data (step 1) and Meldeschein (step 2)
# ---------------------------------------------------------------------------


def guest_data_errors(rg: ReservationGuest) -> dict[str, str]:
    """Missing Meldeschein data for one guest, keyed by Guest attribute."""
    g = rg.guest
    errors: dict[str, str] = {}
    if not (g.first_name or "").strip():
        errors["first_name"] = "Vorname fehlt."
    if not (g.last_name or "").strip():
        errors["last_name"] = "Familienname fehlt."
    if g.birth_date is None:
        errors["birth_date"] = "Geburtsdatum fehlt."
    elif g.birth_date > business_today():
        errors["birth_date"] = "Geburtsdatum liegt in der Zukunft."
    if not (g.nationality or "").strip():
        errors["nationality"] = "Staatsangehörigkeit fehlt."
    if not (g.street or "").strip():
        errors["street"] = "Straße und Hausnummer fehlen."
    if not (g.postal_code or "").strip():
        errors["postal_code"] = "Postleitzahl fehlt."
    if not (g.city or "").strip():
        errors["city"] = "Ort fehlt."
    if (g.nationality or "DE").upper() != "DE" and not (g.id_document_number or "").strip():
        errors["id_document_number"] = (
            "Ausweisnummer fehlt – für ausländische Gäste Pflicht (§ 30 Abs. 2 BMG)."
        )
    return errors


def _full_address(rg: ReservationGuest) -> str:
    g = rg.guest
    address = g.address_line
    if (g.country or "DE").upper() != "DE":
        address = f"{address}, {g.country.upper()}"
    return address


def meldeschein_form(rg: ReservationGuest) -> MeldescheinForm:
    """Build the engine's BMG §30 form; the engine validates the Pflichtangaben."""
    errors = guest_data_errors(rg)
    if errors:
        raise MeldescheinIncompleteError(errors)
    g, res = rg.guest, rg.reservation
    try:
        return MeldescheinForm(
            familienname=g.last_name.strip(),
            vorname=g.first_name.strip(),
            geburtsdatum=g.birth_date,
            staatsangehoerigkeit=g.nationality.upper(),
            anschrift=_full_address(rg),
            anreisedatum=res.arrival,
            abreisedatum=res.departure,
            ausweis_seriennummer=(g.id_document_number or None),
        )
    except MeldescheinValidationError as exc:
        missing = exc.message.rsplit(":", 1)[-1].strip()
        attr, label = MELDESCHEIN_FIELDS.get(missing, (missing, missing))
        raise MeldescheinIncompleteError({attr or missing: f"{label} fehlt."}) from exc


def _now() -> datetime:
    return datetime.now(UTC)


def _render(rg: ReservationGuest, form: MeldescheinForm, form_id: str) -> bytes:
    res = rg.reservation
    settings = get_settings()
    return render_meldeschein_pdf(
        form,
        form_id=form_id,
        hotel_name=settings.hotel_name,
        hotel_city=settings.hotel_city,
        reservation_code=res.code,
        room=(f"{res.room.number} · {res.room.category}" if res.room else "–"),
        co_travellers=[
            other.guest.full_name for other in res.guests if other.id != rg.id and other.guest
        ],
        generated_at=_now(),
    )


def generate_meldeschein(session: Session, rg: ReservationGuest) -> bytes:
    """Validate via the engine, render the PDF, store it as 'erzeugt'."""
    form = meldeschein_form(rg)
    form_id = rg.meldeschein_form_id or engine_form_id()
    pdf = _render(rg, form, form_id)
    rg.meldeschein_form_id = form_id
    rg.meldeschein_pdf = pdf
    rg.meldeschein_status = MELDESCHEIN_GENERATED
    rg.meldeschein_generated_at = _now()
    rg.meldeschein_signed_at = None
    audit.record(
        session,
        action="meldeschein.generated",
        entity="reservation_guest",
        entity_id=rg.id,
        summary=f"Meldeschein erzeugt für {rg.guest.full_name} ({rg.reservation.code})",
        payload={"form_id": form_id, "reservation": rg.reservation.code},
    )
    session.flush()
    return pdf


def meldeschein_pdf(session: Session, rg: ReservationGuest) -> bytes | None:
    """Stored PDF, or re-rendered from the current data when only the form id survived."""
    if rg.meldeschein_pdf:
        return rg.meldeschein_pdf
    if not rg.meldeschein_form_id:
        return None
    pdf = _render(rg, meldeschein_form(rg), rg.meldeschein_form_id)
    rg.meldeschein_pdf = pdf
    session.flush()
    return pdf


def sign_meldeschein(session: Session, rg: ReservationGuest) -> None:
    if rg.meldeschein_status != MELDESCHEIN_GENERATED:
        raise CheckinError(
            "Unterschrift kann erst bestätigt werden, wenn der Meldeschein als PDF erzeugt ist."
        )
    rg.meldeschein_status = MELDESCHEIN_SIGNED
    rg.meldeschein_signed_at = _now()
    audit.record(
        session,
        action="meldeschein.signed",
        entity="reservation_guest",
        entity_id=rg.id,
        summary=f"Unterschrift Meldeschein bestätigt: {rg.guest.full_name}",
        payload={"form_id": rg.meldeschein_form_id, "reservation": rg.reservation.code},
    )
    session.flush()


def invalidate_meldeschein(rg: ReservationGuest) -> bool:
    """Guest data changed after the PDF existed → the form no longer matches."""
    if rg.meldeschein_status == MELDESCHEIN_OPEN and not rg.meldeschein_pdf:
        return False
    rg.meldeschein_status = MELDESCHEIN_OPEN
    rg.meldeschein_pdf = None
    rg.meldeschein_generated_at = None
    rg.meldeschein_signed_at = None
    return True


# ---------------------------------------------------------------------------
# Kurtaxe (step 3)
# ---------------------------------------------------------------------------


@dataclass
class KurtaxeLine:
    reservation_guest_id: int
    guest_id: int
    name: str
    age: int | None
    band: str | None
    band_label: str
    rate_per_day: Decimal | None
    days: int
    amount: Decimal | None
    exempt: bool
    exemption: str | None
    exemption_label: str | None
    evidence: str | None
    blocker: str | None = None

    def as_json(self) -> dict:
        return {
            "guest_id": self.guest_id,
            "reservation_guest_id": self.reservation_guest_id,
            "name": self.name,
            "age": self.age,
            "band": self.band,
            "band_label": self.band_label,
            "rate_per_day": str(self.rate_per_day) if self.rate_per_day is not None else None,
            "days": self.days,
            "amount": str(self.amount) if self.amount is not None else None,
            "exempt": self.exempt,
            "exemption": self.exemption,
            "exemption_label": self.exemption_label,
            "evidence": self.evidence,
        }


@dataclass
class KurtaxeResult:
    lines: list[KurtaxeLine]
    total: Decimal | None
    nights: int
    blockers: list[Blocker] = field(default_factory=list)
    satzung_label: str = ""

    @property
    def ok(self) -> bool:
        return not self.blockers

    @property
    def payable_days(self) -> int:
        return sum(line.days for line in self.lines if not line.exempt and line.amount)

    @property
    def exempt_count(self) -> int:
        return sum(1 for line in self.lines if line.exempt)


def _engine_guest(rg: ReservationGuest) -> EngineGuest:
    g = rg.guest
    return EngineGuest(
        name=g.full_name,
        birth_date=g.birth_date,
        nationality=(g.nationality or "DE").upper(),
        disability_pct=g.disability_pct,
    )


def kurtaxe_preview(
    reservation: Reservation,
    overrides: dict[int, tuple[str | None, str | None]] | None = None,
) -> KurtaxeResult:
    """Compute the tourist tax without touching the database.

    ``overrides`` maps reservation_guest id → (exemption category, evidence)
    for an unsaved form. A category counts only with evidence; otherwise
    the guest pays and the step is blocked until staff resolve it.
    """
    overrides = overrides or {}
    nights = reservation.nights
    lines: list[KurtaxeLine] = []
    blockers: list[Blocker] = []
    pairs: list[tuple[KurtaxeLine, EngineGuest]] = []  # guests the engine can tariff
    exemptions: dict[EngineGuest, Exemption] = {}
    sz = satzung()

    for rg in reservation.guests:
        category, evidence = overrides.get(rg.id, (rg.exemption_category, rg.exemption_evidence))
        category = category or None
        evidence = (evidence or "").strip() or None
        g = rg.guest
        line = KurtaxeLine(
            reservation_guest_id=rg.id,
            guest_id=g.id,
            name=g.full_name,
            age=None,
            band=None,
            band_label="–",
            rate_per_day=None,
            days=nights,
            amount=None,
            exempt=False,
            exemption=category,
            exemption_label=EXEMPTION_LABELS.get(category) if category else None,
            evidence=evidence,
        )
        lines.append(line)
        if g.birth_date is None:
            line.blocker = "Geburtsdatum fehlt – in Schritt 1 ergänzen."
            blockers.append(
                Blocker("kurtaxe", f"{g.full_name}: {line.blocker}", rg.id, "birth_date")
            )
            continue
        eg = _engine_guest(rg)
        line.age = calculator._age_at(eg, reservation.arrival)
        try:
            band = calculator._find_band_for_guest(eg, sz, reservation.arrival)
        except ValueError:
            line.blocker = "Keine Tarifgruppe der Satzung passt (Alter/GdB prüfen)."
            blockers.append(Blocker("kurtaxe", f"{g.full_name}: {line.blocker}", rg.id))
            continue
        line.band, line.band_label, line.rate_per_day = (
            band.name,
            BAND_LABELS.get(band.name, band.name),
            band.rate_per_day,
        )
        pairs.append((line, eg))
        if category:
            if not evidence:
                line.blocker = (
                    "Befreiungsnachweis fehlt. Nachweis eintragen oder Befreiung entfernen."
                )
                blockers.append(
                    Blocker(
                        "kurtaxe", f"{g.full_name}: {line.blocker}", rg.id, "exemption_evidence"
                    )
                )
            elif category == "schwerbehindert_100" and (g.disability_pct or 0) < 100:
                line.blocker = (
                    f"Befreiung GdB 100 passt nicht zum erfassten GdB "
                    f"({g.disability_pct or 'keiner'}). GdB in Schritt 1 korrigieren "
                    f"oder Befreiung entfernen."
                )
                blockers.append(Blocker("kurtaxe", f"{g.full_name}: {line.blocker}", rg.id))
            else:
                exemption = Exemption(
                    guest_name=eg.name,
                    reservation_id=reservation.code,
                    category=category,
                    evidence=evidence,
                    valid_on=reservation.arrival,
                )
                if is_exempt(exemption):
                    exemptions[eg] = exemption

    total: Decimal | None = None
    engine_guests = [eg for _, eg in pairs]
    with _ENGINE_LOCK:
        for line, eg in pairs:
            single = EngineReservation(
                reservation_id=reservation.code,
                arrival=reservation.arrival,
                departure=reservation.departure,
                guests=(eg,),
            )
            ex = {eg: exemptions[eg]} if eg in exemptions else None
            line.amount = calculate_kurtaxe_for_reservation(single, sz, ex)
            line.exempt = eg in exemptions
        if engine_guests:
            total = calculate_kurtaxe_for_reservation(
                EngineReservation(
                    reservation_id=reservation.code,
                    arrival=reservation.arrival,
                    departure=reservation.departure,
                    guests=tuple(engine_guests),
                ),
                sz,
                exemptions,
            )
    per_guest = sum((line.amount for line, _ in pairs), Decimal("0.00"))
    if total is not None and per_guest != total:
        raise AssertionError(f"Kurtaxe breakdown {per_guest} != engine total {total}")
    if len(pairs) != len(lines):
        total = None  # someone could not be tariffed: no total to quote
    return KurtaxeResult(
        lines=lines, total=total, nights=nights, blockers=blockers, satzung_label=satzung_label()
    )


def assess_kurtaxe(session: Session, reservation: Reservation) -> KurtaxeAssessment:
    """Compute via the engine and upsert the reservation's assessment row."""
    missing = [rg.guest.full_name for rg in reservation.guests if rg.guest.birth_date is None]
    if missing:
        raise MissingBirthDateError(missing)
    result = kurtaxe_preview(reservation)
    if result.blockers or result.total is None:
        raise KurtaxeBlockedError(result.blockers)
    assessment = reservation.kurtaxe or KurtaxeAssessment(reservation=reservation)
    assessment.amount = result.total
    assessment.nights = result.nights
    assessment.breakdown = [line.as_json() for line in result.lines]
    assessment.satzung_label = result.satzung_label
    assessment.computed_at = _now()
    reservation.kurtaxe = assessment
    session.add(assessment)
    session.flush()
    return assessment


def assess_seeded_stays(session: Session, reservations: list[Reservation]) -> int:
    """Seed helper: assess every stay that is or was in house; skip blocked ones."""
    count = 0
    for reservation in reservations:
        if reservation.status not in (CHECKED_IN, CHECKED_OUT):
            continue
        try:
            assess_kurtaxe(session, reservation)
        except CheckinError:
            continue
        count += 1
    return count


def drop_assessment(session: Session, reservation: Reservation) -> None:
    """Inputs changed → the stored assessment is stale."""
    if reservation.kurtaxe is not None:
        session.delete(reservation.kurtaxe)
        reservation.kurtaxe = None
        session.flush()


# ---------------------------------------------------------------------------
# Kurkarte (step 4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KurkarteView:
    code: str
    guest_name: str
    template_code: str
    template_name: str
    valid_from: date
    valid_until: date
    qr_payload: str
    heilbad_badge: str
    wallet: dict


def _booking(rg: ReservationGuest, code: str, today: date) -> dict:
    res = rg.reservation
    return {
        "booking_id": code,
        "guest_name": rg.guest.full_name,
        "template_code": res.package_code or "",
        "arrival": res.arrival,
        "departure": res.departure,
        "nights": res.nights,
        "today": today,
    }


def kurkarte_code(rg: ReservationGuest) -> str:
    return f"KK-{rg.reservation.code}-{rg.position + 1}"


def kurkarte_view(rg: ReservationGuest, today: date | None = None) -> KurkarteView | None:
    if not rg.kurkarte_code:
        return None
    card = issue_guest_card(_booking(rg, rg.kurkarte_code, today or rg.reservation.arrival))
    template = PACKAGE_TEMPLATES.get(card.template_code) if card.template_code else None
    return KurkarteView(
        code=rg.kurkarte_code,
        guest_name=card.guest_name,
        template_code=card.template_code,
        template_name=template.name if template else "Kurkarte",
        valid_from=card.valid_from,
        valid_until=card.valid_until,
        qr_payload=rg.kurkarte_qr_payload or card.qr_payload,
        heilbad_badge=card.heilbad_badge,
        wallet=render_apple_pass(card),
    )


def issue_kurkarte(
    session: Session, rg: ReservationGuest, today: date | None = None
) -> KurkarteView:
    code = rg.kurkarte_code or kurkarte_code(rg)
    card = issue_guest_card(_booking(rg, code, today or rg.reservation.arrival))
    render_apple_pass(card)  # the engine's BFSG/WCAG checks on the wallet pass
    rg.kurkarte_code = code
    rg.kurkarte_qr_payload = card.qr_payload
    rg.kurkarte_issued_at = _now()
    audit.record(
        session,
        action="kurkarte.issued",
        entity="reservation_guest",
        entity_id=rg.id,
        summary=f"Kurkarte {code} ausgestellt für {rg.guest.full_name}",
        payload={"code": code, "valid_until": card.valid_until.isoformat()},
    )
    session.flush()
    view = kurkarte_view(rg, today)
    assert view is not None
    return view


# ---------------------------------------------------------------------------
# Readiness across the five steps
# ---------------------------------------------------------------------------


def readiness(reservation: Reservation) -> dict[str, list[Blocker]]:
    """Open items per check-in step. Empty lists everywhere = ready to complete."""
    steps: dict[str, list[Blocker]] = {key: [] for key in STEP_KEYS}
    if not reservation.guests:
        steps["gaeste"].append(Blocker("gaeste", "Keine Gäste auf der Reservierung."))
    for rg in reservation.guests:
        name = rg.guest.full_name.strip() or "Gast"
        for attr, message in guest_data_errors(rg).items():
            steps["gaeste"].append(Blocker("gaeste", f"{name}: {message}", rg.id, attr))
        if rg.meldeschein_status == MELDESCHEIN_OPEN:
            steps["meldeschein"].append(
                Blocker("meldeschein", f"{name}: Meldeschein noch nicht erzeugt.", rg.id)
            )
        elif rg.meldeschein_status == MELDESCHEIN_GENERATED:
            steps["meldeschein"].append(
                Blocker("meldeschein", f"{name}: PDF erzeugt · Unterschrift fehlt.", rg.id)
            )
        if not rg.kurkarte_code:
            steps["kurkarte"].append(
                Blocker("kurkarte", f"{name}: Kurkarte noch nicht ausgestellt.", rg.id)
            )
    if reservation.room is None:
        steps["abschluss"].append(Blocker("abschluss", "Kein Zimmer zugewiesen."))
    if not steps["gaeste"]:
        preview = kurtaxe_preview(reservation)
        steps["kurtaxe"].extend(preview.blockers)
        if not preview.blockers and reservation.kurtaxe is None:
            steps["kurtaxe"].append(
                Blocker("kurtaxe", "Kurtaxe noch nicht berechnet und bestätigt.")
            )
    else:
        steps["kurtaxe"].append(Blocker("kurtaxe", "Erst die Gästedaten vervollständigen."))
    return steps


def first_open_step(reservation: Reservation) -> str:
    state = readiness(reservation)
    for key in STEP_KEYS[:-1]:
        if state[key]:
            return key
    return "abschluss"


def load_reservation(session: Session, reservation_id: int) -> Reservation | None:
    return session.scalar(select(Reservation).where(Reservation.id == reservation_id))
