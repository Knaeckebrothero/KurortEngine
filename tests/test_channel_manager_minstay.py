"""AC-1: MinLosProfile YAML loader (DHV Saison calendar).

Test_oracle path recorded in spec.yaml:79 (test_ac1_minlos_profile_loader_returns_5_dhv_saison_rules)
and spec_lock.md:50.

This is the red-phase test that will fail with an AssertionError against the
placeholder (or absent) implementation. The `channel_manager_minstay` package
does not yet exist; `load_minlos_profile` does not yet exist; the YAML profile
fixture does not yet exist. The test asserts the AC-1 contract per spec.yaml:67-79.

AC-1 contract (spec.yaml:67-78):
    Ubiquitous. The `channel_manager_minstay` package shall expose a
    `load_minlos_profile(bundesland: str, kurort: str) -> MinLosProfile`
    function that loads a YAML profile from
    `repo/src/channel_manager_minstay/profiles/<bundesland>_<kurort>_minlos.yaml`
    and returns a `MinLosProfile` whose `rules` tuple contains exactly the
    five canonical DHV Saison entries — `easter`, `whitsun`, `summer`,
    `christmas`, plus one default `shoulder` rule — with each rule carrying
    a `date_range: ("YYYY-MM-DD", "YYYY-MM-DD")` tuple, a `minlos: int`
    nights count, and an `applies_to_ota: bool` flag, parsed via `PyYAML`'s
    `safe_load` (NOT `yaml.load`) so that an untrusted profile cannot
    execute arbitrary Python.

RED VERIFY
----------
This test is expected to FAIL during the red phase. The failure mode must be
``AssertionError`` (a failing assertion on the returned `MinLosProfile`), NOT
``ImportError`` / ``ModuleNotFoundError` / `SyntaxError` / `CollectionError`.

We enforce the failure mode by:
  1. Using ``importlib.util.find_spec`` to pre-check the package exists BEFORE
     attempting the import. If the spec is missing, we raise ``AssertionError``
     with a helpful message (NOT let ``ModuleNotFoundError`` propagate). This
     satisfies RED VERIFY (failure is AssertionError, not ImportError).
  2. Asserting the returned `MinLosProfile` has `.rules` tuple length == 5.
  3. Asserting the rule names are exactly {"easter", "whitsun", "summer",
     "christmas", "shoulder"} (set comparison).

The fixture file `repo/src/channel_manager_minstay/profiles/hessen_bad_orb_minlos.yaml`
will be created in the green phase; this test does NOT pre-create it (that would
short-circuit the red-phase verification).
"""
from __future__ import annotations

import importlib.util
import inspect
import sys


# ---------------------------------------------------------------------------
# AC-1 contract constants (verbatim from spec.yaml:67-78 + spec_lock.md:38-48)
# ---------------------------------------------------------------------------

AC1_EXPECTED_RULE_NAMES: frozenset[str] = frozenset(
    {"easter", "whitsun", "summer", "christmas", "shoulder"}
)
AC1_RULE_COUNT: int = 5  # 4 named peak-weeks + 1 default shoulder


def _load_channel_manager_minstay_or_assert():
    """Import ``channel_manager_minstay`` and return the module.

    Raises ``AssertionError`` (NOT ``ModuleNotFoundError``) when the package
    is absent — this is the AC-1 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("channel_manager_minstay")
    assert spec is not None, (
        "AC-1 contract violated: channel_manager_minstay package not found in "
        "sys.path. The red phase expects this AssertionError (NOT ImportError) "
        "until the green phase implements the package under "
        "repo/src/channel_manager_minstay/__init__.py."
    )
    module = importlib.import_module("channel_manager_minstay")
    return module


def test_ac1_minlos_profile_loader_returns_5_dhv_saison_rules() -> None:
    """AC-1 master contract: load_minlos_profile returns 5 DHV Saison rules.

    Bundles the three sub-contracts into a single assertion surface so that
    ``pytest -k test_ac1_minlos_profile_loader_returns_5_dhv_saison_rules``
    serves as the canonical AC-1 verdict command.

    Sub-contracts:
      (a) `load_minlos_profile(bundesland, kurort)` exists as a callable.
      (b) The returned `MinLosProfile` has a `.rules` tuple attribute with
          length == 5.
      (c) The 5 rule names are exactly {"easter", "whitsun", "summer",
          "christmas", "shoulder"}.
    """
    module = _load_channel_manager_minstay_or_assert()

    # (a) `load_minlos_profile(bundesland, kurort)` is a callable on the package.
    assert hasattr(module, "load_minlos_profile"), (
        "AC-1 contract violated: channel_manager_minstay has no attribute "
        "'load_minlos_profile'. The red phase expects AssertionError (NOT "
        "AttributeError) until the green phase implements the loader."
    )
    loader = module.load_minlos_profile
    assert callable(loader), (
        "AC-1 contract violated: channel_manager_minstay.load_minlos_profile "
        "is not callable"
    )

    # Signature sanity check — 2 positional args (bundesland, kurort).
    sig = inspect.signature(loader)
    params = list(sig.parameters.values())
    positional_params = [
        p for p in params
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    assert len(positional_params) >= 2, (
        "AC-1 contract violated: load_minlos_profile must accept at least 2 "
        f"positional arguments (bundesland, kurort); got {len(positional_params)}"
    )

    # (b, c) Call the loader and inspect the returned MinLosProfile.
    profile = loader("hessen", "bad_orb")
    assert profile is not None, (
        "AC-1 contract violated: load_minlos_profile returned None"
    )
    assert hasattr(profile, "rules"), (
        "AC-1 contract violated: returned profile has no .rules attribute "
        f"(got profile type {type(profile).__name__})"
    )
    rules = profile.rules
    assert isinstance(rules, tuple), (
        "AC-1 contract violated: profile.rules must be a tuple; got "
        f"{type(rules).__name__}"
    )
    assert len(rules) == AC1_RULE_COUNT, (
        f"AC-1 contract violated: profile.rules must have {AC1_RULE_COUNT} "
        f"entries (easter + whitsun + summer + christmas + shoulder); "
        f"got {len(rules)}"
    )

    # Each rule has a `.name` attribute (or is a string itself — accept either).
    rule_names: set[str] = set()
    for rule in rules:
        if isinstance(rule, str):
            rule_names.add(rule)
        else:
            assert hasattr(rule, "name"), (
                f"AC-1 contract violated: rule {rule!r} has no .name attribute"
            )
            rule_names.add(rule.name)

    assert rule_names == set(AC1_EXPECTED_RULE_NAMES), (
        "AC-1 contract violated: rule names must be exactly "
        f"{set(AC1_EXPECTED_RULE_NAMES)}; got {rule_names}"
    )


# ===========================================================================
# AC-2: Booking.com OAuth2 machine-account token exchange
# Test_oracle path recorded in spec.yaml:94 and spec_lock.md:68.
# ===========================================================================

"""AC-2: BookingComConnector OAuth2 token exchange + Authorization header.

AC-2 contract (spec.yaml:81-93):
    Event-driven. When ``BookingComConnector.exchange_token(client_id,
    client_secret)`` is invoked, the connector shall POST to the
    ``/connectivity/token-based-authentication/exchange`` endpoint with
    ``application/x-www-form-urlencoded`` body containing ``client_id`` +
    ``client_secret`` and a ``User-Agent: kurort_engine/<version>`` header,
    shall cache the returned bearer access token for the duration of the
    process, and shall attach ``Authorization: Bearer <token>`` to every
    subsequent Connectivity API call; if the HTTP transport is a stub that
    returns a pre-canned ``{"access_token": "fake-...", "expires_in": 3600}``
    JSON body, the connector shall use the stubbed value verbatim (so the
    test can assert the round-trip without real Booking.com credentials).

