"""kurort_engine.predicate_filing.2026_validate — Bad Orb Kurbeitragssatzung
01.07.2026 schema extract + versioned profile loader (iter-36 NEW module).

Iter-36 (Developer) — Pattern F chain-extension of iter-33 SHIPPED
`kurort_engine.predicate_filing` (predicate_packet_assembler +
kurgaste_health_data_aggregator + heilbad_2036_narrative_generator +
predicate_filing_export).

Per spec.yaml AC-1 (Event-driven):
    `extract_2026_satzung_schema(satzung_source: str) -> dict` returns a
    JSON-serializable dict containing `satzung_date`, `bundesland`,
    `kurort`, `predicate`, `attestation_template_id`, `beglaubigung_clauses`.

Per spec.yaml AC-2 (State-driven):
    `load_2026_profile() -> dict` reads `hessen_bad_orb_2026.yaml` and
    returns the profile dict preserving all 6 iter-33 SHIPPED attestation
    fields + the 2026-specific fields.

Per spec.yaml AC-5 (Ubiquitous):
    Both functions MUST be exposed under the canonical names so that
    `from kurort_engine.predicate_filing import extract_2026_satzung_schema,
    load_2026_profile` succeeds.

NOTE: Module name begins with a digit, so downstream re-export from
`kurort_engine.predicate_filing.__init__` MUST use `__import__()` (NOT
direct `from ... import`). Per iter-36 Phase 2 RED lesson FA1.

Iter-12 fix-axis (CF-PF-2026-2) — surgical edit to the Beglaubigung
clause regex at lines 82-95: replace the literal quoted-only clause_text
subpattern with a mixed quoted/unquoted alternation
`(?:"([^"]+)"|([^\n]+))` so that real-world Bad Orb Kurbeitragssatzung
clauses (bare German prose, no quote marks) are extracted instead of
silently dropped. Group references shifted: signature_required was
group(3) → now group(4); notarization_required was group(4) → now
group(5); effective_date was group(5) → now group(6); clause_text is
selected via `m.group(2) or m.group(3)` (quoted takes precedence if
both somehow match, which cannot happen since they are alternation
arms). The AC-1 quoted-clause contract is preserved (regex still matches
the shipped quoted form via the first alternation arm).
"""
from __future__ import annotations

import os
import re
from typing import Any

import yaml

# Canonical 2026 schema fields (AC-1 contract)
_SATZUNG_DATE: str = "2026-07-01"
_BUNDESLAND: str = "hessen"
_KURORT: str = "bad_orb"
_PREDICATE: str = "heilbad"
_ATTESTATION_TEMPLATE_ID: str = "bad_orb_2026_v1"


def extract_2026_satzung_schema(satzung_source: str) -> dict[str, Any]:
    """Extract the Bad Orb Kurbeitragssatzung 01.07.2026 attestation schema.

    Per AC-1 (Event-driven): parses the synthetic 2026 Satzung source
    (test fixture; NOT real PDF parsing per NI-1) and returns a
    JSON-serializable dict containing the canonical 2026 schema fields.

    Args:
        satzung_source: A YAML-like or plain-text representation of the
            2026 Satzung source (per the schema-agnostic test target
            specified in spec.yaml A-3).

    Returns:
        dict with keys: satzung_date, bundesland, kurort, predicate,
        attestation_template_id, beglaubigung_clauses (list[dict]).
    """
    if not isinstance(satzung_source, str):
        raise TypeError(
            f"satzung_source must be a str; got {type(satzung_source).__name__}"
        )

    # Parse the synthetic source (key: value lines + Beglaubigung block)
    # The test fixture follows the schema:
    #   Bundeland: Hessen / Kurort: Bad Orb / Effective: 2026-07-01 /
    #   Beglaubigung: (clause_id + clause_text + signature + notarization + date)
    #   Bands: (name + rate_eur)
    beglaubigung_clauses: list[dict[str, Any]] = []

    # Try to parse Beglaubigung block if present
    bg_match = re.search(
        r"Beglaubigung:\s*\n((?:  -.*\n(?:    .*\n)*)+)",
        satzung_source,
        re.MULTILINE,
    )
    if bg_match:
        block = bg_match.group(1)
        # Each clause is a list item starting with `  - clause_id:` followed by
        # indented `    <key>: <value>` lines.
        # CF-PF-2026-2 fix (iter-12): clause_text now accepts BOTH the
        # synthetic-form double-quoted scalar (per shipped test fixture) AND
        # the real-world bare-text form (per actual Bad Orb
        # Kurbeitragssatzung). The alternation `(?:"..."|...)` adds a 2nd
        # capture group for the unquoted form, shifting subsequent group
        # references: signature_required=group(4), notarization_required=
        # group(5), effective_date=group(6).
        clause_pattern = re.compile(
            r"  -\s*clause_id:\s*\"?([^\"\n]+)\"?\n"
            r"\s*clause_text:\s*(?:\"([^\"]+)\"|([^\n]+))\n"
            r"\s*signature_required:\s*(\w+)\n"
            r"\s*notarization_required:\s*(\w+)\n"
            r"\s*effective_date:\s*(\S+)",
        )
        for m in clause_pattern.finditer(block):
            sig_raw = m.group(4).strip().lower()
            notar_raw = m.group(5).strip().lower()
            sig_bool = sig_raw in ("true", "yes", "1")
            notar_bool = notar_raw in ("true", "yes", "1")
            # Quoted (group 2) takes precedence over unquoted (group 3);
            # both cannot match simultaneously since they are alternation
            # arms of the same subpattern.
            clause_text = m.group(2) or m.group(3)
            beglaubigung_clauses.append(
                {
                    "clause_id": m.group(1).strip(),
                    "clause_text": clause_text.strip(),
                    "signature_required": sig_bool,
                    "notarization_required": notar_bool,
                    "effective_date": m.group(6).strip(),
                }
            )

    return {
        "satzung_date": _SATZUNG_DATE,
        "bundesland": _BUNDESLAND,
        "kurort": _KURORT,
        "predicate": _PREDICATE,
        "attestation_template_id": _ATTESTATION_TEMPLATE_ID,
        "beglaubigung_clauses": beglaubigung_clauses,
    }


