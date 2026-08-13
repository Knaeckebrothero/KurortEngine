"""AC-5: Badekur Rechnung layout (Krankenkasse §23 SGB V submission).

Test_oracle path recorded in spec.yaml:105. This is the red-phase test
that will fail with an ``AssertionError`` against the placeholder
implementation (``build_badekur_rechnung`` currently returns ``""`` with
the wrong signature ``(reservation, satzung, exemptions=None,
out_path=None)``).

AC-5 contract (spec.yaml:98-105):
    When ``build_badekur_rechnung(reservation, satzung, folios)`` is
    invoked, the ``kurort_engine`` shall produce a Rechnung whose layout
    separates "Zuschussfähige Posten" into the three sub-totals Kurtaxe,
    Übernachtung, and Verpflegung, and whose footer includes the
    reference text "Badekur/Ambulante Vorsorge §23 SGB V".

The two AC-5 clauses, pinned:
    1.  Layout clause — three distinct Zuschussfähige-Posten sub-totals,
        one per category: Kurtaxe, Übernachtung, Verpflegung. The
        rendered output must surface each label so a Krankenkasse
        reviewer can read off the three amounts.
    2.  Footer clause — the literal substring
        ``"Badekur/Ambulante Vorsorge §23 SGB V"`` must appear in the
        output (verbatim; this is the legal §23 SGB V citation that
        authorises the Krankenkasse to reimburse the Zuschussfähige
        Posten).

Convention notes
----------------
- The fixture factory (cached Satzung + age-anchored Guest) lives in
  ``tests/_factories``. We use it for ``make_hessen_satzung`` and
  ``make_guest`` to match the conventions of the other AC tests
  (test_reporting.py, test_calculator.py).
- We deliberately import from ``kurort_engine`` (the AC-6 public API
  surface) rather than from ``kurort_engine.rechnung`` directly so the
  test exercises the documented re-export contract.
- The ``folios`` argument is documented at module level only — the spec
  does not pin its exact shape, so the test uses a reasonable
  ``dict[str, list[Decimal]]`` form (one Decimal per night per category)
  and only asserts the rendered output honours the three labelled
  sub-totals and the footer. The green phase is free to refine the
  folios shape.

RED VERIFY
----------
These tests are expected to FAIL during the red phase. The failure mode
must be ``AssertionError`` (placeholder returns ``""``, signature
mismatch, missing labels, or missing footer string), NOT
``ImportError`` / ``AttributeError`` / ``TypeError`` / ``NotImplementedError``.
We enforce the failure mode by:

  1. Asserting the function signature matches the AC-5 contract FIRST
     via ``inspect.signature``. The placeholder has parameters
     ``(reservation, satzung, exemptions=None, out_path=None)`` — second
     and third params are wrong (should be ``satzung`` and ``folios``),
     and there is an unexpected ``out_path`` fourth parameter. Each of
     these is asserted via ``assert`` so a mismatch raises
     ``AssertionError``, never ``TypeError``.
  2. Calling ``build_badekur_rechnung`` with the three spec-documented
     positional arguments (the placeholder's first three params happen
     to be ``reservation, satzung, exemptions`` — so passing a folios
     dict as the third positional argument will be accepted by Python's
     argument binder without raising ``TypeError``; the empty return
     value then triggers the AssertionError on non-empty / non-blank
     content).
  3. Asserting on output TEXT (substrings, lengths) rather than on
     parsing structured objects — keeps the failure mode a plain
     ``AssertionError``.
"""
from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal

import pytest

import kurort_engine
from kurort_engine import (
    Guest,
    Reservation,
    Satzung,
    build_badekur_rechnung,
    calculate_kurtaxe_for_reservation,
)

from tests._factories import hessen_satzung, make_guest  # noqa: F401  (fixtures re-exported)


# ---------------------------------------------------------------------------
# AC-5 footer string (verbatim from spec.yaml:104)
# ---------------------------------------------------------------------------
#
# This is the §23 SGB V legal citation. Krankenkasse reviewers grep for it
# on the printed Rechnung before authorising reimbursement. Pinned here so
# a copy-paste typo in either the spec or the implementation surfaces as a
# single, focused assertion failure rather than a downstream parser error.
AC5_FOOTER_TEXT: str = "Badekur/Ambulante Vorsorge §23 SGB V"