RED VERIFY
----------
Same pattern as AC-1: convert ModuleNotFoundError to AssertionError via
``importlib.util.find_spec`` on the not-yet-existing booking_com submodule.
The test uses a ``FakeHttpClient`` that captures the (method, url, headers,
body) of the HTTP call in a ``last_call`` attribute and returns a pre-canned
JSON response. This is dependency-injection of the HTTP transport; it is NOT
mocking-the-unit-under-test (the BookingComConnector's real token-cache +
bearer-header logic is exercised end-to-end).
"""


# ---------------------------------------------------------------------------
# AC-2 contract constants (verbatim from spec.yaml:81-93 + spec_lock.md:53-66)
# ---------------------------------------------------------------------------

AC2_TEST_CLIENT_ID = "test_client_id"
AC2_TEST_CLIENT_SECRET = "test_client_secret"
AC2_FAKE_ACCESS_TOKEN = "fake-token-abc"
AC2_FAKE_EXPIRES_IN = 3600
AC2_TOKEN_EXCHANGE_URL = "/connectivity/token-based-authentication/exchange"
AC2_TEST_HOTEL_ID = "123456"
AC2_TEST_RATE_PLAN_CODE = "BAR-NRF"
AC2_TEST_INV_TYPE_CODE = "STD-SGL"


class _CallRecord:
    """Captures one HTTP call as a flat attribute namespace.

    Used by ``FakeHttpClient`` to record the (method, url, headers, body) of
    the most recent HTTP call so the AC-2 test can assert on them without
    using ``unittest.mock``.
    """

    method: str
    url: str
    headers: dict
    body: object

    def __init__(
        self,
        method: str,
        url: str,
        headers: dict,
        body: object,
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body


class FakeHttpClient:
    """Test double for the HTTP transport dependency of BookingComConnector.

    Records the most recent call in ``self.last_call`` and returns a
    pre-canned JSON response (the Booking.com token-exchange stubbed body).
    Subsequent calls without ``set_response`` return a default OTA-style
    response so a second HTTP call (e.g. ``get_hotel_availnotif``) does not
    raise ``NoResponse``.

    Implements the minimal surface that ``BookingComConnector`` consumes:
    a single ``request(method, url, headers=None, body=None)`` returning a
    dict-like response object with a ``status`` attribute and a ``json()``
    method.
    """

    def __init__(
        self,
        token_access: str = AC2_FAKE_ACCESS_TOKEN,
        token_expires_in: int = AC2_FAKE_EXPIRES_IN,
    ) -> None:
        self.last_call: _CallRecord | None = None
        self.call_log: list[_CallRecord] = []
        self._token_payload = {
            "access_token": token_access,
            "expires_in": token_expires_in,
        }
        self._default_response_payload = {"status": "ok"}

    def _make_response(self, payload: dict) -> "_FakeResponse":
        return _FakeResponse(
            status=200,
            payload=payload,
        )

    def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: object = None,
    ) -> "_FakeResponse":
        """Record the call and return a token-exchange-style response.

        The test asserts on ``self.last_call`` after invoking
        ``BookingComConnector.exchange_token``.
        """
        record = _CallRecord(
            method=method,
            url=url,
            headers=dict(headers) if headers else {},
            body=body,
        )
        self.last_call = record
        self.call_log.append(record)
        # First call is the token exchange; subsequent calls default-respond.
        if len(self.call_log) == 1:
            return self._make_response(self._token_payload)
        return self._make_response(self._default_response_payload)


class _FakeResponse:
    """A dict-like response object with ``status`` attribute + ``json()``."""

    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self._payload = payload

    def json(self) -> dict:
        return dict(self._payload)


def _load_booking_com_or_assert():
    """Import ``channel_manager_minstay.booking_com`` and return the submodule.

    Raises ``AssertionError`` (NOT ``ModuleNotFoundError``) when the submodule
    is absent — this is the AC-2 red-phase RED VERIFY contract. Same pattern
    as ``_load_channel_manager_minstay_or_assert`` but for the booking_com
    submodule specifically.
    """
    spec = importlib.util.find_spec("channel_manager_minstay.booking_com")
    assert spec is not None, (
        "AC-2 contract violated: channel_manager_minstay.booking_com submodule "
        "not found in sys.path. The red phase expects this AssertionError "
        "(NOT ModuleNotFoundError) until the green phase implements the "
        "connector at repo/src/channel_manager_minstay/booking_com.py."
    )
    submodule = importlib.import_module("channel_manager_minstay.booking_com")
    return submodule


def test_ac2_booking_com_oauth2_token_exchange_and_authorization_header() -> None:
    """AC-2 master contract: BookingComConnector OAuth2 token exchange + bearer.

    Bundles the four sub-contracts into a single assertion surface so that
    ``pytest -k test_ac2_booking_com_oauth2_token_exchange_and_authorization_header``
    serves as the canonical AC-2 verdict command.

    Sub-contracts:
      (a) The ``BookingComConnector`` class exists on the
          ``channel_manager_minstay.booking_com`` submodule and exposes
          ``set_http_client(client)`` + ``exchange_token(client_id,
          client_secret)`` methods.
      (b) Calling ``exchange_token(client_id, client_secret)`` invokes the
          HTTP transport exactly once with method=POST, url containing
          AC2_TOKEN_EXCHANGE_URL, a form-encoded body containing
          ``client_id`` + ``client_secret``, and a ``User-Agent`` header
          starting with ``kurort_engine/``.
      (c) The bearer access token returned by the (stubbed) HTTP transport
          is cached on the connector instance (so subsequent calls do NOT
          re-exchange).
      (d) A SECOND call to the connector (``get_hotel_availnotif(...)`` or
          equivalent) carries the ``Authorization: Bearer <token>`` header
          on the HTTP transport request. The test asserts the header is
          present in the second call's recorded headers.
    """
    booking_com = _load_booking_com_or_assert()

    # (a) BookingComConnector class exists on the submodule.
    assert hasattr(booking_com, "BookingComConnector"), (
        "AC-2 contract violated: channel_manager_minstay.booking_com has no "
        "attribute 'BookingComConnector'. The red phase expects "
        "AssertionError (NOT AttributeError) until the green phase implements "
        "the connector class."
    )
    cls = booking_com.BookingComConnector
    assert callable(cls), (
        "AC-2 contract violated: BookingComConnector is not callable (cannot "
        "be instantiated)"
    )

    # set_http_client + exchange_token method existence (signature probes).
    connector = cls()
    assert hasattr(connector, "set_http_client"), (
        "AC-2 contract violated: BookingComConnector has no 'set_http_client' "
        "method; cannot inject a test HTTP transport"
    )
    assert hasattr(connector, "exchange_token"), (
        "AC-2 contract violated: BookingComConnector has no 'exchange_token' "
        "method"
    )
    assert callable(connector.set_http_client), (
        "AC-2 contract violated: BookingComConnector.set_http_client is not callable"
    )
    assert callable(connector.exchange_token), (
        "AC-2 contract violated: BookingComConnector.exchange_token is not callable"
    )

    # (b + c) Inject FakeHttpClient + drive exchange_token; assert on the
    # recorded HTTP call AND that the token is cached.
    fake_client = FakeHttpClient()
    connector.set_http_client(fake_client)

    returned = connector.exchange_token(AC2_TEST_CLIENT_ID, AC2_TEST_CLIENT_SECRET)

    # The connector must return SOMETHING (the access_token or a token-cached
    # object). We don't constrain the return type strictly — but the
    # documented token-exchange JSON has an `access_token` key, so the most
    # permissive interpretation is: returned must NOT be None.
    assert returned is not None, (
        "AC-2 contract violated: BookingComConnector.exchange_token returned None"
    )

    # The HTTP transport must have been called exactly once so far (the
    # token-exchange call). No early re-exchange should happen.
    assert fake_client.last_call is not None, (
        "AC-2 contract violated: FakeHttpClient never recorded a call. "
        "exchange_token did not invoke the HTTP transport at all."
    )
    record = fake_client.last_call
    assert record.method.upper() == "POST", (
        "AC-2 contract violated: token-exchange must use HTTP POST; got "
        f"{record.method!r}"
    )
    assert AC2_TOKEN_EXCHANGE_URL in record.url, (
        "AC-2 contract violated: token-exchange URL must contain "
        f"{AC2_TOKEN_EXCHANGE_URL!r}; got {record.url!r}"
    )

    # Form-encoded body must contain client_id + client_secret. We accept
    # either:
    #   - a dict body (parsed from form-encoded)
    #   - a `str` body containing `client_id=...&client_secret=...`
    # The stub uses a dict for clarity; the green implementation can use
    # `urllib.parse.urlencode(...)` to produce the str form.
    body = record.body
    if isinstance(body, dict):
        body_str = "&".join(f"{k}={v}" for k, v in body.items())
    else:
        body_str = str(body)
    assert AC2_TEST_CLIENT_ID in body_str, (
        "AC-2 contract violated: token-exchange body must contain "
        f"client_id={AC2_TEST_CLIENT_ID!r}; got body={body_str!r}"
    )
    assert AC2_TEST_CLIENT_SECRET in body_str, (
        "AC-2 contract violated: token-exchange body must contain "
        f"client_secret={AC2_TEST_CLIENT_SECRET!r}; got body={body_str!r}"
    )

    # User-Agent header check.
    user_agent = record.headers.get("User-Agent", "")
    assert user_agent.startswith("kurort_engine/"), (
        "AC-2 contract violated: token-exchange User-Agent header must start "
        f"with 'kurort_engine/'; got {user_agent!r}"
    )

    # (c) Token must be cached. We probe by calling exchange_token a SECOND
    # time and asserting the call count increased by AT LEAST 0 (allowing
    # the connector to re-use the cached token) but ALSO that a subsequent
    # Connectivity API call carries the Authorization header.
    #
    # The simplest assertion: the connector exposes the cached token
    # somehow. We accept either an `_access_token` attribute, a `token`
    # property, or the same value is returned from a second exchange_token
    # call.
    #
    # We assert only that the connector RETAINS the token for use in
    # subsequent calls (covered by sub-contract (d) below). The token-cache
    # shape is implementation-defined.

    # (d) A second call to the connector (e.g. a hypothetical
    # get_hotel_availnotif) must carry the Authorization: Bearer header.
    # We probe via the FakeHttpClient: invoke get_hotel_availnotif (if it
    # exists), else fallback to manually constructing a second request via
    # the FakeHttpClient to demonstrate the connector adds the header.
    #
    # We accept EITHER of these shapes:
    #   1. Connector has a `get_hotel_availnotif(...)` method that
    #      internally drives FakeHttpClient.request a SECOND time.
    #   2. Connector has a `_build_authorization_headers()` helper we can
    #      call directly.
    #
    # If neither exists, the implementation has NOT preserved the token-
    # caching contract — surface a clear AssertionError.

    call_count_before = len(fake_client.call_log)

    # Sub-contract (d) probe: try the connector's documented second-call
    # surface. If absent, surface a clear AssertionError so the green phase
    # knows it must implement the second-call API.
    second_call_methods = [
        "_make_authorized_request",  # HTTP-driving surface (Phase 5 green shipped); probes first so the token-cached Authorization header is exercised
        "get_hotel_availnotif",
        "build_availnotif_envelope",  # AC-3 pure-data XML builder; tested separately in test_ac3_…
    ]
    used_method = None
    for name in second_call_methods:
        if hasattr(connector, name):
            used_method = name
            method = getattr(connector, name)
            try:
                # Try calling with sensible defaults; some methods may take
                # kwargs (xml_body, ...), others positional (hotel_id, rate_plan).
                if name == "get_hotel_availnotif":
                    method(AC2_TEST_HOTEL_ID, AC2_TEST_RATE_PLAN_CODE, AC2_TEST_INV_TYPE_CODE)
                elif name == "build_availnotif_envelope":
                    method({"name": "easter", "date_range": ["2026-04-03", "2026-04-12"], "minlos": 5, "applies_to_ota": True},
                           (AC2_TEST_RATE_PLAN_CODE,), (AC2_TEST_INV_TYPE_CODE,))
                elif name == "_make_authorized_request":
                    method("GET", "/some/path")
            except Exception:
                # Implementation may choose to NOT actually drive a network
                # call from `_make_authorized_request`; the test just needs
                # the header construction logic exposed.
                pass
            break

    assert used_method is not None, (
        "AC-2 contract violated: BookingComConnector must expose at least one "
        "second-call surface (e.g. get_hotel_availnotif, "
        "build_availnotif_envelope, or _make_authorized_request) so the "
        "token-cached Authorization header can be exercised."
    )

    # If the connector did drive a second HTTP call via FakeHttpClient,
    # assert the Authorization: Bearer header was attached.
    if len(fake_client.call_log) > call_count_before:
        second_call = fake_client.call_log[-1]
        auth_header = second_call.headers.get("Authorization", "")
        assert auth_header == f"Bearer {AC2_FAKE_ACCESS_TOKEN}", (
            "AC-2 contract violated: the second connector call must carry the "
            "'Authorization: Bearer <token>' header. "
            f"expected='Bearer {AC2_FAKE_ACCESS_TOKEN}', got={auth_header!r}"
        )
    else:
        # Second call did not invoke the transport — token-cache contract is
        # NOT exercised. Surface an AssertionError to make the gap visible
        # to the green phase.
        assert False, (
            "AC-2 contract violated: second-call surface "
            f"{used_method!r} did NOT invoke the HTTP transport, so the "
            "token-cached Authorization header cannot be verified. The green "
            "phase must route the second call through the connector's HTTP "
            "transport so the FakeHttpClient can capture the "
            "Authorization header."
        )


# ===========================================================================
# AC-3: Booking.com OTA_HotelAvailNotif XML envelope structure
# Test_oracle path recorded in spec.yaml:111 and spec_lock.md:86.
# ===========================================================================

"""AC-3: BookingComConnector OTA_HotelAvailNotif XML envelope builder.

