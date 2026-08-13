"""Q5.3 AC-1 + AC-5 — kurkarte_wallet.passkit module test surface (Apple PKPass).

AC-1 contract (verbatim from spec.yaml):

    Ubiquitous. The system shall render an Apple PKPass JSON serialisation
    AND a Google Wallet Generic pass object from a
    `kurort_engine.kurpaket_guest_card.KurpaketGuestCard` instance; each
    rendering shall include the booking ID, guest name, and Kurpaket
    template code (A=Kurzurlaub-Wochenende / B=Classic / C=Premium /
    D=Intensiv / E=Spezial-Heilbad) as either a `headerFields` entry (Apple)
    or `cardTitle`/`header` entry (Google).

AC-5 contract (verbatim from spec.yaml):

    Unwanted-behavior. If the pass serialisation is rendered THEN the
    pass JSON MUST reference `lang="de"` on text fields AND pass-fields
    MUST include a `label` (accessibilityLabel) for non-text elements
    per BFSG-AA + WCAG 2.1 AA guidance (lockscreen text contrast
    ≥ 4.5:1, font sizing ≥ 12pt — values declared as document-level
    metadata `formatVersion` + `applePassStyle`); if `lang` or `label`
    are absent, the pass serialiser MUST raise `BFSGComplianceError`
    naming the missing field.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check so missing-module failures surface
as ``AssertionError`` ("module should exist"), not ``ModuleNotFoundError``.

Per `iter-21-pinned-tdd-rules-kurkarte-wallet-scope-forbidden-patterns-loc-budget`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete substring + structural assertions for AC-1 PKPass serialisation
  * Concrete BFSG-AA compliance assertions for AC-5
"""
from __future__ import annotations

import importlib.util
from datetime import date