# ---------------------------------------------------------------------------
# AC-5 Zuschussfähige Posten labels (verbatim from spec.yaml:102-103)
# ---------------------------------------------------------------------------
#
# The three sub-totals the Krankenkasse reimburses under §23 SGB V. The
# output must contain each label (case-sensitive) so a reviewer can read
# off the amount per category from the printed Rechnung.
AC5_ZUSCHUSSFAEHIGE_LABELS: tuple[str, ...] = (
    "Kurtaxe",
    "Übernachtung",
    "Verpflegung",
)


# ---------------------------------------------------------------------------
# AC-5 signature contract (shared helper across tests)
# ---------------------------------------------------------------------------

def _assert_ac5_signature() -> inspect.Signature:
    """Assert that ``build_badekur_rechnung`` matches the AC-5 contract.

    AC-5 mandates: ``build_badekur_rechnung(reservation, satzung, folios)``
    producing a string Rechnung. We enforce:

      - At least three positional parameters, in spec-documented order.
      - First parameter named ``reservation``.
      - Second parameter named ``satzung``.
      - Third parameter named ``folios`` (NOT ``exemptions``, NOT
        ``out_path`` — the placeholder uses ``exemptions`` as the third
        parameter, which is the wrong name).
      - Any fourth-and-later parameters are allowed but MUST be keyword
        only OR carry defaults (we don't pin defaults — the engine is
        free to add optional kwargs later — but we reject bare
        additional positional params because AC-5 pins exactly three).

    Returns the inspected ``inspect.Signature`` so callers can pass
    arguments using the documented parameter names via ``**``.
    """
    sig = inspect.signature(build_badekur_rechnung)
    params = list(sig.parameters.values())

    # Three documented positional params, in order.
    assert len(params) >= 3, (
        f"AC-5 contract requires (reservation, satzung, folios) — got signature "
        f"{sig!s} with only {len(params)} parameter(s)"
    )
    assert params[0].name == "reservation", (
        f"AC-5 contract: first parameter must be named 'reservation', "
        f"got {params[0].name!r}"
    )
    assert params[1].name == "satzung", (
        f"AC-5 contract: second parameter must be named 'satzung', "
        f"got {params[1].name!r}"
    )
    assert params[2].name == "folios", (
        f"AC-5 contract: third parameter must be named 'folios' (NOT "
        f"'exemptions', NOT 'out_path'), got {params[2].name!r}"
    )

    # Reject any additional parameters that are bare positional (no
    # default) — AC-5 pins exactly three positional parameters.
    for extra in params[3:]:
        assert extra.default is not inspect.Parameter.empty, (
            f"AC-5 contract: extra parameter {extra.name!r} must have a "
            f"default value (keyword-only or optional) — bare extra "
            f"positional parameters are not allowed"
        )

    return sig


# ---------------------------------------------------------------------------
# Helper: a sample folios dict (one Decimal per night per category)
# ---------------------------------------------------------------------------

def _sample_folios() -> dict[str, list[Decimal]]:
    """Return a two-night folios payload with Übernachtung + Verpflegung.

    Shape: ``{category_name: [per-night Decimal, ...]}``. The exact shape
    is not pinned by AC-5 — the green phase is free to choose between
    ``dict[str, list[Decimal]]`` / ``dict[str, Decimal]`` (totals) /
    ``list[dict]`` etc. This helper exists only so the red-phase test
    has a concrete input to pass to the placeholder; the assertions
    check the OUTPUT, not the input shape.
    """
    return {
        "übernachtung": [Decimal("100.00"), Decimal("100.00")],   # 2 nights @ €100
        "verpflegung": [Decimal("30.00"), Decimal("30.00")],      # 2 nights @ €30
    }


# ===========================================================================
# Test 1 — the spec test_oracle (AC-5 layout + footer)
# ===========================================================================