AC-3 contract (spec.yaml:96-110):
    Event-driven. When ``BookingComConnector.build_availnotif_envelope(
    minlos_rule, rate_plan_codes: tuple[str, ...], inv_type_codes: tuple[str, ...])``
    is invoked with a single MinLOS rule (e.g. ``minlos=5``,
    ``date_range=("2026-04-03","2026-04-12")``), the connector shall return a
    well-formed ``OTA_HotelAvailNotif`` XML envelope (parseable by
    ``xml.etree.ElementTree.fromstring``) that contains one
    ``<AvailStatusMessages>`` block per RatePlan×InvType, one
    ``<LengthsOfStay>/<LengthOfStay>`` element per rule with child elements
    ``<Time>{minlos}</Time>``, ``<TimeUnit>Day</TimeUnit>``,
    ``<ArrivalDateBased>0</ArrivalDateBased>``,
    ``<MinMaxMessageType>SetMinLOS</MinMaxMessageType>``, and
    ``<RestrictionStatus>Active</RestrictionStatus>``, exactly matching the
    OTA_HotelAvailNotif schema documented at
    ``developers.booking.com/connectivity/docs/ota-hotelavailnotif`` (Source 1862).

RED VERIFY
----------
The ``channel_manager_minstay.booking_com`` submodule EXISTS (Phase 5 shipped
the BookingComConnector class) but the ``build_availnotif_envelope`` METHOD
does NOT exist yet (it is what Phase 7 green will implement). The test must
fail with ``AssertionError`` (NOT ``AttributeError`` per RED VERIFY protocol);
the helper ``_assert_has_build_availnotif_envelope`` converts the missing-method
condition into an AssertionError so the failure is observable + honest.
"""


# ---------------------------------------------------------------------------
# AC-3 contract constants (verbatim from spec.yaml:96-110 + spec_lock.md:71-85)
# ---------------------------------------------------------------------------

AC3_EASTER_DATE_START = "2026-04-03"
AC3_EASTER_DATE_END = "2026-04-12"
AC3_EASTER_MINLOS = 5
AC3_TEST_RATE_PLAN_CODES: tuple[str, ...] = ("BAR-NRF",)
AC3_TEST_INV_TYPE_CODES: tuple[str, ...] = ("STD-SGL",)
AC3_EXPECTED_ENVELOPE_ROOT = "OTA_HotelAvailNotif"
AC3_EXPECTED_AVAIL_STATUS_MESSAGES = "AvailStatusMessages"
AC3_EXPECTED_AVAIL_STATUS_MESSAGE = "AvailStatusMessage"
AC3_EXPECTED_STATUS_APPLICATION_CONTROL = "StatusApplicationControl"
AC3_EXPECTED_LENGTHS_OF_STAY = "LengthsOfStay"
AC3_EXPECTED_LENGTH_OF_STAY = "LengthOfStay"
AC3_EXPECTED_TIME_TAG = "Time"
AC3_EXPECTED_TIME_UNIT_TAG = "TimeUnit"
AC3_EXPECTED_TIME_UNIT_VALUE = "Day"
AC3_EXPECTED_ARRIVAL_DATE_BASED_TAG = "ArrivalDateBased"
AC3_EXPECTED_ARRIVAL_DATE_BASED_VALUE = "0"
AC3_EXPECTED_MINMAX_MESSAGE_TYPE_TAG = "MinMaxMessageType"
AC3_EXPECTED_MINMAX_MESSAGE_TYPE_VALUE = "SetMinLOS"
AC3_EXPECTED_RESTRICTION_STATUS_TAG = "RestrictionStatus"
AC3_EXPECTED_RESTRICTION_STATUS_VALUE = "Active"


def _assert_has_build_availnotif_envelope(connector) -> None:
    """Assert the BookingComConnector exposes ``build_availnotif_envelope``.

    The connector class is implemented (Phase 5) but the
    ``build_availnotif_envelope`` method is NOT — Phase 7 green will add it.
    This helper converts the would-be ``AttributeError`` into a clear
    ``AssertionError`` so RED VERIFY surfaces an assertion failure (NOT an
    attribute failure) when the method is missing.
    """
    assert hasattr(connector, "build_availnotif_envelope"), (
        "AC-3 contract violated: BookingComConnector has no "
        "'build_availnotif_envelope' method. The red phase expects "
        "AssertionError (NOT AttributeError) until the green phase adds the "
        "method to repo/src/channel_manager_minstay/booking_com.py."
    )


def test_ac3_booking_com_availnotif_xml_envelope_structure() -> None:
    """AC-3 master contract: build_availnotif_envelope returns valid XML.

    Bundles 5 sub-contracts into a single assertion surface so that
    ``pytest -k test_ac3_booking_com_availnotif_xml_envelope_structure``
    serves as the canonical AC-3 verdict command.

    Sub-contracts:
      (a) ``BookingComConnector.build_availnotif_envelope(rule, rate_plans,
          inv_types)`` exists as a callable method.
      (b) The returned string is parseable by
          ``xml.etree.ElementTree.fromstring(...)`` (well-formed XML).
      (c) The root tag is ``<OTA_HotelAvailNotif>``.
      (d) Exactly one ``<AvailStatusMessages>`` child containing one
          ``<AvailStatusMessage>`` grandchild (per RatePlan×InvType).
      (e) The ``<StatusApplicationControl>`` element matches
          ``RatePlanCode="BAR-NRF" InvTypeCode="STD-SGL"``.
      (f) The ``<LengthsOfStay>/<LengthOfStay>`` element has children
          ``<Time>5</Time>``, ``<TimeUnit>Day</TimeUnit>``,
          ``<ArrivalDateBased>0</ArrivalDateBased>``,
          ``<MinMaxMessageType>SetMinLOS</MinMaxMessageType>``, and
          ``<RestrictionStatus>Active</RestrictionStatus>`` — matching the
          OTA_HotelAvailNotif schema documented at
          ``developers.booking.com/connectivity/docs/ota-hotelavailnotif``
          (Source 1862).
    """
    # (Pre-condition) BookingComConnector exists; the booking_com submodule
    # was implemented in Phase 5 green.
    booking_com = _load_booking_com_or_assert()
    assert hasattr(booking_com, "BookingComConnector"), (
        "AC-3 pre-condition violated: BookingComConnector missing from "
        "channel_manager_minstay.booking_com. Phase 5 regression."
    )
    connector = booking_com.BookingComConnector()

    # (a) build_availnotif_envelope method existence — must convert any
    # AttributeError into AssertionError (RED VERIFY protocol).
    _assert_has_build_availnotif_envelope(connector)
    builder = connector.build_availnotif_envelope
    assert callable(builder), (
        "AC-3 contract violated: BookingComConnector.build_availnotif_envelope "
        "is not callable"
    )

    # Construct a sample MinLosRule for the test. Use the public re-export
    # `channel_manager_minstay.MinLosRule` (parity with how external callers
    # would use the API).
    cm_package = _load_channel_manager_minstay_or_assert()
    MinLosRule = cm_package.MinLosRule
    rule = MinLosRule(
        name="easter",
        date_range=(AC3_EASTER_DATE_START, AC3_EASTER_DATE_END),
        minlos=AC3_EASTER_MINLOS,
        applies_to_ota=True,
    )

    # Drive the builder. The returned object must be a non-empty string
    # containing the OTA_HotelAvailNotif XML envelope.
    envelope = builder(
        rule,
        AC3_TEST_RATE_PLAN_CODES,
        AC3_TEST_INV_TYPE_CODES,
    )
    assert envelope is not None, (
        "AC-3 contract violated: build_availnotif_envelope returned None"
    )
    assert isinstance(envelope, str), (
        "AC-3 contract violated: build_availnotif_envelope must return a "
        f"str; got {type(envelope).__name__}"
    )
    assert len(envelope) > 0, (
        "AC-3 contract violated: build_availnotif_envelope returned empty string"
    )

    # (b) Parse the envelope via stdlib xml.etree.ElementTree. This is the
    # canonical "well-formed XML" assertion — fromstring raises
    # xml.etree.ElementTree.ParseError if the XML is malformed.
    import xml.etree.ElementTree as ET
    root = ET.fromstring(envelope)

    # (c) Root tag is <OTA_HotelAvailNotif>.
    assert root.tag == AC3_EXPECTED_ENVELOPE_ROOT, (
        "AC-3 contract violated: envelope root tag must be "
        f"{AC3_EXPECTED_ENVELOPE_ROOT!r}; got {root.tag!r}"
    )

    # (d) Exactly one <AvailStatusMessages> child with one <AvailStatusMessage>
    # grandchild.
    avail_status_messages = list(root.findall(AC3_EXPECTED_AVAIL_STATUS_MESSAGES))
    assert len(avail_status_messages) == 1, (
        "AC-3 contract violated: envelope must contain exactly one "
        f"<{AC3_EXPECTED_AVAIL_STATUS_MESSAGES}> child (per "
        f"RatePlan×InvType); got {len(avail_status_messages)}"
    )
    asm = avail_status_messages[0]
    avail_status_message_grandchildren = list(
        asm.findall(AC3_EXPECTED_AVAIL_STATUS_MESSAGE)
    )
    assert len(avail_status_message_grandchildren) == 1, (
        "AC-3 contract violated: <AvailStatusMessages> must contain exactly "
        f"one <{AC3_EXPECTED_AVAIL_STATUS_MESSAGE}> grandchild; "
        f"got {len(avail_status_message_grandchildren)}"
    )
    message_el = avail_status_message_grandchildren[0]

    # (e) <StatusApplicationControl RatePlanCode="BAR-NRF" InvTypeCode="STD-SGL" />
    sac_elements = list(
        message_el.findall(AC3_EXPECTED_STATUS_APPLICATION_CONTROL)
    )
    assert len(sac_elements) == 1, (
        "AC-3 contract violated: <AvailStatusMessage> must contain exactly "
        f"one <{AC3_EXPECTED_STATUS_APPLICATION_CONTROL}> element; "
        f"got {len(sac_elements)}"
    )
    sac = sac_elements[0]
    assert sac.get("RatePlanCode") == AC3_TEST_RATE_PLAN_CODES[0], (
        "AC-3 contract violated: <StatusApplicationControl RatePlanCode=> "
        f"must be {AC3_TEST_RATE_PLAN_CODES[0]!r}; got {sac.get('RatePlanCode')!r}"
    )
    assert sac.get("InvTypeCode") == AC3_TEST_INV_TYPE_CODES[0], (
        "AC-3 contract violated: <StatusApplicationControl InvTypeCode=> "
        f"must be {AC3_TEST_INV_TYPE_CODES[0]!r}; got {sac.get('InvTypeCode')!r}"
    )

    # (f) <LengthsOfStay>/<LengthOfStay> with the 5 documented children.
    los_containers = list(message_el.findall(AC3_EXPECTED_LENGTHS_OF_STAY))
    assert len(los_containers) == 1, (
        "AC-3 contract violated: <AvailStatusMessage> must contain exactly "
        f"one <{AC3_EXPECTED_LENGTHS_OF_STAY}> element; "
        f"got {len(los_containers)}"
    )
    los_elements = list(
        los_containers[0].findall(AC3_EXPECTED_LENGTH_OF_STAY)
    )
    assert len(los_elements) == 1, (
        "AC-3 contract violated: <LengthsOfStay> must contain exactly one "
        f"<{AC3_EXPECTED_LENGTH_OF_STAY}> element; got {len(los_elements)}"
    )
    los = los_elements[0]

    # <Time>5</Time> — the MinLOS value (5 nights for Easter).
    time_el = los.find(AC3_EXPECTED_TIME_TAG)
    assert time_el is not None, (
        "AC-3 contract violated: <LengthOfStay> must contain a "
        f"<{AC3_EXPECTED_TIME_TAG}> child; got None"
    )
    assert time_el.text == str(AC3_EASTER_MINLOS), (
        "AC-3 contract violated: <Time> text must equal the MinLOS value "
        f"({AC3_EASTER_MINLOS}); got {time_el.text!r}"
    )

    # <TimeUnit>Day</TimeUnit>
    time_unit_el = los.find(AC3_EXPECTED_TIME_UNIT_TAG)
    assert time_unit_el is not None, (
        "AC-3 contract violated: <LengthOfStay> must contain a "
        f"<{AC3_EXPECTED_TIME_UNIT_TAG}> child; got None"
    )
    assert time_unit_el.text == AC3_EXPECTED_TIME_UNIT_VALUE, (
        "AC-3 contract violated: <TimeUnit> text must be "
        f"{AC3_EXPECTED_TIME_UNIT_VALUE!r}; got {time_unit_el.text!r}"
    )

    # <ArrivalDateBased>0</ArrivalDateBased> (0 = stay-through restriction)
    arr_date_el = los.find(AC3_EXPECTED_ARRIVAL_DATE_BASED_TAG)
    assert arr_date_el is not None, (
        "AC-3 contract violated: <LengthOfStay> must contain a "
        f"<{AC3_EXPECTED_ARRIVAL_DATE_BASED_TAG}> child; got None"
    )
    assert arr_date_el.text == AC3_EXPECTED_ARRIVAL_DATE_BASED_VALUE, (
        "AC-3 contract violated: <ArrivalDateBased> text must be "
        f"{AC3_EXPECTED_ARRIVAL_DATE_BASED_VALUE!r} (stay-through); got "
        f"{arr_date_el.text!r}"
    )

    # <MinMaxMessageType>SetMinLOS</MinMaxMessageType>
    minmax_el = los.find(AC3_EXPECTED_MINMAX_MESSAGE_TYPE_TAG)
    assert minmax_el is not None, (
        "AC-3 contract violated: <LengthOfStay> must contain a "
        f"<{AC3_EXPECTED_MINMAX_MESSAGE_TYPE_TAG}> child; got None"
    )
    assert minmax_el.text == AC3_EXPECTED_MINMAX_MESSAGE_TYPE_VALUE, (
        "AC-3 contract violated: <MinMaxMessageType> text must be "
        f"{AC3_EXPECTED_MINMAX_MESSAGE_TYPE_VALUE!r}; got {minmax_el.text!r}"
    )

    # <RestrictionStatus>Active</RestrictionStatus>
    restriction_el = los.find(AC3_EXPECTED_RESTRICTION_STATUS_TAG)
    assert restriction_el is not None, (
        "AC-3 contract violated: <LengthOfStay> must contain a "
        f"<{AC3_EXPECTED_RESTRICTION_STATUS_TAG}> child; got None"
    )
    assert restriction_el.text == AC3_EXPECTED_RESTRICTION_STATUS_VALUE, (
        "AC-3 contract violated: <RestrictionStatus> text must be "
        f"{AC3_EXPECTED_RESTRICTION_STATUS_VALUE!r}; got "
        f"{restriction_el.text!r}"
    )

# ===========================================================================
# AC-4: HRS Channel Manager RateType filter + audit-trail latency marker
# Test_oracle path recorded in spec.yaml:127 and spec_lock.md:103.
# ===========================================================================

"""AC-4: HrsCmConnector filters rate types and records audit-trail latency.

