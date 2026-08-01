"""kurort_engine.esg.report — Q5.1 ESG report public API (Tier-2).

Iteration 27 (Developer) — chosen by Critic verdict (iter-26) from iter-25
Scholar Proposal 002 (Q5.1 ESG-CSRD Voluntary VSME + HCMI Scope 3 Tier-2).
Mix B applied per `iter-26-critic-lawyer-budget-gate-verification-state-of-project-unchanged-mix-b-`:
NO Lawyer review required (voluntary ESG = no AVV + no Art. 9 + no contract law).

Iteration 30 (Developer) — Pattern F chain-extension of iter-27 SHIPPED Q5.1
ESG surface. Chosen by iter-29 Critic verdict from iter-28 Scholar Proposal 002
(Axis B HCMI Scope 1+2 EXTENSION). Adds 5 new symbols (calculate_scope_1 +
calculate_scope_2 + calculate_scope_1_2 from hcmi_scope1_2_calculator +
generate_heilbad_2036_esg_narrative + export_scope1_2_bfsg_aa from
heilbad_predicate_2036_repraedikatisierung) to the public API surface.

Public API (re-exported)
------------------------

* :func:`collect_basic_module_b3` — VSME Basic Module B3 collector (AC-1)
* :func:`calculate_scope_3` — HCMI Scope 3 emissions calculator (AC-2)
* :func:`scope1_heating_thermal_spring_emissions` — Scope 1 thermal-spring
  NiedrigEnergie baseline calculator (companion stub per iter-25-proposal-002 §7)
* :func:`check_alignment` — Gastgeber-Klimaneutralität 2030 alignment
  surface (AC-3)
* :func:`generate_heilbad_predicate_2036` — Kurort-vertical Heilbad narrative
  generator (AC-4)
* :func:`export_lang_de_accessibilitylabel` — BFSG-AA compliant ESG
  disclosure (AC-5)
* :class:`BFSGComplianceError` — raised on BFSG-AA / WCAG 2.1 AA violation
  (AC-5; re-used from SHIPPED iter-21 kurkarte_wallet)

Iter-30 ADDITIONS (Pattern F chain-extension, Axis B HCMI Scope 1+2 EXTENSION):

* :func:`calculate_scope_1` — HCMI Scope 1 (direct) emissions calculator
  (AC-1 of iter-30; heating + refrigeration per Sustainable Hospitality
  Alliance (SHA) HCMI methodology 2025/2026 baseline).
* :func:`calculate_scope_2` — HCMI Scope 2 (purchased electricity) emissions
  calculator with ``green_electricity_contract`` factor selection (AC-2 of
  iter-30; OK Lab green 0.02 kg CO2e/kWh vs DE Strommix 0.42 kg CO2e/kWh).
* :func:`calculate_scope_1_2` — HCMI Scope 1+2 unified envelope calculator
  (AC-3 of iter-30; composes AC-1 + AC-2 into a single JSON-serialisable
  HCMI Scope 1+2 dict).
* :func:`generate_heilbad_2036_esg_narrative` — Heilbad 2036
  Reprädikatisierung forward-looking ESG narrative builder (AC-4 of
  iter-30; 6 Kurort-vertical anchors + lang="de" + accessibility_label
  ≥ 20 chars per WCAG 2.1 SC 4.1.3).
* :func:`export_scope1_2_bfsg_aa` — BFSG-EAA compliant HCMI Scope 1+2 ESG
  disclosure export (AC-5 of iter-30; emits RED-1 verbatim non-affirmation
  clause + RED-2 Sustainable Hospitality Alliance (SHA) HCMI methodology
  citation in the disclosure footer; raises
  :class:`BFSGComplianceError` on `lang != "de"` or missing
  `accessibility_label`).
"""
from __future__ import annotations

# AC-5 — BFSG-AA ESG disclosure
from kurort_engine.esg.report.bfsg_aa_esg_disclosure import (
    export_lang_de_accessibilitylabel,
)

# AC-3 — Gastgeber-Klimaneutralität 2030 alignment
from kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030 import (
    check_alignment,
)

# ---------------------------------------------------------------------------
# Iter-30 Pattern F chain-extension (Axis B HCMI Scope 1+2 EXTENSION).
# 5 NEW public-API symbols re-exported below; PRESERVES the 7 iter-27
# SHIPPED exports + their verbatim `__all__` order above.
# ---------------------------------------------------------------------------
# AC-1 — HCMI Scope 1 (direct) emissions calculator (iter-30).
# AC-2 — HCMI Scope 2 (purchased electricity) emissions calculator (iter-30).
# AC-3 — HCMI Scope 1+2 unified envelope calculator (iter-30).
from kurort_engine.esg.report.hcmi_scope1_2_calculator import (
    calculate_scope_1,
    calculate_scope_1_2,
    calculate_scope_2,
)

# AC-2 — HCMI Scope 3 emissions calculator
from kurort_engine.esg.report.hcmi_scope3_calculator import calculate_scope_3

# AC-4 — Heilbad 2036 Reprädikatisierung ESG narrative builder (iter-30).
# AC-5 — BFSG-EAA compliant HCMI Scope 1+2 ESG disclosure export (iter-30).
from kurort_engine.esg.report.heilbad_predicate_2036_repraedikatisierung import (
    export_scope1_2_bfsg_aa,
    generate_heilbad_2036_esg_narrative,
)

# AC-4 — Kurort-vertical Heilbad narrative generator
from kurort_engine.esg.report.kurort_vertical_narrative import (
    generate_heilbad_predicate_2036,
)

# Companion stub — Scope 1 thermal-spring NiedrigEnergie baseline calculator
# (per iter-25-proposal-002 §7; needed by Group 2 AC-3 + AC-4 even though not
# directly asserted in AC-1+AC-2).
from kurort_engine.esg.report.scope1_heating_thermal_spring import (
    scope1_heating_thermal_spring_emissions,
)

# AC-1 — VSME Basic Module B3 collector
from kurort_engine.esg.report.vsme_collector import collect_basic_module_b3

# Cross-cutting BFSG-AA exception class (re-used from SHIPPED iter-21 kurkarte_wallet)
from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402,F401

__all__ = [
    # Iter-27 SHIPPED exports (PRESERVED VERBATIM, original order intact).
    "BFSGComplianceError",
    "calculate_scope_3",
    "check_alignment",
    "collect_basic_module_b3",
    "export_lang_de_accessibilitylabel",
    "generate_heilbad_predicate_2036",
    "scope1_heating_thermal_spring_emissions",
    # Iter-30 NEW exports (Pattern F chain-extension, appended in AC-id order).
    "calculate_scope_1",
    "calculate_scope_2",
    "calculate_scope_1_2",
    "generate_heilbad_2036_esg_narrative",
    "export_scope1_2_bfsg_aa",
]