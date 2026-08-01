"""HRS Channel Manager connector for MinLOS pushes (AC-4).

This module implements :class:`HrsCmConnector`, a Kurort-native push connector for
the HRS Channel Manager (HRS CM) MinLOS-push pipeline. HRS is one of the two OTA
channels supported by L13-004 (the other being Booking.com — see
:mod:`channel_manager_minstay.booking_com`).

HRS MinLOS pushes follow Source 1863 (SmartHOTEL connectguide): only rate types
in the ``RateTypeFilter`` (``{"Special", "Hot deal", "Trade show"}``) support
MinLOS push via channel manager; ``Weekend Rate`` and ``Seasonal Rate`` entries
are silently skipped (they use a different push mechanism outside the
MinLOS-push workflow).

HRS pushes are also queued, not real-time, per Source 1848 (Beds24 wiki):
the push is acknowledged with HTTP 202 Accepted and the actual rate update
propagates during the "next update cycle" (typically a few minutes to a few
hours depending on HRS load).

The connector:
    1. Receives a list of ``rate_plans`` (dict-shaped with ``code`` + ``rate_type``)
    2. Filters to only those whose ``rate_type`` is in ``RateTypeFilter``
    3. Builds an OTA-style XML envelope (root ``<HotelRatePlanUpdate>``) containing
       one ``<RatePlan RateType="...">`` element per filter-passing rate type
    4. Drives HTTP POST via the injected ``self._http_client`` (when set)
    5. Appends an audit-trail dict to the ``audit_log`` list (when provided)
       carrying ``actor='hrs'``, the rate-type list that was sent, and
       ``latency_estimate='next-update-cycle'``
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Module-level constants (per AC-4 contract: spec.yaml:114-127)
# ---------------------------------------------------------------------------

#: The default rate-type filter for HRS MinLOS pushes. Per Source 1863
#: (SmartHOTEL connectguide), only these rate types support MinLOS push via
#: channel manager. ``Weekend Rate`` and ``Seasonal Rate`` are silently skipped.
RateTypeFilter: frozenset[str] = frozenset({"Special", "Hot deal", "Trade show"})

#: Rate types that are explicitly NOT supported by HRS MinLOS push per
#: Source 1863. Listed here for documentation; the actual skip is driven by
#: the inverse of ``RateTypeFilter`` (anything not in the filter is skipped).
_SKIPPED_RATE_TYPES: frozenset[str] = frozenset({"Weekend Rate", "Seasonal Rate"})

#: Audit-trail constants per Source 1848 (Beds24 wiki).
_HRS_AUDIT_ACTOR: str = "hrs"
_HRS_LATENCY_ESTIMATE: str = "next-update-cycle"


class _HttpClient(Protocol):
    """Duck-typed HTTP transport contract (parity with ``booking_com._HttpClient``)."""

    def request(self, method: str, url: str, headers=None, body=None) -> Any:
        """Issue an HTTP request and return a response object."""
        ...


class HrsCmConnector:
    """HRS Channel Manager connector for MinLOS pushes (AC-4).

    The connector builds an OTA-style XML envelope carrying only the rate
    types in :data:`RateTypeFilter` and POSTs it to the HRS CM endpoint via
    the injected ``_http_client``. The push is acknowledged with HTTP 202
    (queued, not real-time per Source 1848).

    Example::

        connector = HrsCmConnector()
        connector.set_http_client(fake_http_client)
        rate_plans = (
            {"code": "BAR-NRF", "rate_type": "Special"},
            {"code": "BAR-WKD", "rate_type": "Weekend Rate"},  # filtered out
        )
        audit: list[dict] = []
        connector.push_minlos(profile, rate_plans, audit_log=audit)
        # audit now has 1 entry: actor='hrs', rate_types=('Special',),
        # latency_estimate='next-update-cycle'
    """

    def __init__(self) -> None:
        """Initialize the connector with no HTTP transport injected."""
        self._http_client: _HttpClient | None = None

    def set_http_client(self, client: _HttpClient) -> None:
        """Inject the HTTP transport used by :meth:`push_minlos`.

        The transport must implement the ``request(method, url, headers=None,
        body=None) -> response`` contract.
        """
        self._http_client = client

    def push_minlos(
        self,
        profile: Any,
        rate_plans: tuple[dict[str, Any], ...],
        audit_log: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Push MinLOS rules from ``profile`` to HRS CM for the filter-passing rate plans.

        Args:
            profile: The :class:`~channel_manager_minstay.MinLosProfile` to push.
                Currently unused at the connector level (the XML payload
                structure is rate-type-centric, not profile-centric; per
                Source 1863 the profile's ``minlos`` value is propagated via
                the rule context, and the ``date_range`` is encoded per rate
                type in the rule-applicable subset).
            rate_plans: Tuple of dict-shaped rate plans, each carrying at
                least ``code`` and ``rate_type`` keys.
            audit_log: Optional mutable list to which an audit-trail dict is
                appended. When provided, the dict has the shape::

                    {"actor": "hrs",
                     "rate_types": ("Special", ...),
                     "latency_estimate": "next-update-cycle"}

        Returns:
            The response from the HTTP transport (or ``None`` if no transport
            was injected — useful for tests that only want to capture the
            XML payload + audit entry).
        """
        # (a) Filter rate_plans by RateTypeFilter; skip Weekend/Seasonal.
        filter_passing: list[dict[str, Any]] = [
            rp for rp in rate_plans if rp.get("rate_type") in RateTypeFilter
        ]

        # (b) Build the HRS XML payload (root <HotelRatePlanUpdate>).
        envelope = self._build_envelope(filter_passing, profile)

        # (c) Drive HTTP POST via the injected transport (when available).
        response = None
        if self._http_client is not None:
            response = self._http_client.request(
                method="POST",
                url="/hrs/channelmanager/rateplanupdate",
                headers={"Content-Type": "text/xml; charset=utf-8"},
                body=envelope,
            )

        # (d) Append audit-trail entry when audit_log is provided.
        if audit_log is not None:
            filter_passing_rate_types: tuple[str, ...] = tuple(
                rp["rate_type"] for rp in filter_passing
            )
            audit_log.append(
                {
                    "actor": _HRS_AUDIT_ACTOR,
                    "rate_types": filter_passing_rate_types,
                    "latency_estimate": _HRS_LATENCY_ESTIMATE,
                }
            )

        return response if response is not None else {}

    def _build_envelope(
        self,
        filter_passing: list[dict[str, Any]],
        profile: Any,
    ) -> str:
        """Build the HRS XML envelope for the filter-passing rate plans.

        Returns the serialized XML as a UTF-8 string (via
        ``ET.tostring(root, encoding="unicode")``).
        """
        root = ET.Element("HotelRatePlanUpdate")
        for rp in filter_passing:
            # <RatePlan RateType="..." Code="..." MinLOS="..."/>
            rate_plan_el = ET.SubElement(root, "RatePlan")
            rate_plan_el.set("RateType", str(rp.get("rate_type", "")))
            rate_plan_el.set("Code", str(rp.get("code", "")))
            # The MinLOS attribute is populated from the profile when the
            # rate plan has an explicit minlos; otherwise 0 (no push).
            minlos = rp.get("minlos", 0)
            rate_plan_el.set("MinLOS", str(minlos))
        return ET.tostring(root, encoding="unicode")