AC-4 contract (spec.yaml:114-127):
    State-driven. While ``HrsCmConnector.push_minlos(profile, rate_plans)`` is
    invoked with a ``MinLosProfile``, the connector shall emit OTA-style XML
    pushes ONLY for rate types in the ``RateTypeFilter`` (default =
    ``frozenset({"Special", "Hot deal", "Trade show"})``), shall silently skip
    Weekend Rate and Seasonal Rate entries per Source 1863 (SmartHOTEL
    connectguide) which documents that those rate types do NOT support
    MinLOS push via channel manager; the connector shall additionally
    attach an audit-trail record carrying ``actor="hrs"``, the rate-type
    list that was sent, and a ``latency_estimate="next-update-cycle"`` marker
    per Source 1848 (Beds24 wiki) which documents that HRS MinLOS pushes
    are queued, not real-time.

RED VERIFY
----------
The ``channel_manager_minstay.hrs`` submodule does NOT yet exist (Phase 9
green will implement it). The ``HrsCmConnector`` class is not importable.
The test must fail with ``AssertionError`` (NOT ``ImportError`` /
``ModuleNotFoundError``) at the helper gate.
"""

import dataclasses
import importlib.util
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# AC-4 contract constants (verbatim from spec.yaml:114-127 + spec_lock.md:89-103)
# ---------------------------------------------------------------------------

AC4_DEFAULT_RATE_TYPE_FILTER: frozenset[str] = frozenset(
    {"Special", "Hot deal", "Trade show"}
)
AC4_SKIPPED_RATE_TYPES: frozenset[str] = frozenset({"Weekend Rate", "Seasonal Rate"})
AC4_EXPECTED_ACTOR: str = "hrs"
AC4_EXPECTED_LATENCY_ESTIMATE: str = "next-update-cycle"


def _load_hrs_or_assert():
    """Import ``channel_manager_minstay.hrs`` and return the module.

    Raises ``AssertionError`` (NOT ``ModuleNotFoundError``) when the
    submodule is absent — this is the AC-4 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("channel_manager_minstay.hrs")
    assert spec is not None, (
        "AC-4 contract violated: channel_manager_minstay.hrs submodule not "
        "found in sys.path. The red phase expects this AssertionError (NOT "
        "ImportError) until the green phase implements the HRS connector "
        "under repo/src/channel_manager_minstay/hrs.py."
    )
    module = importlib.import_module("channel_manager_minstay.hrs")
    return module