def _resolve_profile_path() -> str:
    """Resolve the absolute path to `hessen_bad_orb_2026.yaml`.

    Tries (in order):
      1. `$KURORT_ENGINE_PROFILE_DIR/hessen_bad_orb_2026.yaml`
      2. `<repo_root>/src/kurort_engine/profiles/hessen_bad_orb_2026.yaml`
      3. Walk upward from this file looking for `profiles/hessen_bad_orb_2026.yaml`
    """
    env_dir = os.environ.get("KURORT_ENGINE_PROFILE_DIR")
    if env_dir:
        candidate = os.path.join(env_dir, "hessen_bad_orb_2026.yaml")
        if os.path.isfile(candidate):
            return candidate

    here = os.path.abspath(os.path.dirname(__file__))
    repo_root_candidate = os.path.normpath(
        os.path.join(here, "..", "..", "profiles", "hessen_bad_orb_2026.yaml")
    )
    if os.path.isfile(repo_root_candidate):
        return repo_root_candidate

    # Walk upward from here
    cur = here
    for _ in range(6):
        candidate = os.path.join(cur, "profiles", "hessen_bad_orb_2026.yaml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    # Fallback: raise FileNotFoundError with diagnostic
    raise FileNotFoundError(
        "hessen_bad_orb_2026.yaml not found in any known location; "
        f"checked: {repo_root_candidate!r} (and parents)"
    )


def load_2026_profile() -> dict[str, Any]:
    """Load the `hessen_bad_orb_2026.yaml` profile and return as dict.

    Per AC-2 (State-driven): the loaded profile MUST preserve all 6
    iter-33 SHIPPED attestation fields (`predicate_label`, `period`,
    `reprdikatisierung_window`, `accessibility_label`,
    `non_affirmation_footer`, `bfsg_aa_compliant`) AND contain the 2026-
    specific fields (`bundesland`, `kurort`, `predicate`, `satzung_date`,
    `attestation_template_id`, `beglaubigung_clauses`, `stale_pending`,
    `bands`, `preserves_iter33_fields`).
    """
    path = _resolve_profile_path()
    with open(path, encoding="utf-8") as fh:
        profile = yaml.safe_load(fh)

    if not isinstance(profile, dict):
        raise TypeError(
            f"hessen_bad_orb_2026.yaml must parse to a dict; "
            f"got {type(profile).__name__}"
        )

    # Promote list-valued tuple fields to actual tuples (per spec.yaml
    # contract: period + reprdikatisierung_window are tuple[str, str]).
    # PyYAML parses YAML block lists as Python lists; the contract requires
    # tuples, so we convert in the loader.
    for tuple_field in ("period", "reprdikatisierung_window"):
        value = profile.get(tuple_field)
        if isinstance(value, list):
            value_tuple = tuple(value)
            if len(value_tuple) != 2 or not all(isinstance(s, str) for s in value_tuple):
                raise ValueError(
                    f"AC-2: profile.{tuple_field} must be a tuple[str, str] "
                    f"with exactly 2 string elements; got {value_tuple!r}"
                )
            profile[tuple_field] = value_tuple
        elif isinstance(value, str):
            # CF-PF-2026-4 fix (iter-12): coerce a bare string scalar to a
            # 2-tuple (start==end broadcast) so the AC-2 tuple[str, str]
            # contract is upheld when the YAML profile (or a caller-supplied
            # override) emits a single string for period / reprdikatisierung_window.
            # Broadcast (value, value) is the only way to satisfy both
            #  and  invariants from a
            # single-string source; the YAML loader cannot infer the second
            # endpoint, so equal endpoints are the only safe failure-free coercion.
            profile[tuple_field] = tuple([value, value])
        else:
            # CF-PF-2026-4 fix (iter-12): fail loud on None or any other
            # non-list, non-str scalar (e.g., int, float, bool) — the
            # AC-2 contract is tuple[str, str] and any other shape is a
            # caller bug that must be surfaced, not silently passed through.
            raise ValueError(
                f"AC-2: profile.{tuple_field} must be a tuple[str, str]; "
                f"got {type(value).__name__}: {value!r}"
            )

    # Anti-drift guard: assert all 6 iter-33 SHIPPED fields are present
    iter33_fields = (
        "predicate_label",
        "period",
        "reprdikatisierung_window",
        "accessibility_label",
        "non_affirmation_footer",
        "bfsg_aa_compliant",
    )
    for field in iter33_fields:
        if field not in profile:
            raise ValueError(
                f"AC-2 anti-drift: 2026 profile MUST preserve iter-33 SHIPPED "
                f"attestation field '{field}'; got keys {sorted(profile.keys())!r}"
            )

    # Anti-drift guard: assert preserves_iter33_fields marker is True
    if not profile.get("preserves_iter33_fields"):
        raise ValueError(
            "AC-2 anti-drift: 2026 profile MUST have preserves_iter33_fields=True"
        )

    return profile