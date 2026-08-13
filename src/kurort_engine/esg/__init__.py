"""kurort_engine.esg — Q5.1 ESG-CSRD Voluntary VSME + HCMI Scope 3 (Tier-2).

This package extends ``kurort_engine`` with a voluntary ESG reporting layer
for Hotel Rheinland Bad Orb (33-room Heilbad). Iteration 27 (Developer) —
chosen by Critic verdict (iter-26) from iter-25 Scholar Proposal 002
(Q5.1 ESG-CSRD Voluntary VSME + HCMI Scope 3 Tier-2).

Modules
-------

* :mod:`kurort_engine.esg.report` — VSME Basic Module B3 collector + HCMI
  Scope 3 emissions calculator + Gastgeber-Klimaneutralität 2030 alignment
  surface + Kurort-vertical Heilbad predicate 2036 narrative generator +
  BFSG-EAA compliant ESG disclosure. Implements AC-1..AC-5.

Cross-cutting BFSG-AA + WCAG 2.1 AA compliance is enforced via
``BFSGComplianceError`` (re-used from SHIPPED iter-21 kurkarte_wallet for
AC-5 forward-compat — no new exception class needed).

Public API (re-exported)
------------------------

* :data:`report` — ``kurort_engine.esg.report`` sub-package (5 NEW Q5.1
  public symbols + :class:`BFSGComplianceError`)
* :data:`BFSGComplianceError` — raised on BFSG-AA / WCAG 2.1 AA violation
  (AC-5)

Pre-engagement credentials (NI-1..NI-5)
---------------------------------------

* DATEV-EXTF CSV export — DEFERRED to iter-28+ Tier-3.
* Frau Steuerberaterin Müller DATEV-integrated auditor API — DEFERRED to
  iter-28+ Tier-3 (voluntary ESG does not require Lawyer review).
* Real HCMI live-factor API — DEFERRED; uses published 2025/2026 emission
  factors only.

Pilot scope (single-entity)
---------------------------

1× single entity (Hotel Rheinland Bad Orb) per VSME voluntary Basic Module B3.
No multi-property aggregation (deferred to iter-29+ Heilbad 2036 multi-tenant).
"""
from __future__ import annotations

from kurort_engine.esg import report  # noqa: E402,F401
from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402,F401

__all__ = [
    "BFSGComplianceError",
    "report",
]
