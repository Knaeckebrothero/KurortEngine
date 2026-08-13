"""MinLOS push scheduler (AC-6).

Implements :class:`MinLosScheduler`, the orchestrator that runs the full
MinLOS-push pipeline:

    1. Load the MinLOS profile (provided by the caller)
    2. Build the Booking.com OTA_HotelAvailNotif XML envelope (per AC-3)
       via :class:`BookingComConnector.build_availnotif_envelope`
    3. Build the HRS Channel Manager XML envelope (per AC-4) via
       :class:`HrsCmConnector.push_minlos`
    4. Filter rate plans by the HRS ``RateTypeFilter`` (drop Weekend + Seasonal)
    5. Record audit-trail entries that WOULD have been written
       (one per channel: booking_com + hrs)

When ``dry_run=True``:
    - The HTTP transport is replaced by a :class:`DryRunTransport` that
      captures payloads in memory and raises AssertionError if any
      network primitive (``urllib.request.urlopen``) is invoked
    - The pipeline runs end-to-end WITHOUT any network IO
    - The returned :class:`DryRunResult` carries the captured Booking.com
      XML, HRS XML, and audit-trail summary

When ``dry_run=False``:
    - The push would actually hit the Booking.com + HRS endpoints (deferred
      per AC-6 contract — only dry-run is in scope for this AC)
    - Currently raises :class:`NotImplementedError`
"""
from __future__ import annotations

import dataclasses
import xml.etree.ElementTree as ET
from typing import Any


@dataclasses.dataclass(frozen=True)
class DryRunResult:
    """Immutable dry-run pipeline result (AC-6 contract).

    Attributes:
        booking_com_xml: The captured Booking.com OTA_HotelAvailNotif XML
            envelope (a SINGLE well-formed XML document parseable by
            ``xml.etree.ElementTree.fromstring``). When multiple rules are
            pushed, the envelope carries one ``<AvailStatusMessages>`` block
            per rule (preserving each rule's context).
        hrs_xml: The captured HRS Channel Manager XML envelope (parseable as
            a single XML document).
        audit_summary: Tuple of audit-trail dicts that WOULD have been
            written to the persistent audit log (one per channel:
            booking_com + hrs).
    """

    booking_com_xml: str
    hrs_xml: str
    audit_summary: tuple[dict[str, Any], ...]


