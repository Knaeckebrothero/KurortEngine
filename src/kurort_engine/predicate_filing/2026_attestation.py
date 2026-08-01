"""kurort_engine.predicate_filing.2026_attestation — Bad Orb Kurbeitragssatzung
01.07.2026 attestation template + anti-drift SHA integrity (iter-36 NEW module).

Iter-36 (Developer) — Pattern F chain-extension of iter-33 SHIPPED
`kurort_engine.predicate_filing` (predicate_packet_assembler +
kurgaste_health_data_aggregator + heilbad_2036_narrative_generator +
predicate_filing_export) + iter-21 SHIPPED
`kurort_engine.kurkarte_wallet.BFSGComplianceError`.

Per spec.yaml AC-3 (Ubiquitous):
    `apply_2026_attestation_template(profile: dict, attestation_data: dict)
    -> dict` returns a dict with attestation_template_id, satzung_date,
    predicate_label, adult_rate_applied (string "2.50" with 100% precision),
    beglaubigung_sealed (True), accessibility_label (>= 20 chars), and
    non_affirmation_footer (verbatim 2026 Satzung clause).

Per spec.yaml AC-4 (Ubiquitous):
    `compute_anti_drift_sha(profile: dict, baseline_sha: str | None = None)
    -> str` returns the 64-char lowercase hex SHA-256 digest of a canonical
    JSON representation of the iter-33 SHIPPED chain-extension. Raises
    `kurort_engine.kurkarte_wallet.BFSGComplianceError` (re-used from
    SHIPPED iter-21) if the chain-extension has drifted.

Per spec.yaml AC-5 (Ubiquitous):
    Both functions MUST be exposed under the canonical names so that
    `from kurort_engine.predicate_filing import apply_2026_attestation_template,
    compute_anti_drift_sha` succeeds.

NOTE: Module name begins with a digit, so downstream re-export from
`kurort_engine.predicate_filing.__init__` MUST use `__import__()` (NOT
direct `from ... import`). Per iter-36 Phase 2 RED lesson FA1.

Iter-12 fix-axis (CF-PF-2026-1 + CF-PF-2026-3) — surgical edits to
`_find_adult_rate_eur` (line 73: use `Decimal(str(rate)):.2f` for 100%
precision) and the BFSGComplianceError diagnostic message (lines 248-256:
trim to reference ONLY the iter-33 chain-extension modules; add explicit
clause that the 6 SHIPPED modules are protected by separate git-diff
discipline). 6 SHAs + 4 iter-33 SHIPPED predicate_filing modules + this
module's `kurort_engine.predicate_filing.__init__` re-export surface are
preserved byte-identical per anti-drift discipline.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from decimal import Decimal
from typing import Any

# Anti-drift: import BFSGComplianceError from SHIPPED iter-21 kurkarte_wallet
from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402,F401

# Verbatim 2026 Satzung non-affirmation footer clause (AC-3 contract)
_NON_AFFIRMATION_FOOTER_2026 = (
    "This Kurort-predicate attestation is generated against the Bad Orb "
    "Kurbeitragssatzung 01.07.2026 and is provided as voluntary "
    "predicate-renewal positioning; it is NOT a regulatory compliance "
    "attestation"
)

# Verbatim accessibility_label for the 2026 attestation (>= 20 chars per
# WCAG 2.1 SC 4.1.3 + EN 301 549 baseline)
_ACCESSIBILITY_LABEL_2026 = (
    "Bad Orb Kurbeitragssatzung 01.07.2026 predicate-renewal filing for "
    "Hotel Rheinland Bad Orb Kurort-predicate attestation"
)


def _find_adult_rate_eur(bands: list[dict[str, Any]]) -> str:
    """Return the `adult` band's `rate_eur` as a string with 100% precision.

    Per AC-3: `adult_rate_applied: str = "2.50"` with 100% precision match.

    CF-PF-2026-1 fix (iter-12): use `Decimal(str(rate)):.2f` formatting so
    that a Python float `2.50` (or YAML unquoted `2.50` which PyYAML parses
    as float) is rendered as the canonical 2-decimal-place string `"2.50"`,
    NOT `"2.5"`. This preserves the canonical Kurbeitragssatzung "2,50 EUR"
    representation for downstream `Decimal(result['adult_rate_applied'])`
    reconstruction.
    """
    for band in bands or []:
        if band.get("name") == "adult":
            rate = band.get("rate_eur") or band.get("rate_per_day")
            if rate is None:
                raise ValueError(
                    "AC-3: adult band must have rate_eur or rate_per_day; "
                    f"got {band!r}"
                )
            return f"{Decimal(str(rate)):.2f}"
    raise ValueError(
        "AC-3: profile.bands MUST contain an 'adult' band; "
        f"got names {[b.get('name') for b in (bands or [])]!r}"
    )


def apply_2026_attestation_template(
    profile: dict[str, Any],
    attestation_data: dict[str, Any],
) -> dict[str, Any]:
    """Apply the 2026 Kurort-predicate attestation template.

    Per AC-3 (Ubiquitous): returns a JSON-serializable dict with:
      * attestation_template_id (string; from profile)
      * satzung_date (string; from profile)
      * predicate_label (string; from profile)
      * adult_rate_applied (string "2.50" with 100% precision)
      * beglaubigung_sealed (bool; True if all Beglaubigung clauses present)
      * accessibility_label (string >= 20 chars)
      * non_affirmation_footer (string with verbatim 2026 Satzung clause)
    """
    if not isinstance(profile, dict):
        raise TypeError(
            f"profile must be a dict; got {type(profile).__name__}"
        )
    if not isinstance(attestation_data, dict):
        raise TypeError(
            f"attestation_data must be a dict; got {type(attestation_data).__name__}"
        )

    attestation_template_id = profile.get("attestation_template_id")
    if not isinstance(attestation_template_id, str):
        raise ValueError(
            "AC-3: profile.attestation_template_id must be a str; "
            f"got {type(attestation_template_id).__name__}: {attestation_template_id!r}"
        )

    satzung_date = profile.get("satzung_date")
    if not isinstance(satzung_date, str):
        raise ValueError(
            "AC-3: profile.satzung_date must be a str; "
            f"got {type(satzung_date).__name__}: {satzung_date!r}"
        )

    predicate_label = profile.get("predicate_label")
    if not isinstance(predicate_label, str):
        raise ValueError(
            "AC-3: profile.predicate_label must be a str; "
            f"got {type(predicate_label).__name__}: {predicate_label!r}"
        )

    bands = profile.get("bands") or []
    adult_rate_applied = _find_adult_rate_eur(bands)

    beglaubigung_clauses = profile.get("beglaubigung_clauses") or []
    # beglaubigung_sealed=True if all clauses carry signature_required=True
    beglaubigung_sealed = all(
        bool(c.get("signature_required", False)) for c in beglaubigung_clauses
    ) if beglaubigung_clauses else False

    return {
        "attestation_template_id": attestation_template_id,
        "satzung_date": satzung_date,
        "predicate_label": predicate_label,
        "adult_rate_applied": adult_rate_applied,
        "beglaubigung_sealed": beglaubigung_sealed,
        "accessibility_label": _ACCESSIBILITY_LABEL_2026,
        "non_affirmation_footer": _NON_AFFIRMATION_FOOTER_2026,
    }


# Iter-33 SHIPPED chain-extension modules (anti-drift discipline: NEVER modify
# any of these files; we only READ them via importlib.util to compute SHA).
_ITER33_CHAIN_EXTENSION_MODULES: tuple[str, ...] = (
    "kurort_engine.predicate_filing.predicate_packet_assembler",
    "kurort_engine.predicate_filing.kurgaste_health_data_aggregator",
    "kurort_engine.predicate_filing.heilbad_2036_narrative_generator",
    "kurort_engine.predicate_filing.predicate_filing_export",
)


def _read_source_via_importlib(module_name: str) -> str:
    """Read the source code of a module via importlib.util.find_spec.

    Falls back to reading the file directly if the spec cannot be resolved.
    """
    try:
        spec = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ImportError):
        spec = None
    if spec is not None and getattr(spec, "origin", None):
        origin = spec.origin
        if origin and os.path.isfile(origin):
            with open(origin, encoding="utf-8") as fh:
                return fh.read()
    # Fallback: derive path from module name
    parts = module_name.split(".")
    # `kurort_engine.predicate_filing.predicate_packet_assembler` ->
    # `<repo_root>/src/kurort_engine/predicate_filing/predicate_packet_assembler.py`
    rel_path = os.path.join("src", *parts) + ".py"
    if os.path.isfile(rel_path):
        with open(rel_path, encoding="utf-8") as fh:
            return fh.read()
    # Last-ditch: try resolving relative to this file
    here = os.path.abspath(os.path.dirname(__file__))
    rel_to_here = os.path.normpath(os.path.join(here, "..", "..", "..", *parts) + ".py")
    if os.path.isfile(rel_to_here):
        with open(rel_to_here, encoding="utf-8") as fh:
            return fh.read()
    raise FileNotFoundError(
        f"Could not resolve source for module {module_name!r}"
    )


def compute_anti_drift_sha(
    profile: dict[str, Any],
    baseline_sha: str | None = None,
) -> str:
    """Compute the SHA-256 anti-drift integrity check on the iter-33 chain-extension.

    Per AC-4 (Ubiquitous):
      * Returns the 64-char lowercase hex SHA-256 digest of a canonical JSON
        representation of the iter-33 SHIPPED `predicate_filing` chain-extension.
      * If `baseline_sha` is provided AND the iter-33 chain-extension has NOT
        drifted, returns `baseline_sha` unchanged.
      * If `baseline_sha` is provided AND the iter-33 chain-extension HAS
        drifted (computed SHA != baseline_sha), raises
        `kurort_engine.kurkarte_wallet.BFSGComplianceError` (re-used from
        SHIPPED iter-21).
      * Does NOT modify any of the 6 SHIPPED modules (only reads them).

    CF-PF-2026-3 fix (iter-12): the BFSGComplianceError message references
    ONLY the 4 iter-33 chain-extension modules that are actually in the SHA
    envelope (per `_ITER33_CHAIN_EXTENSION_MODULES`). The 6 SHIPPED modules
    are protected by SEPARATE git-diff discipline per iter-30 SHIPPED
    foundation verify ritual — they are NOT in the runtime SHA envelope, so
    they MUST NOT be named in this diagnostic (would send operator on a
    wild-goose chase to inspect modules that are not actually checked at
    runtime).
    """
    if not isinstance(profile, dict):
        raise TypeError(
            f"profile must be a dict; got {type(profile).__name__}"
        )

    # Canonical JSON representation of the iter-33 chain-extension:
    # include the profile's identifies + SHA of each chain-extension module.
    sources: dict[str, str] = {}
    for module_name in _ITER33_CHAIN_EXTENSION_MODULES:
        try:
            sources[module_name] = _read_source_via_importlib(module_name)
        except FileNotFoundError:
            # If a module cannot be resolved, use an empty string so the SHA
            # is still computable but mark it clearly.
            sources[module_name] = ""

    # Canonical envelope: order-stable JSON
    envelope = {
        "profile_attestation_template_id": profile.get("attestation_template_id"),
        "profile_satzung_date": profile.get("satzung_date"),
        "profile_bundesland": profile.get("bundesland"),
        "profile_kurort": profile.get("kurort"),
        "iter33_chain_extension_sources": sources,
        "iter33_chain_extension_modules": list(_ITER33_CHAIN_EXTENSION_MODULES),
    }

    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # Validate baseline_sha format if provided
    if baseline_sha is not None:
        if not isinstance(baseline_sha, str):
            raise TypeError(
                f"baseline_sha must be a str or None; got {type(baseline_sha).__name__}"
            )
        if len(baseline_sha) != 64 or not all(
            c in "0123456789abcdefABCDEF" for c in baseline_sha
        ):
            raise ValueError(
                f"baseline_sha must be 64-char hex SHA-256 digest; "
                f"got {len(baseline_sha)} chars: {baseline_sha!r}"
            )
        if digest != baseline_sha:
            # iter-33 chain-extension has drifted; raise BFSGComplianceError.
            # CF-PF-2026-3 fix: message references ONLY the 4 iter-33 chain-
            # extension modules (the actual SHA envelope). Modules outside
            # this envelope are protected by separate git-diff discipline
            # (per iter-30 SHIPPED foundation verify ritual) and are NOT
            # named here (would be misleading).
            raise BFSGComplianceError(
                f"AC-4 anti-drift violation: iter-33 SHIPPED predicate_filing "
                f"chain-extension has drifted. Computed SHA-256={digest!r} does "
                f"not match baseline_sha={baseline_sha!r}. The 4 iter-33 SHIPPED "
                f"chain-extension modules (predicate_packet_assembler + "
                f"kurgaste_health_data_aggregator + "
                f"heilbad_2036_narrative_generator + predicate_filing_export) "
                f"MUST remain verbatim UNCHANGED. Modules outside the runtime "
                f"SHA envelope are protected by separate git-diff discipline "
                f"and are not verified at runtime."
            )
        # No drift: return baseline_sha unchanged
        return baseline_sha

    # No baseline: return the computed SHA
    return digest