@dataclasses.dataclass
class _FakeHrsRequest:
    method: str
    url: str
    headers: dict
    body: str


class _FakeHrsHttpClient:
    """Recording HTTP transport for the HRS connector (parity with FakeHttpClient)."""

    def __init__(self) -> None:
        self.call_log: list[_FakeHrsRequest] = []

    def request(self, method: str, url: str, headers=None, body=None) -> "_FakeHrsResponse":
        # Coerce body to string so XML assertions can parse it.
        if body is None:
            body_str = ""
        elif isinstance(body, bytes):
            body_str = body.decode("utf-8", errors="replace")
        else:
            body_str = str(body)
        self.call_log.append(
            _FakeHrsRequest(
                method=method,
                url=url,
                headers=dict(headers or {}),
                body=body_str,
            )
        )
        # HRS is queued, not real-time — return a 202 Accepted with no body
        return _FakeHrsResponse(status=202, body="")


@dataclasses.dataclass
class _FakeHrsResponse:
    status: int
    body: str


def test_ac4_hrs_cm_connector_filters_rate_types_and_records_audit_latency() -> None:
    """AC-4 master contract: HrsCmConnector.push_minlos filters rate types + records audit.

    Sub-contracts:
      (a) ``HrsCmConnector`` class is importable from
          ``channel_manager_minstay.hrs``.
      (b) ``HrsCmConnector.push_minlos(profile, rate_plans)`` exists and is
          callable.
      (c) Only rate types in ``AC4_DEFAULT_RATE_TYPE_FILTER`` are emitted in
          the XML payload; ``AC4_SKIPPED_RATE_TYPES`` (Weekend, Seasonal) are
          silently dropped.
      (d) An audit-trail record is attached carrying
          ``actor="hrs"``, the rate-type list that was sent, and
          ``latency_estimate="next-update-cycle"``.
    """
    hrs_module = _load_hrs_or_assert()

    # (a) HrsCmConnector class exists.
    assert hasattr(hrs_module, "HrsCmConnector"), (
        "AC-4 contract violated: channel_manager_minstay.hrs has no attribute "
        "'HrsCmConnector'. The red phase expects AssertionError (NOT "
        "AttributeError) until the green phase implements the class."
    )
    connector = hrs_module.HrsCmConnector()
    fake_client = _FakeHrsHttpClient()
    connector.set_http_client(fake_client)

    # (b) Build a MinLosProfile (reuse the shipped AC-1 profile loader).
    from channel_manager_minstay import load_minlos_profile
    profile = load_minlos_profile("hessen", "bad_orb")

    # (c) Call push_minlos with 4 rate plans: 3 in the filter + 1 skipped.
    rate_plans = (
        {"code": "BAR-NRF", "rate_type": "Special"},
        {"code": "BAR-HOT", "rate_type": "Hot deal"},
        {"code": "BAR-TRD", "rate_type": "Trade show"},
        {"code": "BAR-WKD", "rate_type": "Weekend Rate"},
    )
    audit_entries: list[dict] = []
    result = connector.push_minlos(profile, rate_plans, audit_log=audit_entries)

    # The HRS push should have driven 1 HTTP call (HRS batches all
    # filter-passing rate types into a single payload).
    assert len(fake_client.call_log) >= 1, (
        "AC-4 contract violated: HrsCmConnector.push_minlos did not invoke "
        "the HTTP transport; got 0 calls in call_log"
    )
    sent_body = fake_client.call_log[0].body
    assert sent_body, (
        "AC-4 contract violated: HRS push body is empty; expected a non-empty "
        "OTA-style XML payload"
    )

    # Parse the sent XML.
    parsed = ET.fromstring(sent_body)

    # Find all <RatePlan> (or <Rate>) children that carry a RateType attribute.
    # HRS uses <RatePlan RateType="..."> per Source 1863.
    rate_type_tags = [
        el for el in parsed.iter() if "RateType" in el.attrib
    ]
    sent_rate_types = {el.attrib["RateType"] for el in rate_type_tags}

    # Only the 3 filter-passing rate types should be present.
    assert sent_rate_types == AC4_DEFAULT_RATE_TYPE_FILTER, (
        "AC-4 contract violated: HRS push must include ONLY the 3 default-"
        f"filter rate types {AC4_DEFAULT_RATE_TYPE_FILTER}; got {sent_rate_types}. "
        f"Weekend/Seasonal rate types MUST be silently dropped per Source 1863."
    )

    # (d) Audit-trail entry recorded with the correct actor + rate-type list +
    # latency_estimate.
    assert len(audit_entries) >= 1, (
        "AC-4 contract violated: HrsCmConnector.push_minlos did not record an "
        "audit-trail entry; expected at least 1 entry with actor='hrs'"
    )
    hrs_audit = [
        e for e in audit_entries
        if e.get("actor") == AC4_EXPECTED_ACTOR
    ]
    assert len(hrs_audit) >= 1, (
        f"AC-4 contract violated: no audit entry with actor="
        f"{AC4_EXPECTED_ACTOR!r}; got actors={[e.get('actor') for e in audit_entries]!r}"
    )
    entry = hrs_audit[0]
    assert entry.get("latency_estimate") == AC4_EXPECTED_LATENCY_ESTIMATE, (
        "AC-4 contract violated: HRS audit entry must carry "
        f"latency_estimate={AC4_EXPECTED_LATENCY_ESTIMATE!r} per Source 1848; "
        f"got {entry.get('latency_estimate')!r}"
    )
    audit_rate_types = set(entry.get("rate_types", ()))
    assert audit_rate_types == AC4_DEFAULT_RATE_TYPE_FILTER, (
        "AC-4 contract violated: HRS audit entry's rate_types list must match "
        f"the filter {AC4_DEFAULT_RATE_TYPE_FILTER}; got {audit_rate_types}"
    )


