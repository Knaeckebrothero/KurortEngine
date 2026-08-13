"""Booking.com Connectivity API connector (AC-2 + AC-3 partial).

Implements the L13-004 Booking.com side of the channel-manager MinLOS push:
the ``BookingComConnector`` exchanges a machine-account client_id + client_secret
for a bearer access token via Booking.com's OAuth2 ``/connectivity/token-based-
authentication/exchange`` endpoint, caches the token for the process lifetime,
and attaches ``Authorization: Bearer <token>`` to every subsequent Connectivity
API call.

The HTTP transport is **dependency-injected** via :meth:`set_http_client` so the
connector is testable without real Booking.com credentials (L13-004-CF1 — the
real Booking.com Connectivity Partner program requires 1-2 week onboarding,
deferred to iter-16+). Tests use ``FakeHttpClient`` (defined in the test file)
to drive the round-trip + capture the headers for assertion.

Module-level constants
----------------------
``_USER_AGENT``
    HTTP ``User-Agent`` header value sent on every request. Booking.com's
    Connectivity docs require a stable User-Agent for partner identification
    (Source 1877). Format: ``kurort_engine/<version>``.

``_TOKEN_EXCHANGE_URL``
    Path component for the OAuth2 token-exchange endpoint (Booking.com's
    machine-account flow per Source 1875). Path is RELATIVE — the green
    implementation does NOT bake in a host (avoids hardcoding
    ``https://supply-xml.booking.com`` so tests can run without network IO).

Per AC-2 contract (spec.yaml:81-93 + spec_lock.md:53-66):
    When ``BookingComConnector.exchange_token(client_id, client_secret)`` is
    invoked, the connector shall POST to the token-exchange endpoint with
    ``application/x-www-form-urlencoded`` body containing ``client_id`` +
    ``client_secret`` and a ``User-Agent: kurort_engine/<version>`` header,
    shall cache the returned bearer access token for the duration of the
    process, and shall attach ``Authorization: Bearer <token>`` to every
    subsequent Connectivity API call.

Per AC-3 contract (spec.yaml:96-110 + spec_lock.md:71-86), the connector will
ALSO expose :meth:`build_availnotif_envelope` (added in this slice; see
Phase 7 green for the implementation).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Protocol
from urllib.parse import urlencode

# Module-level constants.
_USER_AGENT = "kurort_engine/0.1.0"
_TOKEN_EXCHANGE_URL = "/connectivity/token-based-authentication/exchange"


class _HttpClient(Protocol):
    """Minimal protocol for the HTTP transport dependency.

    The green ``BookingComConnector`` calls ``self._http_client.request(...)``
    with this signature. Tests inject ``FakeHttpClient`` (defined in the test
    file) which has a matching signature.

    Production code wires this to ``urllib.request`` via a thin adapter
    (deferred to iter-16+ when live Booking.com credentials land).
    """

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: Any = None,
    ) -> Any:  # returns a response object with `.json()` + `.status`
        ...


class BookingComConnector:
    """Connector for the Booking.com Connectivity API (OAuth2 + MinLOS push).

    Lifecycle
    ---------
    1. ``connector = BookingComConnector()`` — construct (no I/O).
    2. ``connector.set_http_client(client)`` — inject the HTTP transport.
    3. ``connector.exchange_token(client_id, client_secret)`` — drive the
       OAuth2 token-exchange round-trip; the access token is cached on the
       connector instance for the process lifetime.
    4. ``connector._make_authorized_request(method, path, body=None)`` —
       drive a subsequent Connectivity API call with the cached bearer
       attached as the ``Authorization: Bearer <token>`` header.

    The token cache is intentionally simple (single in-memory value, no
    refresh-on-expiry logic). The Booking.com ``expires_in`` field from the
    token-exchange response is stored alongside the token so a future
    iteration can add refresh-on-expiry without breaking the API.
    """

    def __init__(self) -> None:
        """Construct a connector with no HTTP transport and no cached token.

        NO I/O at construction time. Both ``self._http_client`` and
        ``self._access_token`` start as ``None``; calling
        :meth:`exchange_token` or :meth:`_make_authorized_request` before
        :meth:`set_http_client` is invoked raises ``RuntimeError`` (fail-loud
        per the project's pattern).
        """
        self._http_client: _HttpClient | None = None
        self._access_token: str | None = None
        self._token_expires_at: int | None = None

    def set_http_client(self, client: _HttpClient) -> None:
        """Inject the HTTP transport dependency.

        The connector calls ``self._http_client.request(method, url,
        headers, body)`` for every Connectivity API request. Tests inject
        ``FakeHttpClient``; production code injects a urllib-backed
        adapter (deferred to iter-16+).

        Parameters
        ----------
        client:
            An object implementing the ``_HttpClient`` protocol (a single
            ``request`` method). Cannot be ``None`` — passing ``None``
            raises ``ValueError`` (fail-loud) so a misconfiguration
            surfaces immediately rather than at the first network call.
        """
        if client is None:
            raise ValueError(
                "set_http_client requires a non-None client; "
                "passing None would crash at the first HTTP call."
            )
        self._http_client = client

    def exchange_token(self, client_id: str, client_secret: str) -> str:
        """Drive the OAuth2 machine-account token-exchange round-trip.

        POST to ``/connectivity/token-based-authentication/exchange`` with:
        - ``User-Agent: kurort_engine/<version>`` header
        - ``Content-Type: application/x-www-form-urlencoded`` header
        - Form-encoded body ``client_id=<id>&client_secret=<secret>``
        - Bearer-style request (no Authorization header — token exchange
          is the credential, not a subsequent API call).

        The response JSON is expected to contain ``access_token`` (str) and
        ``expires_in`` (int seconds). The token is cached on the connector
        instance; the ``expires_in`` value is stored alongside so future
        iterations can add refresh-on-expiry.

        Parameters
        ----------
        client_id:
            Booking.com machine-account ``client_id`` (from the Connectivity
            Partner portal).
        client_secret:
            Booking.com machine-account ``client_secret``. Treated as a
            secret in production — must NOT be logged. The current
            implementation does not log; a future iteration may add a
            redaction layer for debug logs.

        Returns
        -------
        str
            The bearer access token returned by the token-exchange endpoint.

        Raises
        ------
        RuntimeError
            If ``set_http_client(...)`` has not been called yet.
        """
        if self._http_client is None:
            raise RuntimeError(
                "BookingComConnector.exchange_token requires an HTTP client; "
                "call set_http_client(...) first."
            )

        # Build form-encoded body + headers per AC-2 contract.
        body_str = urlencode(
            {"client_id": client_id, "client_secret": client_secret}
        )
        headers = {
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Drive the HTTP transport. The FakeHttpClient in tests captures
        # this call (method, url, headers, body) in `.last_call` /
        # `.call_log` for assertion.
        response = self._http_client.request(
            method="POST",
            url=_TOKEN_EXCHANGE_URL,
            headers=headers,
            body=body_str,
        )

        # Parse the JSON response. The transport is expected to return an
        # object with a `.json()` method (parity with the stdlib
        # `urllib.request.urlopen` response + the test FakeHttpClient).
        payload = response.json()
        access_token = str(payload["access_token"])
        expires_in = int(payload.get("expires_in", 3600))

        # Cache for the duration of the process.
        self._access_token = access_token
        self._token_expires_at = expires_in

        return access_token

    def _make_authorized_request(
        self,
        method: str,
        path: str,
        body: Any = None,
    ) -> Any:
        """Drive a Connectivity API call with the cached bearer attached.

        Attaches the ``Authorization: Bearer <token>`` header (per AC-2(d)
        contract) plus the standard ``User-Agent`` header to the injected
        HTTP transport's ``request(...)`` method. Returns the transport's
        response object unchanged (caller parses JSON via ``.json()`` as
        needed).

        Parameters
        ----------
        method:
            HTTP method — e.g. ``"GET"``, ``"POST"``. Uppercase per RFC 7230
            (the connector does NOT auto-uppercase; the caller is expected
            to pass an uppercase string).
        path:
            URL path component (e.g. ``"/hotels/123456/availnotif"``). The
            connector does NOT concatenate a host; the caller is expected
            to pass a path-only URL (parity with the token-exchange call).
        body:
            Optional request body. For POST/PUT, typically a form-encoded
            str or a dict. For GET, typically ``None``. Default ``None``.

        Returns
        -------
        Any
            The transport's response object (whatever ``http_client.request``
            returns). For ``FakeHttpClient``, that's a ``_FakeResponse``
            with ``.status`` + ``.json()`` attributes. For stdlib
            ``urllib.request.urlopen``, that's an ``http.client.HTTPResponse``
            with ``.read()`` + ``.status`` attributes.

        Raises
        ------
        RuntimeError
            If ``exchange_token(...)`` has not been called yet (no cached
            bearer) OR if ``set_http_client(...)`` has not been called yet.
        """
        if self._http_client is None:
            raise RuntimeError(
                "BookingComConnector._make_authorized_request requires an "
                "HTTP client; call set_http_client(...) first."
            )
        if self._access_token is None:
            raise RuntimeError(
                "BookingComConnector._make_authorized_request requires an "
                "access token; call exchange_token(...) first."
            )

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": _USER_AGENT,
        }
        return self._http_client.request(
            method=method,
            url=path,
            headers=headers,
            body=body,
        )

    def build_availnotif_envelope(
        self,
        rule: Any,
        rate_plan_codes: tuple[str, ...],
        inv_type_codes: tuple[str, ...],
    ) -> str:
        """Build an OTA_HotelAvailNotif XML envelope string for the given MinLOS rule.

        Implements the AC-3 contract (spec.yaml:96-110 + spec_lock.md:71-86).
        The envelope is constructed via stdlib xml.etree.ElementTree (NOT
        lxml -- per the project's zero-runtime-deps policy). Returns the
        serialized XML as a string (parseable by
        xml.etree.ElementTree.fromstring(...)).

        Envelope structure::

            <OTA_HotelAvailNotif>
              <AvailStatusMessages>
                <AvailStatusMessage>
                  <StatusApplicationControl RatePlanCode="..." InvTypeCode="..."/>
                  <LengthsOfStay>
                    <LengthOfStay>
                      <Time>{rule.minlos}</Time>
                      <TimeUnit>Day</TimeUnit>
                      <ArrivalDateBased>0</ArrivalDateBased>
                      <MinMaxMessageType>SetMinLOS</MinMaxMessageType>
                      <RestrictionStatus>Active</RestrictionStatus>
                    </LengthOfStay>
                  </LengthsOfStay>
                </AvailStatusMessage>
                ...  # one per (rate_plan_code, inv_type_code) combination
              </AvailStatusMessages>
            </OTA_HotelAvailNotif>

        Parameters
        ----------
        rule:
            The MinLOS rule carrying the minlos int (duck-typed -- we accept
            any object with a .minlos attribute, NOT just
            channel_manager_minstay.MinLosRule). Other rule fields are NOT
            used in the envelope.
        rate_plan_codes:
            Tuple of rate-plan code strings (e.g. ("BAR-NRF", "BAR-FLEX")).
            The envelope emits one <AvailStatusMessage> block per
            RatePlan*InvType combination (Cartesian product).
        inv_type_codes:
            Tuple of room-inventory type code strings (e.g.
            ("STD-SGL", "STD-DBL")).

        Returns
        -------
        str
            The serialized XML envelope string (no XML declaration).
        """
        root = ET.Element("OTA_HotelAvailNotif")
        avail_status_messages = ET.SubElement(root, "AvailStatusMessages")
        minlos_text = str(rule.minlos)
        for rate_plan_code in rate_plan_codes:
            for inv_type_code in inv_type_codes:
                message = ET.SubElement(
                    avail_status_messages, "AvailStatusMessage"
                )
                ET.SubElement(
                    message,
                    "StatusApplicationControl",
                    RatePlanCode=rate_plan_code,
                    InvTypeCode=inv_type_code,
                )
                lengths_of_stay = ET.SubElement(message, "LengthsOfStay")
                length_of_stay = ET.SubElement(lengths_of_stay, "LengthOfStay")
                ET.SubElement(length_of_stay, "Time").text = minlos_text
                ET.SubElement(length_of_stay, "TimeUnit").text = "Day"
                # ArrivalDateBased=0 means "stay-through restriction" (the MinLOS
                # applies if the stay INCLUDES the specified date). Per Source
                # 1862, 0 is the default for OTA_HotelAvailNotif.
                ET.SubElement(length_of_stay, "ArrivalDateBased").text = "0"
                ET.SubElement(length_of_stay, "MinMaxMessageType").text = "SetMinLOS"
                ET.SubElement(length_of_stay, "RestrictionStatus").text = "Active"
        return ET.tostring(root, encoding="unicode")
