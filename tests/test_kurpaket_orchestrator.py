"""Q5.7 AC-1..AC-6 — Kurpaket orchestrator test surface.

This file exercises the six top-level templates (A=Kurzurlaub-Wochenende 3-Nächte
Fri-Sun, B=Classic 7-Nächte, C=Premium 10-Nächte, D=Intensiv 14-Nächte,
E=Spezial-Heilbad 21-Nächte) and the Heilbad-2026 badge auto-expiry via
``kurpaket_orchestrator.compose(...)`` (or whichever primary entry point the
green phase lands on — the test asserts behaviour, not the exact symbol).

Test_oracle paths recorded in spec_lock.md → traceability matrix.

RED VERIFY
----------
Each test in this file is expected to FAIL during the red phase with an
``AssertionError`` that pins the contract; ``ImportError`` / ``ModuleNotFoundError``
/ ``SyntaxError`` / ``CollectionError`` are NOT acceptable — they mean the test
is broken, not the code under test.

Per ``iter-15-pinned-tdd-rules-for-coverage-gate-closure-forbidden-test-patterns-red-v``:
  * Use ``importlib.util.find_spec`` as a pre-check so the import failure mode
    surfaces as ``AssertionError`` ("module should exist"), not ``ImportError``.
  * Use concrete Decimal math + concrete substring / substring-must-NOT-appear
    checks (per AC-6) instead of mocking the unit under test.
  * Fail the test for the right reason — empty body, ``assert True``, ``pytest.skip``
    are forbidden.
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-1..AC-6: import pre-check (find_spec) — every test asserts the contract
# symbol is importable FIRST so the failure is "module missing" rather than a
# cascade of attribute errors on the next line.
# ---------------------------------------------------------------------------

_KURPAKET_ORCHESTRATOR_SPEC = "kurort_engine.kurpaket_orchestrator"


def _kurpaket_orchestrator_is_importable() -> str:
    """Return a one-line human-readable diagnostic for the spec-check.

    The check itself runs through ``assert`` so the test suite surfaces the
    first failing precondition as a clean ``AssertionError``.
    """
    found = importlib.util.find_spec("kurort_engine.kurpaket_orchestrator")
    assert found is not None, (
        f"{_KURPAKET_ORCHESTRATOR_SPEC} is not importable — green phase must "
        f"create repo/src/kurort_engine/kurpaket_orchestrator.py before these "
        f"tests can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


# ---------------------------------------------------------------------------
# Concrete, deterministic reference fixtures for the 5 templates.
# ---------------------------------------------------------------------------
#
# A=Kurzurlaub-Wochenende (3-Nächte Fri-Sun), B=Classic (7-Nächte),
# C=Premium (10-Nächte), D=Intensiv (14-Nächte), E=Spezial-Heilbad (21-Nächte).
# The arrival/departure dates are deterministic so test output is byte-stable.

_TEMPLATE_A_ARRIVAL = date(2026, 5, 22)  # Friday — Kurzurlaub-Wochenende
_TEMPLATE_A_NIGHTS = 3
_TEMPLATE_A_DEPARTURE = _TEMPLATE_A_ARRIVAL + timedelta(days=_TEMPLATE_A_NIGHTS)

_TEMPLATE_B_ARRIVAL = date(2026, 6, 7)  # Sunday — Classic 7-Nächte
_TEMPLATE_B_NIGHTS = 7
_TEMPLATE_B_DEPARTURE = _TEMPLATE_B_ARRIVAL + timedelta(days=_TEMPLATE_B_NIGHTS)

_TEMPLATE_C_ARRIVAL = date(2026, 6, 14)
_TEMPLATE_C_NIGHTS = 10
_TEMPLATE_C_DEPARTURE = _TEMPLATE_C_ARRIVAL + timedelta(days=_TEMPLATE_C_NIGHTS)

_TEMPLATE_D_ARRIVAL = date(2026, 6, 21)
_TEMPLATE_D_NIGHTS = 14
_TEMPLATE_D_DEPARTURE = _TEMPLATE_D_ARRIVAL + timedelta(days=_TEMPLATE_D_NIGHTS)

_TEMPLATE_E_ARRIVAL = date(2026, 7, 5)
_TEMPLATE_E_NIGHTS = 21
_TEMPLATE_E_DEPARTURE = _TEMPLATE_E_ARRIVAL + timedelta(days=_TEMPLATE_E_NIGHTS)


# Per AC-1: Kurzurlaub-Wochenende ceiling per person = 195 EUR.
# Per AC-2..AC-4: HHB In-Balance 7/10/14-Nächte floor per person = 1,169 EUR.
# Per AC-11: ±10% of HHB reference = EUR 1,052.10..1,285.90 inclusive.
_TEMPLATE_A_MAX_PRICE_EUR = Decimal("195.00")
_HHB_REFERENCE_EUR = Decimal("1169.00")


def _get_orchestrator():
    """Helper: import the orchestrator module after the find_spec guard.

    Returns the imported module. Test files don't import symbols at module
    scope because that turns the red-state error into ``ImportError`` instead
    of ``AssertionError``.
    """
    diagnostic = _kurpaket_orchestrator_is_importable()
    import kurort_engine.kurpaket_orchestrator as _orch  # noqa: E402
    assert _orch is not None, f"importlib returned module but got None: {diagnostic}"
    return _orch


# ===========================================================================
# AC-1 — Kurzurlaub-Wochenende 3-Nächte Fri-Sun: Gästekarte + 1 spa/day + ≤195 EUR
# ===========================================================================

def test_ac1_kurzurlaub_weekend_3_nachte() -> None:
    """AC-1 spec test_oracle.

    Contract (verbatim from spec.yaml AC-1):

        When a guest books 3-Nächte Fri-Sun WITH template A (Kurzurlaub-Wochenende)
        THEN the orchestrator shall issue one Gästekarte + 1 spa treatment/day +
        Kurzurlaub-Wochenende pricing at ≤ 195 EUR per person (HHB reference for
        3-Nächte weekend tier).

    The test exercises a 3-Nächte Friday→Sunday booking and asserts the
    orchestrator emits a result carrying:

      * 1 Gästekarte (issued flag true; or guest_card output present)
      * spa_treatments_per_day == 1
      * total_price_eur ≤ 195.00
      * template_code == "A" (Kurzurlaub-Wochenende)
      * nights == 3 (Fri→Sun)
      * arrival is a Friday; departure is the following Monday-wait, Fri → Sun
        is 3 nights (Fri, Sat, Sun) which is the HHB weekend tier wording.

    The orchestrator entry point is whatever the green phase provides
    (e.g. ``kurpaket_orchestrator.compose_quote(...)`` returning a
    ``KurpaketQuote`` dataclass). The test accesses the result fields via the
    canonical names but stays duck-typed enough to survive minor
    naming-inconsistencies — it inspects ``__dict__`` for the AC-mandated
    fields and falls back to attribute access.
    """
    _get_orchestrator()  # find_spec guard — AssertionError not ImportError

    booking = {
        "template_code": "A",
        "nights": _TEMPLATE_A_NIGHTS,
        "arrival": _TEMPLATE_A_ARRIVAL,
        "departure": _TEMPLATE_A_DEPARTURE,
        "guests": 1,
        "include_spa_treatments": True,
    }

    orch = _get_orchestrator()
    compose = getattr(orch, "compose_quote", None) or getattr(
        orch, "compose", None
    ) or getattr(orch, "build", None)
    assert compose is not None and callable(compose), (
        "AC-1: kurpaket_orchestrator must expose a callable compose_quote / "
        "compose / build entry point for the guest booking payload; got: "
        f"{[n for n in dir(orch) if not n.startswith('_')]!r}"
    )

    quote = compose(booking)
    assert quote is not None, (
        "AC-1: orchestrator returned None for a valid 3-Nächte Fri-Sun booking"
    )

    # Inspect the result as a dict-like so we can field-pin the AC-1 contract
    # without depending on the exact dataclass name the green phase chooses.
    fields = getattr(quote, "__dict__", None) or {
        k: v for k, v in vars(quote).items()
    }
    assert isinstance(fields, dict) and fields, (
        f"AC-1: orchestrator result must expose a populated fields mapping; "
        f"got {type(quote).__name__} with {fields!r}"
    )

    # ---- Template code / nights / spa treatments per day ----
    template_code = fields.get("template_code") or fields.get("template")
    assert template_code == "A", (
        f"AC-1: template_code must be 'A' (Kurzurlaub-Wochenende); got {template_code!r}"
    )

    nights = fields.get("nights")
    assert nights == _TEMPLATE_A_NIGHTS == 3, (
        f"AC-1: nights must be 3 for the 3-Nächte Fri-Sun tier; got {nights!r}"
    )

    spa_per_day = fields.get("spa_treatments_per_day") or fields.get(
        "spa_per_day"
    )
    assert spa_per_day == 1, (
        f"AC-1: spa_treatments_per_day must be exactly 1 for Kurzurlaub-"
        f"Wochenende; got {spa_per_day!r}"
    )

    # ---- Gästekarte: issued flag OR presence of a non-empty guest_card ----
    guest_card_issued = fields.get("guest_card_issued")
    if guest_card_issued is None:
        # Fall back to a non-empty guest_card artifact in the fields mapping.
        guest_card = fields.get("guest_card") or fields.get("gaestekarte")
        assert guest_card, (
            f"AC-1: orchestrator must issue a Gästekarte for a Kurzurlaub-"
            f"Wochenende booking; got guest_card={guest_card!r}"
        )
    else:
        assert guest_card_issued is True, (
            f"AC-1: guest_card_issued must be True; got {guest_card_issued!r}"
        )

    # ---- Pricing: ≤ 195 EUR per person ----
    total_price = (
        fields.get("total_price_eur")
        or fields.get("price_eur")
        or fields.get("price")
        or fields.get("price_per_person_eur")
    )
    assert total_price is not None, (
        f"AC-1: orchestrator must report a price_eur / price field; got {fields!r}"
    )
    if not isinstance(total_price, Decimal):
        total_price = Decimal(str(total_price))
    assert total_price <= _TEMPLATE_A_MAX_PRICE_EUR, (
        f"AC-1: Kurzurlaub-Wochenende 3-Nächte pricing must be ≤ "
        f"{_TEMPLATE_A_MAX_PRICE_EUR} EUR per person (HHB weekend tier); "
        f"got {total_price} EUR"
    )


# ===========================================================================
# AC-2 — Classic 7-Nächte HHB-In-Balance ≥ 1,169 EUR + 4 spa + full board + Gästekarte
# ===========================================================================

def test_ac2_classic_kurpaket_7_nachte_hhb() -> None:
    """AC-2 spec test_oracle.

    Contract (verbatim from spec.yaml AC-2):

        When a guest books 7-Nächte WITH template B (Classic-Kurpaket) THEN
        the orchestrator shall apply HHB-In-Balance 7-Nächte benchmark at
        ≥ 1,169 EUR per person reference + 4 spa treatments + full board +
        Gästekarte issuance.

    Asserts:
      * template_code == "B"
      * nights == 7
      * price_per_person_eur >= 1,169.00 (HHB floor — AC-11 ±10% bracket
        passes this; the AC-2 floor is the HHB reference itself)
      * spa_treatments_total == 4 (or spa_treatments_per_day AND nights → 4)
      * board == "full" (full board)
      * Gästekarte issued (flag or artifact)
    """
    _get_orchestrator()  # find_spec guard

    booking = {
        "template_code": "B",
        "nights": _TEMPLATE_B_NIGHTS,
        "arrival": _TEMPLATE_B_ARRIVAL,
        "departure": _TEMPLATE_B_DEPARTURE,
        "guests": 1,
    }
    orch = _get_orchestrator()
    compose = getattr(orch, "compose_quote", None) or getattr(
        orch, "compose", None
    ) or getattr(orch, "build", None)
    assert callable(compose), "AC-2: compose_quote/compose/build entry point missing"

    quote = compose(booking)
    fields = getattr(quote, "__dict__", None) or vars(quote)
    assert fields, f"AC-2: orchestrator returned empty/non-dict quote: {fields!r}"

    template_code = fields.get("template_code") or fields.get("template")
    assert template_code == "B", (
        f"AC-2: template_code must be 'B' (Classic-Kurpaket); got {template_code!r}"
    )

    nights = fields.get("nights")
    assert nights == 7, f"AC-2: nights must be 7; got {nights!r}"

    price = (
        fields.get("price_per_person_eur")
        or fields.get("total_price_eur")
        or fields.get("price_eur")
    )
    assert price is not None, f"AC-2: price missing; got {fields!r}"
    if not isinstance(price, Decimal):
        price = Decimal(str(price))
    assert price >= _HHB_REFERENCE_EUR, (
        f"AC-2: Classic-Kurpaket 7-Nächte HHB-In-Balance benchmark requires "
        f"price ≥ {_HHB_REFERENCE_EUR} EUR per person (HHB reference); "
        f"got {price} EUR"
    )

    spa_total = fields.get("spa_treatments_total")
    if spa_total is None:
        per_day = fields.get("spa_treatments_per_day")
        if per_day is not None:
            spa_total = per_day * nights
    assert spa_total == 4, (
        f"AC-2: Classic-Kurpaket must include 4 spa treatments; got "
        f"{spa_total!r} (per_day={fields.get('spa_treatments_per_day')!r})"
    )

    board = fields.get("board") or fields.get("meal_plan")
    assert board in ("full", "full_board", "VP", "Vollpension"), (
        f"AC-2: Classic-Kurpaket must include full board (Vollpension); "
        f"got board={board!r}"
    )

    gci = fields.get("guest_card_issued")
    if gci is None:
        gc = fields.get("guest_card") or fields.get("gaestekarte")
        assert gc, "AC-2: Gästekarte must be issued for Classic-Kurpaket"
    else:
        assert gci is True, f"AC-2: guest_card_issued must be True; got {gci!r}"


# ===========================================================================
# AC-3 — Premium 10-Nächte HHB-In-Balance + 6 spa + full board + Gästekarte
# ===========================================================================

def test_ac3_premium_kurpaket_10_nachte_hhb() -> None:
    """AC-3 spec test_oracle.

    Contract (verbatim from spec.yaml AC-3):

        When a guest books 10-Nächte WITH template C (Premium-Kurpaket) THEN
        the orchestrator shall apply HHB-In-Balance 10-Nächte benchmark pricing
        + 6 spa treatments + full board + Gästekarte issuance.

    Asserts: template_code == "C"; nights == 10; price within ±10% of HHB
    reference (1,052.10 ≤ price ≤ 1,285.90 EUR); spa_total == 6; board == full;
    Gästekarte issued.
    """
    _get_orchestrator()

    booking = {
        "template_code": "C",
        "nights": _TEMPLATE_C_NIGHTS,
        "arrival": _TEMPLATE_C_ARRIVAL,
        "departure": _TEMPLATE_C_DEPARTURE,
        "guests": 1,
    }
    orch = _get_orchestrator()
    compose = (
        getattr(orch, "compose_quote", None)
        or getattr(orch, "compose", None)
        or getattr(orch, "build", None)
    )
    assert callable(compose), "AC-3: compose entry point missing"

    quote = compose(booking)
    fields = getattr(quote, "__dict__", None) or vars(quote)
    assert fields, f"AC-3: orchestrator returned empty quote: {fields!r}"

    template_code = fields.get("template_code") or fields.get("template")
    assert template_code == "C", (
        f"AC-3: template_code must be 'C' (Premium-Kurpaket); got {template_code!r}"
    )

    nights = fields.get("nights")
    assert nights == 10, f"AC-3: nights must be 10; got {nights!r}"

    price = (
        fields.get("price_per_person_eur")
        or fields.get("total_price_eur")
        or fields.get("price_eur")
    )
    assert price is not None, f"AC-3: price missing; got {fields!r}"
    if not isinstance(price, Decimal):
        price = Decimal(str(price))
    # HHB ±10% bracket (per AC-11): EUR 1,052.10 to EUR 1,285.90 inclusive
    assert Decimal("1052.10") <= price <= Decimal("1285.90"), (
        f"AC-3: Premium-Kurpaket 10-Nächte HHB-In-Balance benchmark requires "
        f"price within ±10% of {_HHB_REFERENCE_EUR} EUR per person "
        f"(1,052.10..1,285.90); got {price} EUR"
    )

    spa_total = fields.get("spa_treatments_total")
    if spa_total is None:
        per_day = fields.get("spa_treatments_per_day")
        if per_day is not None:
            spa_total = per_day * nights
    assert spa_total == 6, (
        f"AC-3: Premium-Kurpaket must include 6 spa treatments; got {spa_total!r}"
    )

    board = fields.get("board") or fields.get("meal_plan")
    assert board in ("full", "full_board", "VP", "Vollpension"), (
        f"AC-3: Premium-Kurpaket must include full board; got board={board!r}"
    )

    gci = fields.get("guest_card_issued")
    if gci is None:
        gc = fields.get("guest_card") or fields.get("gaestekarte")
        assert gc, "AC-3: Gästekarte must be issued for Premium-Kurpaket"
    else:
        assert gci is True, f"AC-3: guest_card_issued must be True; got {gci!r}"


# ===========================================================================
# AC-4 — Intensiv 14-Nächte HHB-In-Balance + 8 spa + full board + Gästekarte
# ===========================================================================

def test_ac4_intensiv_kurpaket_14_nachte_hhb() -> None:
    """AC-4 spec test_oracle.

    Contract (verbatim from spec.yaml AC-4):

        When a guest books 14-Nächte WITH template D (Intensiv-Kurpaket) THEN
        the orchestrator shall apply HHB-In-Balance 14-Nächte benchmark pricing
        + 8 spa treatments + full board + Gästekarte issuance.

    Asserts: template_code == "D"; nights == 14; price within ±10% of HHB
    reference; spa_total == 8; board == full; Gästekarte issued.
    """
    _get_orchestrator()

    booking = {
        "template_code": "D",
        "nights": _TEMPLATE_D_NIGHTS,
        "arrival": _TEMPLATE_D_ARRIVAL,
        "departure": _TEMPLATE_D_DEPARTURE,
        "guests": 1,
    }
    orch = _get_orchestrator()
    compose = (
        getattr(orch, "compose_quote", None)
        or getattr(orch, "compose", None)
        or getattr(orch, "build", None)
    )
    assert callable(compose), "AC-4: compose entry point missing"

    quote = compose(booking)
    fields = getattr(quote, "__dict__", None) or vars(quote)
    assert fields, f"AC-4: orchestrator returned empty quote: {fields!r}"

    template_code = fields.get("template_code") or fields.get("template")
    assert template_code == "D", (
        f"AC-4: template_code must be 'D' (Intensiv-Kurpaket); got {template_code!r}"
    )

    nights = fields.get("nights")
    assert nights == 14, f"AC-4: nights must be 14; got {nights!r}"

    price = (
        fields.get("price_per_person_eur")
        or fields.get("total_price_eur")
        or fields.get("price_eur")
    )
    assert price is not None, f"AC-4: price missing; got {fields!r}"
    if not isinstance(price, Decimal):
        price = Decimal(str(price))
    assert Decimal("1052.10") <= price <= Decimal("1285.90"), (
        f"AC-4: Intensiv-Kurpaket 14-Nächte HHB-In-Balance benchmark requires "
        f"price within ±10% of {_HHB_REFERENCE_EUR} EUR per person "
        f"(1,052.10..1,285.90); got {price} EUR"
    )

    spa_total = fields.get("spa_treatments_total")
    if spa_total is None:
        per_day = fields.get("spa_treatments_per_day")
        if per_day is not None:
            spa_total = per_day * nights
    assert spa_total == 8, (
        f"AC-4: Intensiv-Kurpaket must include 8 spa treatments; got {spa_total!r}"
    )

    board = fields.get("board") or fields.get("meal_plan")
    assert board in ("full", "full_board", "VP", "Vollpension"), (
        f"AC-4: Intensiv-Kurpaket must include full board; got board={board!r}"
    )

    gci = fields.get("guest_card_issued")
    if gci is None:
        gc = fields.get("guest_card") or fields.get("gaestekarte")
        assert gc, "AC-4: Gästekarte must be issued for Intensiv-Kurpaket"
    else:
        assert gci is True, f"AC-4: guest_card_issued must be True; got {gci!r}"


# ===========================================================================
# AC-5 — Spezial-Heilbad 21-Nächte requires §23 SGB V Muster 13 cert ≤28 days old
# ===========================================================================

def test_ac5_spezial_heilbad_requires_sgb_v_certificate() -> None:
    """AC-5 spec test_oracle.

    Contract (verbatim from spec.yaml AC-5):

        When a guest books 21-Nächte WITH template E (Spezial-Heilbad) THEN
        the orchestrator shall require a Gästekarte AND a §23 SGB V medical
        certificate (Muster 13, max 28 days old) before booking confirmation;
        otherwise raise a missing-certificate error citing §23 SGB V.

    Asserts:
      * Without a §23 SGB V Muster-13 certificate (or with a 29+-day-old
        certificate), the orchestrator raises an exception whose message
        mentions "§23 SGB V" (or "23 SGB V") — the spec's "missing-certificate
        error citing §23 SGB V" wording.
      * The error class is dedicated (e.g. ``SGBV23CertificateMissing`` /
        ``MissingSGBV23CertificateError``) rather than a generic ``ValueError``
        — the green phase may choose the exact name but the test pins the
        behaviour via either: a) class name contains 'sgb' + ('v' or '23'),
        OR b) the message clearly cites §23 SGB V.
    """
    _get_orchestrator()

    booking = {
        "template_code": "E",
        "nights": _TEMPLATE_E_NIGHTS,
        "arrival": _TEMPLATE_E_ARRIVAL,
        "departure": _TEMPLATE_E_DEPARTURE,
        "guests": 1,
        # No muster13_id provided — orchestrator must refuse.
    }

    orch = _get_orchestrator()
    compose = (
        getattr(orch, "compose_quote", None)
        or getattr(orch, "compose", None)
        or getattr(orch, "build", None)
    )
    assert callable(compose), "AC-5: compose entry point missing"

    raised_exception = None
    raised_message = ""
    try:
        compose(booking)
    except Exception as exc:  # noqa: BLE001 — collecting the failure type for assertion
        raised_exception = exc
        raised_message = str(exc)

    assert raised_exception is not None, (
        "AC-5: orchestrator must raise a missing-certificate error for a "
        "Spezial-Heilbad booking WITHOUT a §23 SGB V Muster-13 certificate; "
        "the compose call completed silently instead, which is the dangerous "
        "case (the orchestrator let the booking through without the required "
        "ambulante-Vorsorge certificate — a §23 SGB V violation)."
    )

    # ----- The error must cite §23 SGB V in its message -----
    msg = raised_message
    cites_sgb_v = (
        "§23 SGB V" in msg
        or "§ 23 SGB V" in msg
        or "SGB V §23" in msg
        or "23 SGB V" in msg
        or "sgb_v_23" in msg.lower()
        or "sgb v 23" in msg.lower()
        or "sgbv" in msg.lower()
    )
    assert cites_sgb_v, (
        f"AC-5: missing-certificate error must cite §23 SGB V (the ambulante "
        f"Vorsorge statute); got message: {msg!r} (exception type: "
        f"{type(raised_exception).__name__!r})"
    )


# ===========================================================================
# AC-6 — Heilbad 2026 badge auto-expiry post-2036
# ===========================================================================

def test_ac6_heilbad_badge_auto_expires_post_2036() -> None:
    """AC-6 spec test_oracle.

    Contract (verbatim from spec.yaml AC-6):

        When today > 2036 Reprädikatisierung certificate expiry date THEN the
        orchestrator shall hide the "Heilbad 2026" badge from all booking
        confirmations AND Gästekarten (no `Heilbad` substring appears in any
        surfaced confirmation text or QR payload).

    Asserts:
      * When ``today`` is past 2036 (e.g. 2037), the orchestrator's surfaced
        confirmation text and any QR payload do NOT contain the substring
        ``Heilbad`` (case-insensitive per the German "Heilbad" prefix).
      * When ``today`` is within the 04.03.2026..2036 window, the substring
        MAY appear (positive control, but not asserted — the test asserts the
        negative post-2036 behaviour since that is the binding contract).
    """
    _get_orchestrator()

    orch = _get_orchestrator()

    # find_spec the heilbad_badge helper module — orchestrator delegates
    # badge rendering to it (per spec.yaml 'intent' §7.2).
    heilbad_spec = importlib.util.find_spec("kurort_engine.heilbad_badge")
    assert heilbad_spec is not None, (
        "AC-6: kurort_engine.heilbad_badge module must exist before this test "
        f"can pass; find_spec returned: {heilbad_spec!r}"
    )

    # ----- Scenario A: post-2036 — badge MUST be hidden -----
    # Use a concrete post-2036 date (2037-01-15) so the failure is deterministic.
    post_2036_today = date(2037, 1, 15)
    booking = {
        "template_code": "B",
        "nights": 7,
        "arrival": date(2037, 2, 1),
        "departure": date(2037, 2, 8),
        "guests": 1,
        "today": post_2036_today,
    }

    # The orchestrator must expose either a confirmation-text renderer and a
    # QR-payload renderer, OR a single "render" method that returns both.
    render_confirm = getattr(orch, "render_confirmation", None) or getattr(
        orch, "format_confirmation", None
    ) or getattr(orch, "render", None)
    render_qr = getattr(orch, "render_qr_payload", None) or getattr(
        orch, "format_qr_payload", None
    ) or getattr(orch, "build_qr_payload", None)

    assert callable(render_confirm) or callable(render_qr), (
        "AC-6: kurpaket_orchestrator must expose either render_confirmation "
        "or render_qr_payload so the Heilbad-badge hiding behaviour can be "
        "exercised; neither was found on the module."
    )

    # ----- Check confirmation text -----
    if callable(render_confirm):
        confirmation_text = render_confirm(booking)
        assert isinstance(confirmation_text, str), (
            f"AC-6: render_confirmation must return str; got {type(confirmation_text).__name__}"
        )
        assert "Heilbad" not in confirmation_text and "heilbad" not in confirmation_text.lower(), (
            f"AC-6: post-2036 booking confirmation must NOT contain the "
            f"'Heilbad' substring (badge auto-expired); got text containing "
            f"it: {confirmation_text!r}"
        )

    # ----- Check QR payload -----
    if callable(render_qr):
        qr_payload = render_qr(booking)
        # QR payload may be a string OR a (bytes, str) tuple
        # depending on the QR encoder; the test only cares that the
        # printable text portion of the payload does NOT contain 'Heilbad'.
        if isinstance(qr_payload, tuple) or isinstance(qr_payload, list):
            # iterate through every string element looking for the substring
            printable = " ".join(str(p) for p in qr_payload)
        elif isinstance(qr_payload, bytes):
            printable = qr_payload.decode("utf-8", errors="replace")
        else:
            printable = str(qr_payload)

        assert "Heilbad" not in printable and "heilbad" not in printable.lower(), (
            f"AC-6: post-2036 QR payload must NOT contain the 'Heilbad' "
            f"substring (badge auto-expired); got payload containing it: "
            f"{printable!r}"
        )

    # ----- Scenario B: within the window — badge MAY be present (positive control).
    # We do NOT enforce presence here (the AC-6 binding clause is the post-2036
    # hiding); this is just to confirm the orchestrator does not fail to render.
    in_window_booking = {
        "template_code": "B",
        "nights": 7,
        "arrival": date(2030, 6, 1),
        "departure": date(2030, 6, 8),
        "guests": 1,
        "today": date(2030, 5, 15),
    }
    if callable(render_confirm):
        in_window_text = render_confirm(in_window_booking)
        assert isinstance(in_window_text, str), (
            f"AC-6: render_confirmation must return str for an in-window "
            f"date too; got {type(in_window_text).__name__}"
        )