def test_ac5_badekur_rechnung_breaks_out_zuschussfaehige_posten_and_cites_paragraph(
    hessen_satzung,
) -> None:
    """AC-5 spec test_oracle: three Zuschussfähige sub-totals + §23 footer.

    Builds:
      - 1 Reservation with a single paying adult guest, 2 nights
        (2024-06-10 -> 2024-06-12).
      - The Hessen Bad Orb ``Satzung`` (rate band: adult = €2.50/day).
      - A two-night folios payload (Übernachtung + Verpflegung).

    The output must:
      (a) be a non-empty ``str`` (placeholder currently returns ``""``).
      (b) contain each of the three Zuschussfähige Posten labels —
          ``Kurtaxe``, ``Übernachtung``, ``Verpflegung`` — at least
          once each. The Krankenkasse reviewer reads these labels off
          the printed page to identify the reimbursable amounts.
      (c) contain the verbatim footer text
          ``"Badekur/Ambulante Vorsorge §23 SGB V"`` — the legal §23
          SGB V citation that authorises reimbursement of the
          Zuschussfähige Posten.
    """
    _assert_ac5_signature()

    reservation = Reservation(
        reservation_id="R-AC5-001",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),
        guests=(make_guest(age_years=35, name="Anna Badekur"),),
    )

    # Call the function. We pass the three documented positional
    # arguments in order; the placeholder accepts (reservation, satzung,
    # exemptions=None, out_path=None) so positional arity is fine — the
    # folios dict lands in the ``exemptions`` slot on the placeholder,
    # but Python's argument binder does NOT raise ``TypeError`` for a
    # type-mismatched third positional arg. The empty ``""`` return then
    # triggers the AssertionError below.
    rechnung = build_badekur_rechnung(reservation, hessen_satzung, _sample_folios())

    # ---- Type + non-empty contract ----
    assert isinstance(rechnung, str), (
        f"AC-5: build_badekur_rechnung must return str, got {type(rechnung).__name__}"
    )
    assert rechnung.strip(), (
        f"AC-5: rechnung output must not be empty/whitespace; got {rechnung!r}"
    )

    # ---- Layout clause: three Zuschussfähige Posten labels ----
    for label in AC5_ZUSCHUSSFAEHIGE_LABELS:
        assert label in rechnung, (
            f"AC-5: rechnung must contain Zuschussfähige-Posten label "
            f"{label!r} as one of the three sub-totals (Kurtaxe, "
            f"Übernachtung, Verpflegung). Output was:\n{rechnung}"
        )

    # ---- Footer clause: verbatim §23 SGB V citation ----
    assert AC5_FOOTER_TEXT in rechnung, (
        f"AC-5: rechnung footer must contain the verbatim reference "
        f"text {AC5_FOOTER_TEXT!r} (Krankenkasse §23 SGB V citation). "
        f"Output was:\n{rechnung}"
    )


# ===========================================================================
# Test 2 — pure signature contract (no output assertions)
# ===========================================================================

def test_ac5_rechnung_signature_is_reservation_satzung_folios() -> None:
    """AC-5: pin the public-API signature ``(reservation, satzung, folios)``.

    This is an independent, pure signature assertion that does not call
    the function. The placeholder's signature is
    ``(reservation, satzung, exemptions=None, out_path=None)`` which
    fails the ``folios`` and ``no-extras`` assertions. Failures are
    ``AssertionError`` (not ``TypeError``) because every check is an
    explicit ``assert``.
    """
    sig = _assert_ac5_signature()

    # The spec signature must be reconstructible from positional args.
    bound_kwargs = {
        "reservation": None,
        "satzung": None,
        "folios": None,
    }
    try:
        bound = sig.bind(**bound_kwargs)
    except TypeError as exc:
        pytest.fail(
            f"AC-5: signature {sig!s} must accept (reservation, satzung, "
            f"folios) as positional/keyword args, got TypeError: {exc}"
        )
    assert tuple(bound.arguments.keys()) == ("reservation", "satzung", "folios"), (
        f"AC-5: bound argument keys must be (reservation, satzung, "
        f"folios); got {tuple(bound.arguments.keys())!r}"
    )


# ===========================================================================
# Test 3 — Kurtaxe sub-total cross-checks against calculate_kurtaxe
# ===========================================================================

