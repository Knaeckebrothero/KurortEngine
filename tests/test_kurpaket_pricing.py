"""Q5.7 AC-11 — kurpaket_pricing module test surface.

AC-11 contract (verbatim from spec.yaml):

    When pricing is computed for templates B/C/D (HHB-In-Balance
    7/10/14-Nächte canonical tiers) THEN the ``kurpaket_pricing`` module
    shall return prices within ±10% of the HHB €1,169-per-person reference
    (i.e. €1,052.10 to €1,285.90 inclusive), AT LEAST ONCE per template.

RED VERIFY
----------
Test MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check. Per the iter-15 pinned rule
"never mock the unit under test", we exercise the public pricing function
with concrete booking payloads and assert the contract via Decimal
comparisons against the ±10% bracket.
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal

# ---------------------------------------------------------------------------
# Reference values per spec.yaml AC-11 + assumption A-2
# ---------------------------------------------------------------------------
HHB_REFERENCE_EUR: Decimal = Decimal("1169.00")
TOLERANCE_FRACTION: Decimal = Decimal("0.10")
PRICE_BRACKET_LOW_EUR: Decimal = HHB_REFERENCE_EUR * (Decimal("1") - TOLERANCE_FRACTION)
PRICE_BRACKET_HIGH_EUR: Decimal = HHB_REFERENCE_EUR * (Decimal("1") + TOLERANCE_FRACTION)
# 1,169.00 × 0.90 = 1,052.10; 1,169.00 × 1.10 = 1,285.90
assert PRICE_BRACKET_LOW_EUR == Decimal("1052.10"), (
    f"AC-11: -10% of {HHB_REFERENCE_EUR} must equal 1052.10; got {PRICE_BRACKET_LOW_EUR}"
)
assert PRICE_BRACKET_HIGH_EUR == Decimal("1285.90"), (
    f"AC-11: +10% of {HHB_REFERENCE_EUR} must equal 1285.90; got {PRICE_BRACKET_HIGH_EUR}"
)


def _pricing_module_is_importable() -> str:
    """Pre-check: kurpaket_pricing module must exist."""
    found = importlib.util.find_spec("kurort_engine.kurpaket_pricing")
    assert found is not None, (
        "kurort_engine.kurpaket_pricing is not importable — green phase "
        "must create repo/src/kurort_engine/kurpaket_pricing.py before "
        f"this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _get_pricing_module():
    """Import the pricing module after the find_spec guard."""
    _pricing_module_is_importable()
    import kurort_engine.kurpaket_pricing as _pricing  # noqa: E402
    assert _pricing is not None, "importlib returned None — module is None"
    return _pricing


def _coerce_price(value: object) -> Decimal | None:
    """Coerce various price representations to Decimal; return None on failure."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str) and value.strip():
        try:
            return Decimal(value)
        except Exception:  # noqa: BLE001 — coerce attempt failure
            return None
    if isinstance(value, dict):
        # Common wrapper: {"price_eur": "1169.00"} or {"total": Decimal("1169.00")}
        for key in ("price_eur", "total", "amount", "value"):
            if key in value:
                coerced = _coerce_price(value[key])
                if coerced is not None:
                    return coerced
        return None
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return _coerce_price(value[0])
    return None


# ===========================================================================
# AC-11 — HHB In-Balance benchmark: B/C/D templates pricing within ±10%
# ===========================================================================

def test_ac11_hhb_in_balance_benchmark_within_pm10pct() -> None:
    """AC-11 spec test_oracle.

    Asserts that for each of templates B (7-Nächte), C (10-Nächte), and
    D (14-Nächte), the pricing function returns a price within ±10% of the
    HHB In-Balance €1,169-per-person reference (i.e. in the inclusive range
    €1,052.10..€1,285.90) at LEAST ONCE per template.

    Per the iter-15 pinned rule "never mock the unit under test", the test
    exercises the public pricing API with concrete payloads and uses Decimal
    comparisons. The function's exact name and signature are tolerant: the
    test checks for ``price_for_template`` / ``compute_price`` /
    ``quote_price`` / ``price`` shapes via duck-typing.
    """
    _pricing_module_is_importable()
    pr_mod = _get_pricing_module()

    # ---- Locate the public pricing entry point ----
    price_fn = (
        getattr(pr_mod, "price_for_template", None)
        or getattr(pr_mod, "compute_price", None)
        or getattr(pr_mod, "quote_price", None)
        or getattr(pr_mod, "calculate_price", None)
        or getattr(pr_mod, "price", None)
        or getattr(pr_mod, "quote", None)
    )
    assert callable(price_fn), (
        "AC-11: kurpaket_pricing must expose a callable price_for_template / "
        "compute_price / quote_price / calculate_price / price / quote "
        f"function; found: {[n for n in dir(pr_mod) if not n.startswith('_')]!r}"
    )

    # Per-template concrete bookings
    template_specs = (
        ("B", 7),  # Classic 7-Nächte
        ("C", 10),  # Premium 10-Nächte
        ("D", 14),  # Intensiv 14-Nächte
    )

    in_bracket_per_template: dict[str, bool] = {code: False for code, _ in template_specs}
    last_observed: dict[str, Decimal | None] = {code: None for code, _ in template_specs}

    for template_code, nights in template_specs:
        booking = {
            "template_code": template_code,
            "nights": nights,
            "guests": 1,
        }

        # The pricing function may accept kwargs OR a single booking dict.
        # Try both shapes.
        result = None
        try:
            result = price_fn(template_code=template_code, nights=nights, guests=1)
        except TypeError:
            try:
                result = price_fn(booking)
            except TypeError as exc:
                raise AssertionError(
                    "AC-11: kurpaket_pricing entry point must accept either "
                    "keyword args (template_code, nights, guests) OR a single "
                    f"booking dict; neither worked. Last TypeError: {exc!r}"
                ) from exc

        assert result is not None, (
            f"AC-11: pricing returned None for template {template_code!r} "
            f"({nights} nights)"
        )

        # Coerce the result to a Decimal price value
        price = _coerce_price(result)
        assert price is not None, (
            f"AC-11: pricing result for template {template_code!r} could not "
            f"be coerced to a Decimal price; got {result!r} (type "
            f"{type(result).__name__})"
        )

        last_observed[template_code] = price

        # ---- The price must fall within ±10% of HHB €1,169 reference ----
        assert PRICE_BRACKET_LOW_EUR <= price <= PRICE_BRACKET_HIGH_EUR, (
            f"AC-11: HHB In-Balance benchmark requires template "
            f"{template_code!r} ({nights} nights) pricing within ±10% of "
            f"{HHB_REFERENCE_EUR} EUR per person, inclusive. Expected range: "
            f"{PRICE_BRACKET_LOW_EUR}..{PRICE_BRACKET_HIGH_EUR} EUR; got "
            f"{price} EUR (raw result: {result!r})"
        )

        in_bracket_per_template[template_code] = True

    # ---- Every template must have landed at LEAST ONCE in the bracket ----
    # The spec says "AT LEAST ONCE per template" — a single invocation per
    # template suffices; the loop above covers exactly that.
    missing = [c for c, ok in in_bracket_per_template.items() if not ok]
    assert not missing, (
        "AC-11: HHB In-Balance benchmark must produce a price within ±10% "
        f"of {HHB_REFERENCE_EUR} EUR per person at LEAST ONCE for templates "
        f"{missing!r}. Last-observed prices: {last_observed!r}"
    )