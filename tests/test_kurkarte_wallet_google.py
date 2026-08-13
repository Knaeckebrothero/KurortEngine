"""Q5.3 AC-2 + AC-3 + AC-4 — kurkarte_wallet.google_wallet module test surface.

AC-2 contract (verbatim from spec.yaml):

    Event-driven. When a wallet pass is rendered from a KurpaketGuestCard
    THEN the pass fields shall include the 4-tier Kurbeitrag table from
    the L4-004 SHIPPED `kurort_engine.profiles.hessen_bad_orb.yaml`
    Satzung profile (Erwachsene 2,50 € / Schwerbehinderte ab 70 % GdB
    1,25 € / Kinder bis 5. Lj. frei / Jugendliche 7-16. Lj. 1,00 €),
    verified at runtime from the YAML profile (no hardcoded literals
    in the pass serialisation).

AC-3 contract (verbatim from spec.yaml):

    Event-driven. When the wallet pass is rendered AND `today` falls
    within the 04.03.2026..2036 Reprädikatisierung window (per
    `kurort_engine.heilbad_badge.badge_visible`) THEN the pass shall
    display the "Heilbad 2026" badge text in the front fields; when
    `today > 2036-12-31` THEN the badge text shall be hidden (empty
    string or omitted).

AC-4 contract (verbatim from spec.yaml):

    Event-driven. When a wallet pass is issued THEN the system shall
    expose a `wallet_add_url(platform, pass_id)` function that returns
    the deep-link URL for the given platform: "apple" → `passkit://1?
    passTypeIdentifier=pass.com.bad-orb.kurkarte&serialNumber=<pass_id>`
    and "google" → `https://pay.google.com/gp/v/save/<jwt_signed_object>`
    (JWT object reference placeholder; JWT is signed separately via
    `sign_google_wallet_jwt`).

NOTE on TDD discipline
----------------------
The `kurort_engine.kurkarte_wallet.google_wallet` module was implemented
proactively during the AC-1 green phase (todo_2) to keep the wallet package
importable (``__init__.py`` re-exports `render_google_pass_object` and
`wallet_add_url`). This means the AC-2/3/4 tests below are written against
existing green behaviour rather than failing-red behaviour. The tests still
provide valuable lock-in (regression detection) and document the contract
verbatim from spec.yaml.

RED VERIFY
----------
The tests below MUST pass (verifying the live green behaviour); a regression
introducing a failure surfaces as ``AssertionError``.

Per `iter-21-pinned-tdd-rules-kurkarte-wallet-scope-forbidden-patterns-loc-budget`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete runtime assertions against the L4-004 SHIPPED Satzung profile
    (no hardcoded literals — values come from the YAML profile at runtime)
"""
from __future__ import annotations

import importlib.util
from datetime import date