# ===========================================================================
# AC-5: MinLosValidator flags reservations below proposed MinLOS
# Test_oracle path recorded in spec.yaml:142 and spec_lock.md:118.
# ===========================================================================

"""AC-5: MinLosValidator flags reservations with length_of_stay < rule.minlos.

AC-5 contract (spec.yaml:129-142):
    Event-driven. When ``MinLosValidator.validate(profile, existing_reservations)``
    is invoked with a ``MinLosProfile`` and a list of ``kurort_engine.Reservation``
    objects, the validator shall return a ``MinLosValidationReport`` whose
    ``violations`` tuple lists one entry per (reservation, rule) pair where the
    reservation's ``length_of_stay = (departure - arrival).days`` is LESS
    than the matching profile rule's ``minlos`` for any date that overlaps
    the rule's ``date_range``, and whose ``conflicts`` tuple is empty when no
    reservations violate; the validator shall compute ``length_of_stay``
    using the same ``(departure - arrival).days`` formula that
    ``kurort_engine.calculator`` uses for Kurtaxe day-count, ensuring
    consistency between the validator and the existing rate engine.

RED VERIFY
----------
The ``channel_manager_minstay.validator`` submodule does NOT yet exist
(Phase 9 green will implement it). The ``MinLosValidator`` and
``MinLosValidationReport`` classes are not importable. The test must fail
with ``AssertionError`` (NOT ``ImportError`` / ``ModuleNotFoundError``)
at the helper gate.
"""

import dataclasses
import datetime as _dt
import importlib.util

from kurort_engine.calculator import Guest, Reservation


# ---------------------------------------------------------------------------
# AC-5 contract constants (verbatim from spec.yaml:129-142 + spec_lock.md:105-118)
# ---------------------------------------------------------------------------

AC5_TEST_PROFILE_RULE_NAME: str = "easter"
AC5_TEST_PROFILE_DATE_RANGE: tuple[str, str] = ("2026-04-03", "2026-04-12")
AC5_TEST_PROFILE_MINLOS: int = 5
AC5_EXPECTED_VIOLATION_COUNT: int = 1  # only the 3-night reservation violates


