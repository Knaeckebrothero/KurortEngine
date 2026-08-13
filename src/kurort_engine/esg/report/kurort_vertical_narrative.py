"""kurort_engine.esg.report.kurort_vertical_narrative — AC-4 Heilbad predicate 2036.

Iteration 27 (Developer) — Q5.1 ESG-CSRD/VSME Group 2.
Chosen by Critic verdict (iter-26) from iter-25 Scholar Proposal 002.

AC-4 contract (verbatim from spec.yaml):

    Event-driven. When `generate_heilbad_predicate_2036()` is called in
    `kurort_engine.esg.report.kurort_vertical_narrative` THEN the system shall
    return a `dict` describing the Heilbad predicate 2036 ESG narrative for
    Hotel Rheinland Bad Orb, with required keys: `predicate_label: str = "Heilbad
    Bad Orb (Hessischer Heilbäderverband)"`, `narrative_de: str` (German narrative
    block ≥ 200 chars mentioning Spessart Bike Tage + R3 Kinzigtal + WaldErfahren
    + E-Bike charging + Toskana Therme partnership + thermal-spring
    NiedrigEnergie baseline), `narrative_en: str` (English narrative block
    ≥ 200 chars with the same six anchors for Frau Steuerberaterin Müller DATEV
    verification surface), `lang: str = "de"`, `accessibility_label: str`
    (BFSG-EAA compliant accessibilityLabel ≥ 20 chars per WCAG 2.1 SC 4.1.3 +
    EN 301 549 baseline).

Reference: Hessischer Heilbäderverband certification anchor per
`iter-25-proposal-002-q51-esg-csrd-voluntary-vsme-hcmi-scope-3-tier-2-410-loc` §12.
"""
from __future__ import annotations

# Canonical 6 Kurort-vertical anchors per spec.yaml §12 + reference A-5.
# Used verbatim in BOTH the German and the English narrative blocks.
ANCHORS: tuple[str, ...] = (
    "Spessart Bike Tage",
    "R3 Kinzigtal",
    "WaldErfahren",
    "E-Bike charging",
    "Toskana Therme",
    "thermal-spring NiedrigEnergie",
)

# BFSG-EAA compliant accessibilityLabel (≥ 20 chars per WCAG 2.1 SC 4.1.3
# + EN 301 549 baseline). Static string — shared by all narrative builds.
ACCESSIBILITY_LABEL: str = "Heilbad Bad Orb ESG Narrative 2036 (Hessischer Heilbäderverband)"

# Module-level German narrative (≥ 200 chars; contains all 6 canonical anchors).
# Anchored to:
#   - Hessischer Heilbäderverband certification (Heilbad predicate requirement)
#   - Spessart Bike Tage (seasonal outdoor cycling event)
#   - R3 Kinzigtalradweg (premium cycling route waypoint)
#   - WaldErfahren (forest experience programme)
#   - iter-24 E-Bike charging (Q5.2 E-Bike/E-Auto charging integration)
#   - Toskana Therme partnership (Kur-thermal cross-sell)
#   - thermal-spring NiedrigEnergie baseline (Scope 1 heating reduction)
NARRATIVE_DE: str = (
    "Hotel Rheinland in Bad Orb ist als Heilbad nach dem Hessischen "
    "Heilbäderverband zertifiziert und bekennt sich zum Heilbad-Prädikat "
    "2036 mit ganzheitlicher ESG-Verantwortung. Die Kurort-vertikale "
    "Erzählung verankert sechs regionale Beschaffer: Die jährlichen "
    "Spessart Bike Tage und der R3 Kinzigtalradweg etablieren Bad Orb "
    "als touristische Destination, während das ganzjährige WaldErfahren-"
    "Programm die heilklimatischen Wälder curational erschließt. "
    "Quartiergäste nutzen die im Hause installierte E-Bike charging "
    "Infrastruktur aus dem iter-24 Q5.2-Ausbau (Kurort-ESG-Modellprojekt "
    "Hessen). Die Partnerschaft mit der Toskana Therme verzahnt thermal-"
    "heilkundliche Anwendungen mit touristischen Tagesgästen. Die "
    "Scope-1-Heizungsemissionen werden über die thermal-spring "
    "NiedrigEnergie baseline des Hessischen Heilbäderverbandes "
    "kontinuierlich gesenkt. Dieses ESG-Narrativ bildet die Grundlage "
    "für den VSME B3 Bericht, das CSRD-Reporting ab 2028 sowie für die "
    "Gastgeber-Klimaneutralität 2030."
)