def test_ac5_rechnung_kurtaxe_subtotal_matches_calculator(hessen_satzung) -> None:
    """AC-5: the rendered Kurtaxe sub-total equals the calculator's total.

    For a single paying adult (€2.50/day) over 2 nights the Kurtaxe
    total per :func:`calculate_kurtaxe_for_reservation` is
    ``Decimal('5.00')``. The rendered Rechnung must surface this same
    value in the Kurtaxe sub-total so the Krankenkasse and the
    Hotel's Kurtaxe remittance reconcile.

    German Rechnungen typically render amounts with a comma decimal
    separator (e.g. ``5,00 EUR``); the engine is free to choose comma
    or dot, so we accept either form by asserting that BOTH the dot
    form (``5.00``) AND the comma form (``5,00``) appear in the output
    when normalised — the engine should pick one and stick to it. We
    fail loudly if neither appears.
    """
    _assert_ac5_signature()

    reservation = Reservation(
        reservation_id="R-AC5-KURTAX",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),
        guests=(make_guest(age_years=35, name="Anna Badekur"),),
    )

    # Calculator's per-reservation Kurtaxe total for 1 adult × 2 nights.
    expected_total: Decimal = calculate_kurtaxe_for_reservation(reservation, hessen_satzung)
    assert expected_total == Decimal("5.00"), (
        f"AC-5 cross-check precondition: calculator must return €5.00 for "
        f"1 adult × 2 nights under Hessen Bad Orb; got €{expected_total}. "
        f"If this fails, fix the calculator before changing the Rechnung."
    )

    rechnung = build_badekur_rechnung(reservation, hessen_satzung, _sample_folios())
    assert isinstance(rechnung, str) and rechnung.strip(), (
        f"AC-5: rechnung output must be a non-empty string; got {rechnung!r}"
    )

    # Isolate the Kurtaxe sub-total block from the output so the
    # assertion doesn't accidentally pass on a "5,00" appearing in a
    # Verpflegung row. Split on the "Kurtaxe" label, take everything
    # until the next Zuschussfähige-Posten label or end-of-document,
    # and search that block for the €5.00 amount.
    kurtaxe_marker = "Kurtaxe"
    assert kurtaxe_marker in rechnung, (
        f"AC-5: rechnung must contain the 'Kurtaxe' label to anchor the "
        f"Kurtaxe sub-total block. Output was:\n{rechnung}"
    )
    after_kurtaxe = rechnung.split(kurtaxe_marker, 1)[1]
    # Cut off at the next Zuschussfähige-Posten label if present, so we
    # only search within the Kurtaxe block.
    end_markers = [label for label in AC5_ZUSCHUSSFAEHIGE_LABELS if label != kurtaxe_marker]
    for end in end_markers:
        if end in after_kurtaxe:
            after_kurtaxe = after_kurtaxe.split(end, 1)[0]
            break

    # Accept either German ("5,00") or English ("5.00") decimal form.
    has_dot_form = "5.00" in after_kurtaxe
    has_comma_form = "5,00" in after_kurtaxe
    assert has_dot_form or has_comma_form, (
        f"AC-5: Kurtaxe sub-total block must contain the calculator's "
        f"€5.00 total (as '5.00' or '5,00'). Kurtaxe block was:\n"
        f"{after_kurtaxe!r}\nFull rechnung:\n{rechnung}"
    )


# ===========================================================================
# Test 4 — verbatim §23 SGB V footer (independent of layout clause)
# ===========================================================================

def test_ac5_rechnung_footer_cites_sgb_v_paragraph() -> None:
    """AC-5: footer must cite §23 SGB V verbatim (Krankenkasse reimbursement).

    Independent of the layout clause: this test asserts only that the
    output contains the literal substring
    ``"Badekur/Ambulante Vorsorge §23 SGB V"``. This is the legal
    citation that authorises the Krankenkasse to reimburse the
    Zuschussfähige Posten; missing it invalidates the Rechnung.

    A near-miss (e.g. missing the slash, lower-case "sgb", missing the
    "Ambulante Vorsorge" qualifier, substituting ASCII "Section" for
    "§") is a fail — the footer string is bit-for-bit pinned.
    """
    _assert_ac5_signature()

    reservation = Reservation(
        reservation_id="R-AC5-FOOTER",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),
        guests=(make_guest(age_years=35, name="Anna Badekur"),),
    )
    satzung: Satzung = kurort_engine.load_profile("hessen", "bad_orb")

    rechnung = build_badekur_rechnung(reservation, satzung, _sample_folios())
    assert isinstance(rechnung, str) and rechnung.strip(), (
        f"AC-5: rechnung output must be a non-empty string; got {rechnung!r}"
    )

    # Verbatim check — bit-for-bit match against the pinned string.
    assert AC5_FOOTER_TEXT in rechnung, (
        f"AC-5: rechnung must contain the verbatim footer text "
        f"{AC5_FOOTER_TEXT!r} (the §23 SGB V Krankenkasse citation). "
        f"Output was:\n{rechnung}"
    )

    # Additional guard: the §-character (U+00A7) MUST be present, not
    # an ASCII fallback ("Section 23" or "Paragraph 23"). German legal
    # citations use §; substituting it breaks OCR-based reviewers.
    assert "§" in rechnung, (
        f"AC-5: rechnung must contain the § character (U+00A7), not an "
        f"ASCII fallback (e.g. 'Section 23'). Output was:\n{rechnung}"
    )

    # Additional guard: "23 SGB V" must appear (the specific paragraph
    # and statute — §23 of the Fünftes Buch Sozialgesetzbuch).
    assert "23 SGB V" in rechnung, (
        f"AC-5: rechnung must cite '23 SGB V' (specific paragraph + "
        f"statute) for §23 SGB V Badekur/Ambulante Vorsorge. "
        f"Output was:\n{rechnung}"
    )