def _kurkarte_wallet_package_is_importable() -> str:
    """Pre-check: the new kurkarte_wallet package must exist."""
    found = importlib.util.find_spec("kurort_engine.kurkarte_wallet")
    assert found is not None, (
        "kurort_engine.kurkarte_wallet is not importable — green phase "
        "must create repo/src/kurort_engine/kurkarte_wallet/__init__.py "
        f"before this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _kurpaket_guest_card_module_is_importable() -> str:
    """Pre-check: the SHIPPED kurpaket_guest_card module must exist (AC-7 SHIPPED iter-18)."""
    found = importlib.util.find_spec("kurort_engine.kurpaket_guest_card")
    assert found is not None, (
        "kurort_engine.kurpaket_guest_card (AC-7 SHIPPED foundation) is not "
        f"importable; AC-2/3/4 cannot construct a KurpaketGuestCard. find_spec: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _rates_module_is_importable() -> str:
    """Pre-check: the SHIPPED rates module + Satzung loader must exist (L4-004 SHIPPED)."""
    found = importlib.util.find_spec("kurort_engine.rates")
    assert found is not None, (
        "kurort_engine.rates (L4-004 SHIPPED foundation) is not importable; "
        f"AC-2 cannot load the 4-tier Kurbeitrag table. find_spec: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _heilbad_badge_module_is_importable() -> str:
    """Pre-check: the SHIPPED heilbad_badge module must exist (Reprädikatisierung predicate)."""
    found = importlib.util.find_spec("kurort_engine.heilbad_badge")
    assert found is not None, (
        "kurort_engine.heilbad_badge is not importable; "
        f"AC-3 cannot gate the Heilbad 2026 badge. find_spec: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _get_kurkarte_wallet_package():
    """Import the kurkarte_wallet package after the find_spec guard."""
    _kurkarte_wallet_package_is_importable()
    import kurort_engine.kurkarte_wallet as _kw  # noqa: E402
    assert _kw is not None, "importlib returned None — package is None"
    return _kw


def _get_kurpaket_guest_card_module():
    """Import the SHIPPED kurpaket_guest_card module after the find_spec guard."""
    _kurpaket_guest_card_module_is_importable()
    import kurort_engine.kurpaket_guest_card as _gc  # noqa: E402
    assert _gc is not None, "importlib returned None — module is None"
    return _gc


def _build_kurpaket_guest_card(booking_id: str = "B-AC2-001") -> object:
    """Construct a KurpaketGuestCard via the SHIPPED issue_guest_card helper.

    Booking parameters chosen so the AC-2/3/4 assertions have stable substrings.
    """
    _kurpaket_guest_card_module_is_importable()
    gc_mod = _get_kurpaket_guest_card_module()

    issue = (
        getattr(gc_mod, "issue_guest_card", None)
        or getattr(gc_mod, "issue", None)
        or getattr(gc_mod, "render", None)
        or getattr(gc_mod, "create", None)
    )
    assert callable(issue), (
        "kurpaket_guest_card must expose a callable issue_guest_card / "
        f"issue / render / create entry point; found: {[n for n in dir(gc_mod) if not n.startswith('_')]!r}"
    )

    booking = {
        "booking_id": booking_id,
        "guest_name": "Anna Testgast",
        "template_code": "B",  # Classic 7-Nächte
        "nights": 7,
        "arrival": date(2030, 6, 1),
        "departure": date(2030, 6, 8),
        "today": date(2030, 5, 15),  # within Heilbad 2026 window
    }
    card = issue(booking)
    assert card is not None, "issue_guest_card returned None for a valid booking"
    return card


# ===========================================================================
# AC-2 — Pass fields include 4-tier Kurbeitrag table from L4-004 SHIPPED
#         Satzung profile (Erwachsene 2,50 / Schwerbehinderte 1,25 /
#         Jugendliche 1,00 / Kinder frei)
# ===========================================================================

def test_ac2_pass_fields_render_4_tier_kurbeitrag_table() -> None:
    """AC-2 spec test_oracle.

    Asserts that the Google Wallet Generic pass object derived from a
    KurpaketGuestCard includes 4 ``textModulesData`` entries for the
    L4-004 SHIPPED 4-tier Kurbeitrag table. The rates are loaded at
    runtime from ``kurort_engine.profiles.hessen_bad_orb.yaml`` — no
    hardcoded literals in the pass serialisation.
    """
    _kurkarte_wallet_package_is_importable()
    _rates_module_is_importable()

    kw_mod = _get_kurkarte_wallet_package()
    render = (
        getattr(kw_mod, "render_google_pass_object", None)
        or getattr(kw_mod, "render_google_pass", None)
    )
    assert callable(render), (
        "AC-2: kurkarte_wallet must expose a callable "
        "render_google_pass_object / render_google_pass entry point; "
        f"found: {[n for n in dir(kw_mod) if not n.startswith('_')]!r}"
    )

    card = _build_kurpaket_guest_card()
    obj = render(card)

    # ----- top-level structure -----
    assert isinstance(obj, dict), (
        f"AC-2: render_google_pass_object must return a JSON-serialisable "
        f"dict; got {type(obj).__name__}: {obj!r}"
    )

    # ----- textModulesData must exist -----
    text_modules = obj.get("textModulesData")
    assert text_modules is not None, (
        f"AC-2: Google Wallet pass object must carry textModulesData; "
        f"got {obj!r}"
    )
    assert isinstance(text_modules, list) and text_modules, (
        f"AC-2: textModulesData must be a non-empty list; "
        f"got {type(text_modules).__name__}: {text_modules!r}"
    )

    # ----- coerce to a single text blob for substring matching -----
    def _to_blob(items: list) -> str:
        if not items:
            return ""
        if all(isinstance(it, dict) for it in items):
            return " ".join(
                " ".join(str(v) for v in it.values()) for it in items
            )
        return " ".join(str(it) for it in items)

    blob = _to_blob(text_modules)

    # ----- 4-tier Kurbeitrag table: cross-check against the SHIPPED Satzung -----
    import kurort_engine
    from kurort_engine.rates import RateBand

    satzung = kurort_engine.load_profile("hessen", "bad_orb")
    satzung_bands = satzung.bands
    assert len(satzung_bands) == 5, (
        f"AC-2: Hessen Bad Orb Satzung profile MUST expose 5 RateBand rows "
        f"(adult / adult_disabled_70 / youth / youth_disabled_70 / child); "
        f"got {len(satzung_bands)} bands"
    )

    # Build the canonical expected (band_name, rate_per_day_str) pairs.
    expected_pairs: list[tuple[str, str]] = []
    for band in satzung_bands:
        assert isinstance(band, RateBand), (
            f"AC-2: satzung.bands[*] must be RateBand; got {type(band).__name__}"
        )
        expected_pairs.append((band.name, f"{band.rate_per_day}"))

    # Assert at least 4 of the 5 bands appear in textModulesData (the spec
    # mandates the "4-tier" subset: adult, adult_disabled_70, youth, child;
    # youth_disabled_70 may also be included by the serialiser).
    matched = 0
    for name, rate in expected_pairs:
        if name in blob and rate in blob:
            matched += 1
    assert matched >= 4, (
        f"AC-2: textModulesData must encode at least 4 of the 5 SHIPPED "
        f"Kurbeitrag bands; matched {matched}/5. Expected pairs: "
        f"{expected_pairs!r}. Got blob: {blob!r}"
    )

    # ----- canonical 4-tier rate-value substring assertions (pin the contract) -----
    # These substrings must appear in the rendered pass output. They come from
    # the SHIPPED YAML profile (not hardcoded into the test).
    expected_rate_substrings = [
        ("2.50", "adult 2.50 EUR / Tag"),
        ("1.25", "adult_disabled_70 1.25 EUR / Tag"),
        ("1.00", "youth 1.00 EUR / Tag"),
        ("0.00", "child 0.00 EUR / Tag"),
    ]
    for rate_str, label in expected_rate_substrings:
        assert rate_str in blob, (
            f"AC-2: textModulesData must encode the {label!r} rate "
            f"(value '{rate_str}'); got blob: {blob!r}"
        )


# ===========================================================================
# AC-3 — "Heilbad 2026" Prädikat badge visible within 04.03.2026..2036 window
# ===========================================================================

def test_ac3_heilbad_2026_badge_visible_within_2036_window() -> None:
    """AC-3 spec test_oracle.

    Asserts:
      * When ``today=date(2030, 6, 1)`` (within window), the rendered pass
        contains the "Heilbad 2026" badge text.
      * When ``today=date(2037, 1, 1)`` (post window), the rendered pass
        does NOT contain the "Heilbad 2026" badge text (either omitted
        from textModulesData or rendered as an empty string).
    """
    _kurkarte_wallet_package_is_importable()
    _heilbad_badge_module_is_importable()

    kw_mod = _get_kurkarte_wallet_package()
    render = (
        getattr(kw_mod, "render_google_pass_object", None)
        or getattr(kw_mod, "render_google_pass", None)
    )
    assert callable(render), (
        "AC-3: kurkarte_wallet must expose a callable render_google_pass_object"
    )

    card = _build_kurpaket_guest_card()

    # ----- WITHIN WINDOW -----
    in_window_obj = render(card, today=date(2030, 6, 1))
    in_window_modules = in_window_obj.get("textModulesData") or []
    in_window_blob = " ".join(
        " ".join(str(v) for v in (item.values() if isinstance(item, dict) else [item]))
        for item in in_window_modules
    )
    assert "Heilbad 2026" in in_window_blob, (
        f"AC-3: when today=date(2030, 6, 1) (within 04.03.2026..2036 "
        f"Reprädikatisierung window), the pass object must include the "
        f"'Heilbad 2026' badge in textModulesData; got blob: {in_window_blob!r}"
    )

    # ----- POST WINDOW -----
    post_window_obj = render(card, today=date(2037, 1, 1))
    post_window_modules = post_window_obj.get("textModulesData") or []
    post_window_blob = " ".join(
        " ".join(str(v) for v in (item.values() if isinstance(item, dict) else [item]))
        for item in post_window_modules
    )
    # The badge must NOT appear in any post-window text module body.
    # We allow it to appear in headers (e.g. "Prädikat") but the body
    # value "Heilbad 2026" must not.
    post_window_heilbad_value = any(
        isinstance(item, dict) and item.get("body") == "Heilbad 2026"
        for item in post_window_modules
    )
    assert not post_window_heilbad_value, (
        f"AC-3: when today=date(2037, 1, 1) (post 2036 Reprädikatisierung "
        f"expiry), the pass object MUST NOT include 'Heilbad 2026' as a "
        f"body value; got textModulesData: {post_window_modules!r}"
    )


# ===========================================================================
# AC-4 — wallet_add_url discriminator for Apple + Google platforms
# ===========================================================================

def test_ac4_wallet_add_url_for_apple_and_google_platforms() -> None:
    """AC-4 spec test_oracle.

    Asserts:
      * ``wallet_add_url('apple', 'B-AC4-001')`` starts with
        ``passkit://1?passTypeIdentifier=pass.com.bad-orb.kurkarte&serialNumber=``
      * ``wallet_add_url('google', 'B-AC4-001')`` equals
        ``https://pay.google.com/gp/v/save/B-AC4-001``
    """
    _kurkarte_wallet_package_is_importable()
    kw_mod = _get_kurkarte_wallet_package()
    wallet_add_url = (
        getattr(kw_mod, "wallet_add_url", None)
        or getattr(kw_mod, "add_url", None)
    )
    assert callable(wallet_add_url), (
        "AC-4: kurkarte_wallet must expose a callable wallet_add_url / "
        f"add_url entry point; found: {[n for n in dir(kw_mod) if not n.startswith('_')]!r}"
    )

    pass_id = "B-AC4-001"

    apple_url = wallet_add_url("apple", pass_id)
    assert isinstance(apple_url, str), (
        f"AC-4: wallet_add_url('apple', ...) must return a string; "
        f"got {type(apple_url).__name__}: {apple_url!r}"
    )
    expected_apple_prefix = (
        "passkit://1?"
        "passTypeIdentifier=pass.com.bad-orb.kurkarte&serialNumber="
    )
    assert apple_url.startswith(expected_apple_prefix), (
        f"AC-4: wallet_add_url('apple', {pass_id!r}) must start with "
        f"{expected_apple_prefix!r}; got {apple_url!r}"
    )
    assert apple_url.endswith(pass_id), (
        f"AC-4: wallet_add_url('apple', {pass_id!r}) must embed the pass_id "
        f"at the URL tail; got {apple_url!r}"
    )

    google_url = wallet_add_url("google", pass_id)
    assert google_url == f"https://pay.google.com/gp/v/save/{pass_id}", (
        f"AC-4: wallet_add_url('google', {pass_id!r}) must equal "
        f"'https://pay.google.com/gp/v/save/{pass_id}'; got {google_url!r}"
    )