def _load_validator_or_assert():
    """Import ``channel_manager_minstay.validator`` and return the module.

    Raises ``AssertionError`` (NOT ``ModuleNotFoundError``) when the
    submodule is absent — this is the AC-5 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("channel_manager_minstay.validator")
    assert spec is not None, (
        "AC-5 contract violated: channel_manager_minstay.validator submodule "
        "not found in sys.path. The red phase expects this AssertionError "
        "(NOT ImportError) until the green phase implements the validator "
        "under repo/src/channel_manager_minstay/validator.py."
    )
    module = importlib.import_module("channel_manager_minstay.validator")
    return module


def test_ac5_minlos_validator_flags_reservations_below_proposed_minlos() -> None:
    """AC-5 master contract: MinLosValidator flags below-minlos reservations.

    Sub-contracts:
      (a) ``MinLosValidator`` class is importable from
          ``channel_manager_minstay.validator``.
      (b) ``MinLosValidator.validate(profile, existing_reservations)`` exists
          and is callable.
      (c) The returned ``MinLosValidationReport`` carries a ``violations``
          tuple listing one entry per (reservation, rule) pair where
          ``length_of_stay < rule.minlos``.
      (d) The ``length_of_stay`` formula matches
          ``(departure - arrival).days`` (parity with kurort_engine.calculator).
      (e) When no reservations conflict, the ``conflicts`` tuple is empty.
    """
    validator_module = _load_validator_or_assert()

    # (a) MinLosValidator class exists.
    assert hasattr(validator_module, "MinLosValidator"), (
        "AC-5 contract violated: channel_manager_minstay.validator has no "
        "attribute 'MinLosValidator'. The red phase expects AssertionError "
        "(NOT AttributeError) until the green phase implements the class."
    )

    # (b) Build a MinLosProfile with one rule (5 nights, Easter 2026).
    from channel_manager_minstay import MinLosRule, MinLosProfile
    rule = MinLosRule(
        name=AC5_TEST_PROFILE_RULE_NAME,
        date_range=AC5_TEST_PROFILE_DATE_RANGE,
        minlos=AC5_TEST_PROFILE_MINLOS,
        applies_to_ota=True,
    )
    profile = MinLosProfile(
        bundesland="hessen",
        kurort="bad_orb",
        rules=(rule,),
    )

    # (c, d, e) Build 3 reservation fixtures:
    #   r_violate: arrives 2026-04-05, departs 2026-04-08 → 3 nights → < 5 = VIOLATES
    #   r_boundary: arrives 2026-04-05, departs 2026-04-10 → 5 nights = boundary (PASSES)
    #   r_pass: arrives 2026-04-05, departs 2026-04-12 → 7 nights > 5 (PASSES)
    arrival = _dt.date(2026, 4, 5)
    r_violate = Reservation(
        reservation_id="RES-001-VIOLATE",
        arrival=arrival,
        departure=_dt.date(2026, 4, 8),  # 3 nights
        guests=(Guest(name="Guest A", birth_date=_dt.date(1990, 1, 1), nationality="DE"),),
    )
    r_boundary = Reservation(
        reservation_id="RES-002-BOUNDARY",
        arrival=arrival,
        departure=_dt.date(2026, 4, 10),  # 5 nights = boundary
        guests=(Guest(name="Guest B", birth_date=_dt.date(1990, 1, 1), nationality="DE"),),
    )
    r_pass = Reservation(
        reservation_id="RES-003-PASS",
        arrival=arrival,
        departure=_dt.date(2026, 4, 12),  # 7 nights
        guests=(Guest(name="Guest C", birth_date=_dt.date(1990, 1, 1), nationality="DE"),),
    )

    # Sanity: the length_of_stay formula matches kurort_engine.calculator's
    # day_count rule (spec.yaml:131-141 mandates parity).
    assert (r_violate.departure - r_violate.arrival).days == 3
    assert (r_boundary.departure - r_boundary.arrival).days == 5
    assert (r_pass.departure - r_pass.arrival).days == 7

    validator = validator_module.MinLosValidator()
    report = validator.validate(profile, [r_violate, r_boundary, r_pass])

    # Report must be a MinLosValidationReport (namedtuple, dataclass, or
    # duck-typed object with .violations and .conflicts).
    assert report is not None, (
        "AC-5 contract violated: MinLosValidator.validate returned None"
    )
    assert hasattr(report, "violations"), (
        f"AC-5 contract violated: report {type(report).__name__} has no "
        f".violations attribute"
    )
    assert hasattr(report, "conflicts"), (
        f"AC-5 contract violated: report {type(report).__name__} has no "
        f".conflicts attribute"
    )

    violations = report.violations
    conflicts = report.conflicts
    assert isinstance(violations, tuple), (
        f"AC-5 contract violated: report.violations must be a tuple; "
        f"got {type(violations).__name__}"
    )
    assert isinstance(conflicts, tuple), (
        f"AC-5 contract violated: report.conflicts must be a tuple; "
        f"got {type(conflicts).__name__}"
    )

    # (c) Only r_violate (3 nights < 5) violates; r_boundary (5 == 5) and
    # r_pass (7 > 5) pass.
    assert len(violations) == AC5_EXPECTED_VIOLATION_COUNT, (
        f"AC-5 contract violated: expected {AC5_EXPECTED_VIOLATION_COUNT} "
        f"violation (r_violate with 3 nights < minlos=5); got {len(violations)}"
    )

    # The single violation should reference r_violate.
    v = violations[0]
    # Accept either a (reservation, rule) tuple OR a dataclass/namedtuple
    # with a .reservation attribute.
    if isinstance(v, tuple):
        offending_reservation = v[0]
    else:
        assert hasattr(v, "reservation"), (
            f"AC-5 contract violated: violation entry {v!r} has neither tuple "
            f"shape nor .reservation attribute"
        )
        offending_reservation = v.reservation

    assert offending_reservation.reservation_id == r_violate.reservation_id, (
        "AC-5 contract violated: the only violation must reference "
        f"r_violate (id={r_violate.reservation_id!r}); got "
        f"reservation_id={offending_reservation.reservation_id!r}"
    )

    # (e) No conflicts (no reservations violate in conflicting ways).
    assert len(conflicts) == 0, (
        f"AC-5 contract violated: report.conflicts must be empty when no "
        f"conflicts exist; got {len(conflicts)} conflict(s): {conflicts!r}"
    )


# ===========================================================================
# AC-6: MinLosScheduler dry-run emits XML without any network IO
# Test_oracle path recorded in spec.yaml:157 and spec_lock.md:133.
# ===========================================================================

"""AC-6: MinLosScheduler.push(dry_run=True) runs the full pipeline without network IO.

AC-6 contract (spec.yaml:144-157):
    Event-driven. When ``MinLosScheduler.push(profile, dry_run=True)`` is
    invoked with ``dry_run=True``, the scheduler shall execute the full
    MinLOS-push pipeline (load profile → build Booking.com envelope → build
    HRS envelope → filter rate types → record audit entries) WITHOUT
    performing any network IO (the connector HTTP transport is replaced by
    a ``DryRunTransport`` that captures payloads in memory), shall return a
    ``DryRunResult`` carrying the captured Booking.com XML envelope, the
    captured HRS XML envelope, and a summary of the audit-log entries that
    WOULD have been written, and shall NOT call ``urllib.request.urlopen``
    or any other network primitive (verified via a ``DryRunTransport``
    sentinel that raises if any network call is attempted).

RED VERIFY
----------
The ``channel_manager_minstay.scheduler`` submodule does NOT yet exist
(Phase 9 green will implement it). The ``MinLosScheduler`` and
``DryRunResult`` classes are not importable. The test must fail with
``AssertionError`` (NOT ``ImportError`` / ``ModuleNotFoundError``) at the
helper gate.
"""

import importlib.util
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# AC-6 contract constants (verbatim from spec.yaml:144-157 + spec_lock.md:120-133)
# ---------------------------------------------------------------------------

AC6_EXPECTED_NO_NETWORK_CALLS: int = 0


def _load_scheduler_or_assert():
    """Import ``channel_manager_minstay.scheduler`` and return the module.

    Raises ``AssertionError`` (NOT ``ModuleNotFoundError``) when the
    submodule is absent — this is the AC-6 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("channel_manager_minstay.scheduler")
    assert spec is not None, (
        "AC-6 contract violated: channel_manager_minstay.scheduler submodule "
        "not found in sys.path. The red phase expects this AssertionError "
        "(NOT ImportError) until the green phase implements the scheduler "
        "under repo/src/channel_manager_minstay/scheduler.py."
    )
    module = importlib.import_module("channel_manager_minstay.scheduler")
    return module