# Module-level English narrative (≥ 200 chars; same 6 canonical anchors,
# DATEV verification surface for Frau Steuerberaterin Müller).
NARRATIVE_EN: str = (
    "Hotel Rheinland in Bad Orb is certified as a Heilbad (spa resort) "
    "by the Hessischer Heilbäderverband and commits to the Heilbad "
    "predicate 2036 with holistic ESG responsibility. The Kurort-"
    "vertical narrative anchors six regional procurement channels: the "
    "annual Spessart Bike Tage and the R3 Kinzigtal cycling route "
    "establish Bad Orb as a tourist destination, while the year-round "
    "WaldErfahren forest experience programme curatively reveals the "
    "therapeutic-climatic forests. Guests staying at the hotel use the "
    "in-house E-Bike charging infrastructure from iter-24 Q5.2 expansion "
    "(Hessen Kurort-ESG pilot project). The Toskana Therme partnership "
    "intertwines thermal-therapeutic applications with day-spa tourists. "
    "Scope 1 heating emissions are continuously reduced via the thermal-"
    "spring NiedrigEnergie baseline of the Hessischer Heilbäderverband. "
    "This ESG narrative forms the basis for the VSME B3 report, CSRD "
    "reporting from 2028 onwards, and the Gastgeber-Klimaneutralität 2030."
)


def generate_heilbad_predicate_2036() -> dict:
    """Build the Heilbad predicate 2036 ESG narrative for Hotel Rheinland Bad Orb.

    No arguments — this is a pure factory-style narrative builder. The
    German + English narratives are constructed from the module-level
    constants ``NARRATIVE_DE`` + ``NARRATIVE_EN`` + ``ANCHORS`` + the
    predicate label (Hessischer Heilbäderverband) + accessibility label.

    Returns
    -------
    dict
        A JSON-serialisable dict with required keys per spec.yaml AC-4 EARS:

          * ``predicate_label`` — ``str`` exactly equal to
            ``"Heilbad Bad Orb (Hessischer Heilbäderverband)"``.
          * ``narrative_de`` — ``str`` German narrative block ≥ 200 chars
            containing all 6 canonical Kurort-vertical anchor substrings.
          * ``narrative_en`` — ``str`` English narrative block ≥ 200 chars
            containing all 6 canonical Kurort-vertical anchor substrings
            (DATEV verification surface for Frau Steuerberaterin Müller).
          * ``lang`` — ``str`` exactly equal to ``"de"`` (BFSG-EAA primary
            language per Barrierefreiheitsstärkungsgesetz in force
            28.06.2025).
          * ``accessibility_label`` — ``str`` ≥ 20 chars, BFSG-EAA
            compliant per WCAG 2.1 SC 4.1.3 + EN 301 549 baseline
            (screen-reader accessible).
    """
    return {
        "predicate_label": "Heilbad Bad Orb (Hessischer Heilbäderverband)",
        "narrative_de": NARRATIVE_DE,
        "narrative_en": NARRATIVE_EN,
        "lang": "de",
        "accessibility_label": ACCESSIBILITY_LABEL,
    }


__all__ = [
    "generate_heilbad_predicate_2036",
    "ANCHORS",
    "NARRATIVE_DE",
    "NARRATIVE_EN",
    "ACCESSIBILITY_LABEL",
]
