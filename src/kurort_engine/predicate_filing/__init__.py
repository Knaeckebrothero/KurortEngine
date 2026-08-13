"""kurort_engine.predicate_filing — H1 Heilbad 2036 Reprädikatisierung
predicate-renewal filing packet generator (Tier-2 Pattern F chain-extension).

Iter-33 (Developer) — H1-NARROW Tier-2 sub-package chosen by iter-31 Scholar
pick-first (H1-NARROW scope; 9/9 Pattern D clean per
`iter-31-idea-index-synthesis-3-pool-3-fresh-candidates-h1-heilbad-2036-h4-kiosk-`
§6). Chosen in lieu of an iter-32 Critic verdict (the Critic role was skipped
in this loop iteration; the orchestrator inserted Developer directly per the
3-source convergence pattern).

Pattern F chain-extension of 6 SHIPPED modules (anti-drift discipline):

  iter-21 `kurort_engine.kurkarte_wallet.BFSGComplianceError` (re-used by AC-4)
  iter-18 `kurort_engine.kurpaket_orchestrator.SGBV23CertificateMissing`
    (re-used by AC-2)
  iter-30 `kurort_engine.esg.report.calculate_scope_1_2` (chain-extended by AC-3)
  iter-30 `kurort_engine.esg.report.generate_heilbad_2036_esg_narrative`
    (chain-extended by AC-3)
  iter-3 `kurort_engine.spa_wellness.SpaManager` + `ToskanaThermeAdapter`
    (sourced by AC-1 spa_section)
  iter-24 `kurort_engine.ev_charging.reservation_match`
    (sourced by AC-1 mobility_section)

Public API
----------

* :func:`assemble_predicate_packet` — assemble the Bad Orb Heilbad 2036
  Reprädikatisierung predicate-renewal filing packet (AC-1, Ubiquitous)
* :func:`validate_kurgaste_health_data` — DSGVO Art. 9 + §23 SGB V Badekur
  validation gate (AC-2, Event-driven)
* :func:`generate_heilbad_2036_narrative` — DE/EN Kurort-vertical narrative
  builder with 6 canonical anchors (AC-3, Event-driven)
* :func:`export_predicate_filing_bfsg_aa` — BFSG-AA compliant predicate
  filing disclosure export with non-affirmation footer (AC-4, Unwanted-behavior)
* :func:`aggregate_kurgaste_health_data` — Kurgäste §23 SGB V + DSGVO Art. 9
  aggregation (AC-5, Ubiquitous)
* :class:`DSGVOArt9ValidationError` — raised when a Kurgäste record lacks
  explicit DSGVO Art. 9 consent (defined in this package)

Iter-36 (Developer) — H1-NARROW-Satzung-2026 chain-extension of iter-33
SHIPPED `kurort_engine.predicate_filing`. Adds 4 NEW symbols (preserved
verbatim per anti-drift discipline):

* :func:`extract_2026_satzung_schema` — extract 2026 Satzung schema (AC-1)
* :func:`load_2026_profile` — load hessen_bad_orb_2026.yaml profile (AC-2)
* :func:`apply_2026_attestation_template` — apply 2026 attestation template (AC-3)
* :func:`compute_anti_drift_sha` — SHA-256 anti-drift integrity check (AC-4)

Iteration 33 (Developer). Iteration 36 (Developer chain-extension).
Confidence: HIGH.
"""
from __future__ import annotations

from kurort_engine.predicate_filing.heilbad_2036_narrative_generator import (  # noqa: E402,F401
    generate_heilbad_2036_narrative,
)

# Public API — re-exports of the 5 predicate_filing functions + the
# DSGVOArt9ValidationError exception class. Imports below are deferred
# to avoid circular imports between the 4 sub-modules at package load time.
from kurort_engine.predicate_filing.kurgaste_health_data_aggregator import (  # noqa: E402,F401
    DSGVOArt9ValidationError,
    aggregate_kurgaste_health_data,
    validate_kurgaste_health_data,
)
from kurort_engine.predicate_filing.predicate_filing_export import (  # noqa: E402,F401
    export_predicate_filing_bfsg_aa,
)
from kurort_engine.predicate_filing.predicate_packet_assembler import (  # noqa: E402,F401
    assemble_predicate_packet,
)

# Iter-36 NEW: re-export the 4 H1-NARROW-Satzung-2026 symbols.
# Module names begin with a digit (e.g., `2026_validate`), so we MUST use
# `__import__()` instead of direct `from ... import` (per iter-36 Phase 2
# RED lesson FA1). The 2026_validate module is loaded into a local name
# `_v26_mod`, and the 2026_attestation module is loaded into `_a26_mod`.
# The 4 NEW symbols are then explicitly bound to module-level names so
# `from kurort_engine.predicate_filing import extract_2026_satzung_schema`
# succeeds (per spec.yaml done_when[3] "from ... import ... OK").
_v26_mod = __import__(  # noqa: E402,F401
    "kurort_engine.predicate_filing.2026_validate",
    fromlist=["_dummy_"],
)
extract_2026_satzung_schema = _v26_mod.extract_2026_satzung_schema  # noqa: E402,F401
load_2026_profile = _v26_mod.load_2026_profile  # noqa: E402,F401
_a26_mod = __import__(  # noqa: E402,F401
    "kurort_engine.predicate_filing.2026_attestation",
    fromlist=["_dummy_"],
)
apply_2026_attestation_template = _a26_mod.apply_2026_attestation_template  # noqa: E402,F401
compute_anti_drift_sha = _a26_mod.compute_anti_drift_sha  # noqa: E402,F401

__all__ = [
    # AC-1 — predicate packet assembly
    "assemble_predicate_packet",
    # AC-2 — Kurgäste health-data validation (DSGVO Art. 9 + §23 SGB V)
    "validate_kurgaste_health_data",
    # AC-3 — Heilbad 2036 narrative generator (DE/EN)
    "generate_heilbad_2036_narrative",
    # AC-4 — BFSG-AA compliant predicate filing disclosure export
    "export_predicate_filing_bfsg_aa",
    # AC-5 — Kurgäste health-data aggregation
    "aggregate_kurgaste_health_data",
    # AC-2 / AC-5 — DSGVO Art. 9 validation exception class
    "DSGVOArt9ValidationError",
    # AC-1 (iter-36) — 2026 Satzung schema extract
    "extract_2026_satzung_schema",
    # AC-2 (iter-36) — 2026 profile loader
    "load_2026_profile",
    # AC-3 (iter-36) — 2026 attestation template applier
    "apply_2026_attestation_template",
    # AC-4 (iter-36) — anti-drift SHA-256 integrity check
    "compute_anti_drift_sha",
]