def test_ac6_minlos_scheduler_dry_run_emits_xml_without_network_io() -> None:
    """AC-6 master contract: MinLosScheduler.push(dry_run=True) emits XML + zero network IO.

    Sub-contracts:
      (a) ``MinLosScheduler`` class is importable from
          ``channel_manager_minstay.scheduler``.
      (b) ``MinLosScheduler.push(profile, dry_run=True)`` exists and is callable.
      (c) The returned ``DryRunResult`` carries ``.booking_com_xml`` (a
          well-formed ``<OTA_HotelAvailNotif>`` envelope parseable by
          ``ET.fromstring``), ``.hrs_xml`` (the HRS XML envelope), and
          ``.audit_summary`` (the audit entries that WOULD have been written).
      (d) No network IO is performed: ``urllib.request.urlopen`` is NOT
          called (verified via a ``DryRunTransport`` sentinel that raises if
          any network primitive is invoked).
    """
    scheduler_module = _load_scheduler_or_assert()

    # (a) MinLosScheduler class exists.
    assert hasattr(scheduler_module, "MinLosScheduler"), (
        "AC-6 contract violated: channel_manager_minstay.scheduler has no "
        "attribute 'MinLosScheduler'. The red phase expects AssertionError "
        "(NOT AttributeError) until the green phase implements the class."
    )
    # DryRunResult must exist (the return type of push(dry_run=True)).
    assert hasattr(scheduler_module, "DryRunResult"), (
        "AC-6 contract violated: channel_manager_minstay.scheduler has no "
        "attribute 'DryRunResult'. The red phase expects AssertionError "
        "(NOT AttributeError) until the green phase implements the class."
    )

    # (d) Network-IO sentinel: install a urllib.request.urlopen wrapper that
    # raises if called. We use a flag list so the test can assert "no calls".
    _network_call_attempts: list[bool] = []

    import urllib.request as _urllib

    _original_urlopen = _urllib.urlopen

    def _exploding_urlopen(*args, **kwargs):
        _network_call_attempts.append(True)
        raise AssertionError(
            "AC-6 contract violated: MinLosScheduler.push(dry_run=True) "
            "must NOT call urllib.request.urlopen (or any other network "
            "primitive); got args={args!r}, kwargs={kwargs!r}"
        )

    _urllib.urlopen = _exploding_urlopen
    try:
        # (b) Build a full MinLosProfile (reuse the shipped AC-1 fixture).
        from channel_manager_minstay import load_minlos_profile
        profile = load_minlos_profile("hessen", "bad_orb")

        # Build rate_plans + inv_types for the scheduler.
        rate_plans = (
            {"code": "BAR-NRF", "rate_type": "Special"},
            {"code": "BAR-HOT", "rate_type": "Hot deal"},
        )
        inv_types = ("STD-SGL", "STD-DBL")

        scheduler = scheduler_module.MinLosScheduler()
        result = scheduler.push(
            profile,
            rate_plans=rate_plans,
            inv_types=inv_types,
            dry_run=True,
        )

        # (c) Result is a DryRunResult carrying booking_com_xml + hrs_xml + audit_summary.
        assert result is not None, (
            "AC-6 contract violated: MinLosScheduler.push(dry_run=True) "
            "returned None"
        )
        for attr in ("booking_com_xml", "hrs_xml", "audit_summary"):
            assert hasattr(result, attr), (
                f"AC-6 contract violated: DryRunResult has no .{attr} attribute"
            )

        # booking_com_xml must be a well-formed <OTA_HotelAvailNotif> envelope.
        bc_xml = result.booking_com_xml
        assert isinstance(bc_xml, str) and bc_xml, (
            "AC-6 contract violated: DryRunResult.booking_com_xml must be a "
            f"non-empty string; got {type(bc_xml).__name__}"
        )
        bc_parsed = ET.fromstring(bc_xml)
        assert bc_parsed.tag == "OTA_HotelAvailNotif", (
            "AC-6 contract violated: booking_com_xml root must be "
            f"<OTA_HotelAvailNotif>; got <{bc_parsed.tag}>"
        )

        # hrs_xml must be a non-empty XML envelope (HRS-specific schema).
        hrs_xml = result.hrs_xml
        assert isinstance(hrs_xml, str) and hrs_xml, (
            "AC-6 contract violated: DryRunResult.hrs_xml must be a non-empty "
            f"string; got {type(hrs_xml).__name__}"
        )
        hrs_parsed = ET.fromstring(hrs_xml)
        # HRS root element is conventionally <HotelRatePlanUpdate> or
        # <OTA_HotelRatePlanNotif> — accept either; the contract is "non-empty,
        # parseable XML".
        assert hrs_parsed is not None

        # audit_summary must be a list/tuple of audit entries (the ones that
        # WOULD have been written).
        audit_summary = result.audit_summary
        assert isinstance(audit_summary, (list, tuple)), (
            "AC-6 contract violated: DryRunResult.audit_summary must be a "
            f"list or tuple; got {type(audit_summary).__name__}"
        )
        assert len(audit_summary) >= 1, (
            "AC-6 contract violated: DryRunResult.audit_summary must list at "
            "least the 2 audit entries (booking_com + hrs) that WOULD have "
            f"been written; got {len(audit_summary)}"
        )

        # (d) Final assertion: NO network calls happened during the dry-run.
        assert len(_network_call_attempts) == AC6_EXPECTED_NO_NETWORK_CALLS, (
            "AC-6 contract violated: MinLosScheduler.push(dry_run=True) "
            "triggered network IO; expected 0 calls to urllib.request.urlopen "
            f"(or any other network primitive); got {len(_network_call_attempts)} "
            f"attempt(s)"
        )
    finally:
        # Restore the original urlopen to avoid polluting other tests.
        _urllib.urlopen = _original_urlopen


# ===========================================================================
# AC-7: CLI push --dry-run exit 0 emits Booking.com OTA_HotelAvailNotif XML
# Test_oracle path recorded in spec.yaml:175 and spec_lock.md:148.
# ===========================================================================

"""AC-7: python -m channel_manager_minstay push --dry-run exits 0 + emits XML.

AC-7 contract (spec.yaml:159-175):
    Event-driven. When ``python -m channel_manager_minstay push --profile
    hessen_bad_orb --dry-run`` is invoked from the repository root (with
    ``PYTHONPATH=src`` set so the package is importable), the CLI entry point
    shall exit 0 silently (no stdout/stderr from the library code), shall
    write the captured Booking.com OTA_HotelAvailNotif XML envelope to
    stdout (one XML document per RatePlan×InvType combination), and shall
    exit 1 with a structured error message on ``--execute`` mode if no
    Booking.com machine-account credentials are configured (so the user
    never accidentally pushes to a live OTA in CI).

RED VERIFY
----------
The ``channel_manager_minstay.__main__`` module does NOT yet exist
(Phase 9 green will create it). Running ``python -m channel_manager_minstay
push --dry-run`` will exit with a non-zero status (the missing __main__
triggers ModuleNotFoundError). The test must fail with ``AssertionError``
on the returncode assertion (NOT propagate the ModuleNotFoundError).
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET


def test_ac7_cli_push_dry_run_exit_zero_emits_booking_com_xml_envelope() -> None:
    """AC-7 master contract: CLI push --dry-run exits 0 + emits Booking.com XML.

    Sub-contracts:
      (a) ``python -m channel_manager_minstay push --profile hessen_bad_orb
          --dry-run`` exits with returncode == 0.
      (b) stdout contains a well-formed ``<OTA_HotelAvailNotif>`` envelope
          parseable by ``xml.etree.ElementTree.fromstring``.
      (c) stderr is empty from the library code (no warnings, no prints).
    """
    # Run the CLI in a subprocess so we don't pollute the current process's
    # pytest state (and so we exercise the real ``python -m`` invocation
    # path, not an in-process import).
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(repo_root, "src")
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable,
        "-m",
        "channel_manager_minstay",
        "push",
        "--profile",
        "hessen_bad_orb",
        "--dry-run",
    ]
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    # (a) Returncode is 0 (clean exit).
    if result.returncode != 0:
        # Surface the stderr so the failure is diagnosable; the test asserts
        # at the gate below.
        raise AssertionError(
            "AC-7 contract violated: 'python -m channel_manager_minstay push "
            f"--profile hessen_bad_orb --dry-run' exited with non-zero status "
            f"{result.returncode}. Expected returncode == 0. "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}. "
            "The red phase expects this AssertionError (NOT the raw "
            "ModuleNotFoundError) until the green phase implements "
            "repo/src/channel_manager_minstay/__main__.py."
        )

    # (b) stdout contains a well-formed <OTA_HotelAvailNotif> envelope.
    stdout = result.stdout
    assert stdout, (
        "AC-7 contract violated: 'python -m channel_manager_minstay push "
        "--profile hessen_bad_orb --dry-run' produced empty stdout; expected "
        "at least one <OTA_HotelAvailNotif> XML envelope"
    )

    # The envelope might be embedded in additional text (e.g. multiple
    # XML docs for different rate plans); parse the first <OTA_HotelAvailNotif>
    # we find.
    envelope_start = stdout.find("<OTA_HotelAvailNotif")
    assert envelope_start >= 0, (
        "AC-7 contract violated: stdout does not contain an "
        f"<OTA_HotelAvailNotif> element; got stdout={stdout!r}"
    )
    # Parse from the envelope start through the matching close tag.
    envelope_xml = stdout[envelope_start:]
    parsed = ET.fromstring(envelope_xml)
    assert parsed.tag == "OTA_HotelAvailNotif", (
        "AC-7 contract violated: parsed envelope root is "
        f"<{parsed.tag}>; expected <OTA_HotelAvailNotif>"
    )

    # (c) stderr is empty from the library code. (Subprocess stderr may
    # include deprecation warnings from third-party packages; the contract
    # is "no stderr from library code". Allow empty stderr only.)
    stderr = result.stderr
    assert stderr == "", (
        "AC-7 contract violated: 'python -m channel_manager_minstay push "
        "--profile hessen_bad_orb --dry-run' produced non-empty stderr; "
        f"expected empty stderr from library code. got stderr={stderr!r}"
    )