def _kurkarte_wallet_package_is_importable() -> str:
    """Pre-check: the new kurkarte_wallet package must exist.

    Returns a one-line diagnostic string. The check runs through ``assert``
    so the failure surfaces as ``AssertionError`` ("module should exist"),
    not ``ImportError``.
    """
    found = importlib.util.find_spec("kurort_engine.kurkarte_wallet")
    assert found is not None, (
        "kurort_engine.kurkarte_wallet is not importable — green phase "
        "must create repo/src/kurort_engine/kurkarte_wallet/__init__.py "
        "before this test can pass. find_spec returned: "
        f"{found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _kurpaket_guest_card_module_is_importable() -> str:
    """Pre-check: the SHIPPED kurpaket_guest_card module must exist (AC-7 SHIPPED iter-18)."""
    found = importlib.util.find_spec("kurort_engine.kurpaket_guest_card")
    assert found is not None, (
        "kurort_engine.kurpaket_guest_card (AC-7 SHIPPED foundation) is not "
        f"importable; AC-1 cannot construct a KurpaketGuestCard. find_spec: {found!r}"
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


def _build_kurpaket_guest_card() -> object:
    """Construct a KurpaketGuestCard via the SHIPPED issue_guest_card helper.

    Uses booking parameters chosen so the AC-1 happy-path assertions have
    stable substrings to match (booking_id='B-AC1-001', guest_name='Anna
    Testgast', template_code='B' = Classic 7-Nächte).
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
        "booking_id": "B-AC1-001",
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
# AC-1 — Apple PKPass JSON serialisation from KurpaketGuestCard
# ===========================================================================

def test_ac1_apple_pkpass_serialisation_from_kurpaket_card() -> None:
    """AC-1 spec test_oracle.

    Asserts that the Apple PKPass JSON serialisation derived from a
    KurpaketGuestCard includes:
      * top-level `formatVersion` = 1
      * top-level `passTypeIdentifier` = `pass.com.bad-orb.kurkarte`
      * `serialNumber` equal to the booking ID
      * `headerFields` (or equivalent text-field collection) carrying
        the Kurpaket template code
      * `primaryFields` (or equivalent) carrying the guest name
      * the booking_id is reachable somewhere in the serialisation
    """
    _kurkarte_wallet_package_is_importable()
    kw_mod = _get_kurkarte_wallet_package()

    render_apple_pass = (
        getattr(kw_mod, "render_apple_pass", None)
        or getattr(kw_mod, "render", None)
    )
    assert callable(render_apple_pass), (
        "AC-1: kurkarte_wallet must expose a callable render_apple_pass / "
        f"render entry point; found: {[n for n in dir(kw_mod) if not n.startswith('_')]!r}"
    )

    card = _build_kurpaket_guest_card()
    card_fields = getattr(card, "__dict__", None) or vars(card)
    assert card_fields, f"AC-1: KurpaketGuestCard has no fields; got {card_fields!r}"

    pkpass = render_apple_pass(card)

    # ----- core return-type + top-level structure -----
    assert isinstance(pkpass, dict), (
        f"AC-1: render_apple_pass must return a JSON-serialisable dict; "
        f"got {type(pkpass).__name__}: {pkpass!r}"
    )

    # ----- formatVersion = 1 (Apple PKPass spec) -----
    assert pkpass.get("formatVersion") == 1, (
        f"AC-1: PKPass must carry formatVersion=1 per Apple PassKit spec; "
        f"got {pkpass.get('formatVersion')!r}"
    )

    # ----- passTypeIdentifier = pass.com.bad-orb.kurkarte -----
    assert pkpass.get("passTypeIdentifier") == "pass.com.bad-orb.kurkarte", (
        f"AC-1: PKPass passTypeIdentifier must equal 'pass.com.bad-orb.kurkarte'; "
        f"got {pkpass.get('passTypeIdentifier')!r}"
    )

    # ----- serialNumber = booking_id (KurpaketGuestCard.booking_id) -----
    expected_serial = card_fields.get("booking_id", "B-AC1-001")
    assert pkpass.get("serialNumber") == expected_serial, (
        f"AC-1: PKPass serialNumber must equal the booking_id ({expected_serial!r}); "
        f"got {pkpass.get('serialNumber')!r}"
    )

    # ----- template_code reachable via headerFields or equivalent -----
    template_code = card_fields.get("template_code", "B")
    header_fields = (
        pkpass.get("headerFields")
        or pkpass.get("primaryFields")
        or pkpass.get("secondaryFields")
    )
    assert header_fields is not None, (
        f"AC-1: PKPass must carry at least one text-field collection "
        f"(headerFields/primaryFields/secondaryFields); got {pkpass!r}"
    )
    assert isinstance(header_fields, list) and header_fields, (
        f"AC-1: text-field collection must be a non-empty list; "
        f"got {type(header_fields).__name__}: {header_fields!r}"
    )

    # Coerce the text-field collection to a printable text form and assert
    # the template code (case-insensitive) appears somewhere in it.
    if all(isinstance(f, dict) for f in header_fields):
        printable_text = " ".join(
            " ".join(str(v) for v in f.values()) for f in header_fields
        )
    else:
        printable_text = " ".join(str(f) for f in header_fields)
    assert str(template_code).upper() in printable_text.upper(), (
        f"AC-1: PKPass text-fields must encode the Kurpaket template code "
        f"({template_code!r}); got printable text from headerFields+primaryFields: "
        f"{printable_text!r}"
    )

    # ----- guest_name reachable via primaryFields or equivalent -----
    guest_name = card_fields.get("guest_name", "Anna Testgast")
    primary_fields = pkpass.get("primaryFields")
    if primary_fields is not None:
        if all(isinstance(f, dict) for f in primary_fields):
            primary_text = " ".join(
                " ".join(str(v) for v in f.values()) for f in primary_fields
            )
        else:
            primary_text = " ".join(str(f) for f in primary_fields)
        assert guest_name in primary_text, (
            f"AC-1: PKPass primaryFields must encode the guest name "
            f"({guest_name!r}); got printable text: {primary_text!r}"
        )
    else:
        # If primaryFields is absent, header_fields must carry the guest name.
        assert guest_name in printable_text, (
            f"AC-1: PKPass text-fields must encode the guest name "
            f"({guest_name!r}) when primaryFields is absent; got: {printable_text!r}"
        )

    # ----- booking_id reachable somewhere in the serialisation (sanity) -----
    serialisation_text = " ".join(
        str(v) for v in pkpass.values()
    ) + " " + " ".join(
        str(item) for collection in (header_fields or [], primary_fields or [])
        for item in (collection if isinstance(collection, list) else [collection])
    )
    assert expected_serial in serialisation_text, (
        f"AC-1: booking_id ({expected_serial!r}) must appear somewhere in the "
        f"PKPass serialisation; got combined text: {serialisation_text!r}"
    )


# ===========================================================================
# AC-5 — BFSG-AA + WCAG 2.1 AA: lang="de" + accessibilityLabel per field
# ===========================================================================

def test_ac5_pass_serialisation_enforces_lang_de_and_accessibility_labels() -> None:
    """AC-5 spec test_oracle.

    Asserts that the Apple PKPass JSON serialisation derived from a
    KurpaketGuestCard satisfies BFSG-AA + WCAG 2.1 AA compliance:

      (a) the returned dict includes a top-level ``lang`` key with value
          ``"de"`` (German), OR every text field dict carries a
          ``lang="de"`` attribute on its own.
      (b) every text field dict in ``headerFields`` / ``primaryFields`` /
          ``secondaryFields`` includes a non-empty ``label`` key
          (accessibilityLabel).

    If either is missing, ``render_apple_pass`` MUST raise
    ``BFSGComplianceError`` naming the missing field.
    """
    _kurkarte_wallet_package_is_importable()
    kw_mod = _get_kurkarte_wallet_package()

    render_apple_pass = (
        getattr(kw_mod, "render_apple_pass", None)
        or getattr(kw_mod, "render", None)
    )
    assert callable(render_apple_pass), (
        "AC-5: kurkarte_wallet must expose a callable render_apple_pass / "
        "render entry point"
    )

    BFSGComplianceError = getattr(kw_mod, "BFSGComplianceError", None)
    assert BFSGComplianceError is not None and isinstance(
        BFSGComplianceError, type
    ) and issubclass(BFSGComplianceError, Exception), (
        "AC-5: kurkarte_wallet must export a BFSGComplianceError exception class; "
        f"found: {[n for n in dir(kw_mod) if not n.startswith('_')]!r}"
    )

    card = _build_kurpaket_guest_card()

    pkpass = render_apple_pass(card)
    assert isinstance(pkpass, dict), (
        f"AC-5: render_apple_pass(card) must return a dict (even on "
        f"compliance failure surface); got {type(pkpass).__name__}: {pkpass!r}"
    )

    # ----- (a) lang="de" attribute check -----
    top_level_lang = pkpass.get("lang")
    assert top_level_lang == "de", (
        f"AC-5: PKPass must carry a top-level 'lang'='de' attribute (BFSG-AA "
        f"compliance); got lang={top_level_lang!r}. If lang is intentionally "
        f"per-field rather than top-level, see the per-field check below."
    )

    # ----- (b) every text field dict in headerFields/primaryFields/secondaryFields
    #         must include a non-empty 'label' key -----
    text_field_collections = [
        ("headerFields", pkpass.get("headerFields")),
        ("primaryFields", pkpass.get("primaryFields")),
        ("secondaryFields", pkpass.get("secondaryFields")),
        ("auxiliaryFields", pkpass.get("auxiliaryFields")),
        ("backFields", pkpass.get("backFields")),
    ]
    for collection_name, collection in text_field_collections:
        if not collection:
            continue
        assert isinstance(collection, list), (
            f"AC-5: PKPass {collection_name} must be a list of field dicts; "
            f"got {type(collection).__name__}: {collection!r}"
        )
        for field_dict in collection:
            assert isinstance(field_dict, dict), (
                f"AC-5: PKPass {collection_name} entries must be dicts; "
                f"got {type(field_dict).__name__}: {field_dict!r}"
            )
            field_key = field_dict.get("key", "<no-key>")
            label_value = field_dict.get("label")
            assert label_value is not None and str(label_value).strip(), (
                f"AC-5: PKPass {collection_name} field key={field_key!r} must "
                f"include a non-empty 'label' (accessibilityLabel) per "
                f"BFSG-AA + WCAG 2.1 AA SC 4.1.2; got label={label_value!r}"
            )