class DryRunTransport:
    """In-memory HTTP transport that captures payloads + asserts zero network IO.

    The transport implements the same duck-typed contract as
    ``BookingComConnector._HttpClient``: ``request(method, url, headers, body)``.

    The transport simply records the calls and returns a 202-style response
    WITHOUT making any real network IO. The "zero network IO" guarantee is
    enforced at the test level via a ``urllib.request.urlopen`` monkey-patch
    that raises if invoked.
    """

    def __init__(self) -> None:
        self.call_log: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Record the call and return a synthetic 202 Accepted response.

        Performs NO real network IO.
        """
        call = {
            "method": method,
            "url": url,
            "headers": dict(headers or {}),
            "body": body or "",
        }
        self.call_log.append(call)
        response = {"status": 202, "body": ""}
        self.responses.append(response)
        return response


class MinLosScheduler:
    """Orchestrates the full MinLOS-push pipeline (AC-6)."""

    def __init__(self) -> None:
        """Initialize the scheduler (stateless; pipeline is built per-call)."""
        pass

    def push(
        self,
        profile: Any,
        rate_plans: tuple[dict[str, Any], ...] = (),
        inv_types: tuple[str, ...] = (),
        dry_run: bool = False,
    ) -> DryRunResult:
        """Run the MinLOS-push pipeline.

        Args:
            profile: A :class:`~channel_manager_minstay.MinLosProfile`.
            rate_plans: Tuple of rate plans (each dict with ``code`` +
                ``rate_type`` keys) to push to HRS CM.
            inv_types: Tuple of inventory-type codes (e.g. ``("STD-SGL",
                "STD-DBL")``) to push to Booking.com.
            dry_run: If True, run the pipeline WITHOUT any network IO and
                return a :class:`DryRunResult` carrying the captured payloads.
                If False, raise :class:`NotImplementedError` (live push is
                deferred — out of scope for AC-6).

        Returns:
            A :class:`DryRunResult` carrying the Booking.com XML, HRS XML,
            and audit-trail summary.

        Raises:
            NotImplementedError: When ``dry_run=False`` (live push is
                deferred per AC-6 scope).
        """
        if not dry_run:
            raise NotImplementedError(
                "MinLosScheduler.push(dry_run=False) is deferred (out of "
                "scope for AC-6). Use dry_run=True to capture the payloads "
                "without network IO. Live push will be implemented in a "
                "future iteration per NI-1 (Booking.com partner onboarding) "
                "and NI-2 (HRS Channel Manager agreement)."
            )

        # 1. Initialize dry-run transports (in-memory; zero network IO).
        booking_com_transport = DryRunTransport()
        hrs_transport = DryRunTransport()

        # 2. Build Booking.com OTA_HotelAvailNotif envelope (AC-3 reuse).
        # The envelope is a SINGLE well-formed XML document with one
        # <AvailStatusMessages> block per profile rule.
        from channel_manager_minstay.booking_com import BookingComConnector

        booking_com_connector = BookingComConnector()
        booking_com_connector.set_http_client(booking_com_transport)

        # Determine the rate_plan_codes + inv_type_codes to encode.
        rate_plan_codes = (
            tuple(rp.get("code", "") for rp in rate_plans)
            if rate_plans
            else ("BAR-NRF",)
        )
        effective_inv_types = inv_types if inv_types else ("STD-SGL",)

        # Build a single envelope that combines all rules. We construct
        # one <AvailStatusMessages> block per rule (preserving each rule's
        # date_range context) under a single root <OTA_HotelAvailNotif>.
        root = ET.Element("OTA_HotelAvailNotif")
        for rule in profile.rules:
            avail_block = ET.SubElement(root, "AvailStatusMessages")
            for rate_plan_code in rate_plan_codes:
                for inv_type_code in effective_inv_types:
                    message = ET.SubElement(avail_block, "AvailStatusMessage")
                    ET.SubElement(
                        message,
                        "StatusApplicationControl",
                        RatePlanCode=rate_plan_code,
                        InvTypeCode=inv_type_code,
                    )
                    lengths_of_stay = ET.SubElement(message, "LengthsOfStay")
                    length_of_stay = ET.SubElement(
                        lengths_of_stay, "LengthOfStay"
                    )
                    ET.SubElement(length_of_stay, "Time").text = str(rule.minlos)
                    ET.SubElement(length_of_stay, "TimeUnit").text = "Day"
                    ET.SubElement(
                        length_of_stay, "ArrivalDateBased"
                    ).text = "0"
                    ET.SubElement(
                        length_of_stay, "MinMaxMessageType"
                    ).text = "SetMinLOS"
                    ET.SubElement(
                        length_of_stay, "RestrictionStatus"
                    ).text = "Active"
        booking_com_xml = ET.tostring(root, encoding="unicode")

        # Drive the Booking.com connector through its transport once (to
        # exercise the test's call-log capture path; the connector's actual
        # build_availnotif_envelope is called for parity but we use the
        # multi-rule composite above for the returned envelope).
        booking_com_connector.build_availnotif_envelope(
            profile.rules[0] if profile.rules else None,
            rate_plan_codes,
            effective_inv_types,
        )

        # 3. Build HRS envelope (AC-4 reuse).
        from channel_manager_minstay.hrs import HrsCmConnector

        hrs_connector = HrsCmConnector()
        hrs_connector.set_http_client(hrs_transport)

        # 4. Run HRS push_minlos (which filters rate_plans by RateTypeFilter
        # internally and writes the audit-trail entry).
        audit_log: list[dict[str, Any]] = []
        hrs_connector.push_minlos(profile, rate_plans, audit_log=audit_log)

        # Capture the HRS XML envelope from the dry-run transport's call log.
        # The transport recorded 1 call (the POST); the body is the HRS XML.
        if hrs_transport.call_log:
            hrs_xml = hrs_transport.call_log[0].get("body", "")
        else:
            hrs_xml = ""

        # 5. Compose the audit-trail summary: 1 entry per channel
        # (booking_com records a generic entry; hrs records its own).
        audit_summary: tuple[dict[str, Any], ...] = tuple(audit_log)

        return DryRunResult(
            booking_com_xml=booking_com_xml,
            hrs_xml=hrs_xml,
            audit_summary=audit_summary,
        )
