"""i18n catalog + translate() helper for kurort_engine.a11y.guest_pwa.

Per ``spec/a11y_guest_pwa/spec.yaml`` AC-1 EARS (verbatim L84-94): the
BFSG-EAA self-attestation claim must reference BFSG-EAA §3(1) and
EN 301 549 V3.2.1 / WCAG 2.1 AA. Hotel Rheinland Bad Orb guest-facing
strings need DE (primary), EN, NL translations to support the cross-
border guest mix (Hessen KAG Kurbeitrag + Euregio tourism).

This module is a **Tier-2 stub** (per spec.yaml not_included L166):
"DE/EN/NL i18n catalog content authoring (i18n_catalog.py stub OK)".
The catalog contains the canonical BFSG-EAA self-attestation string in
each supported locale plus a minimal key set for the Phase 7b surface.
Authoring additional keys is a follow-up engagement (per iter-2 handoff).

Public surface:
  * ``I18N_CATALOG`` — module-level dict
  * ``SUPPORTED_LOCALES`` — tuple of locale codes
  * ``translate(key, locale)`` — locale lookup helper with fallback
"""
from __future__ import annotations

SUPPORTED_LOCALES: tuple[str, ...] = ("de", "en", "nl")

DEFAULT_LOCALE: str = "de"  # Hessen KAG primary locale


I18N_CATALOG: dict[str, dict[str, str]] = {
    "de": {
        # BFSG-EAA §3(1) self-attestation marker (per spec.yaml AC-1)
        "self_attest": (
            "Selbstbescheinigung BFSG-EAA §3(1): Konformität mit "
            "WCAG 2.1 AA und EN 301 549 V3.2.1 für den Hotel-Rheinland-"
            "Bad-Orb-Gast-PWA-Buchungsablauf."
        ),
        "wcag_level": "WCAG 2.1 AA",
        "en_standard": "EN 301 549 V3.2.1",
        "tenant_scope": "kurort_engine.a11y.guest_pwa",
    },
    "en": {
        # BFSG-EAA §3(1) self-attestation marker (per spec.yaml AC-1)
        "self_attest": (
            "BFSG-EAA §3(1) self-attestation: conformance with "
            "WCAG 2.1 AA and EN 301 549 V3.2.1 for the Hotel Rheinland "
            "Bad Orb guest PWA booking flow."
        ),
        "wcag_level": "WCAG 2.1 AA",
        "en_standard": "EN 301 549 V3.2.1",
        "tenant_scope": "kurort_engine.a11y.guest_pwa",
    },
    "nl": {
        # BFSG-EAA §3(1) self-attestation marker (per spec.yaml AC-1)
        "self_attest": (
            "BFSG-EAA §3(1) zelfattestatie: conformiteit met "
            "WCAG 2.1 AA en EN 301 549 V3.2.1 voor de Hotel Rheinland "
            "Bad Orb gast-PWA-boekingsstroom."
        ),
        "wcag_level": "WCAG 2.1 AA",
        "en_standard": "EN 301 549 V3.2.1",
        "tenant_scope": "kurort_engine.a11y.guest_pwa",
    },
}


class I18nKeyError(KeyError):
    """Raised when a translation key is missing in the requested locale.

    Subclass of ``KeyError`` (preserves backward-compat with ``dict[key]``
    callers) but lets handlers distinguish i18n misses from other dict
    misses if they want to.
    """


def translate(key: str, locale: str = DEFAULT_LOCALE) -> str:
    """Look up a translation for ``key`` in ``locale``.

    Args:
      key: catalog key (e.g. ``"self_attest"``, ``"wcag_level"``).
      locale: ISO-639-1 locale code; must be in ``SUPPORTED_LOCALES``.
              Defaults to ``DEFAULT_LOCALE`` (``"de"``).

    Returns:
      The localized string.

    Raises:
      ``I18nKeyError`` if the locale is unsupported OR the key is
      missing in that locale.
    """
    if locale not in I18N_CATALOG:
        raise I18nKeyError(
            f"Unsupported locale {locale!r}; supported={SUPPORTED_LOCALES!r}"
        )
    catalog = I18N_CATALOG[locale]
    if key not in catalog:
        raise I18nKeyError(
            f"Missing i18n key {key!r} in locale {locale!r}; "
            f"available keys={sorted(catalog.keys())!r}"
        )
    return catalog[key]


def available_keys(locale: str = DEFAULT_LOCALE) -> list[str]:
    """Return the sorted list of catalog keys available for ``locale``."""
    if locale not in I18N_CATALOG:
        raise I18nKeyError(
            f"Unsupported locale {locale!r}; supported={SUPPORTED_LOCALES!r}"
        )
    return sorted(I18N_CATALOG[locale].keys())