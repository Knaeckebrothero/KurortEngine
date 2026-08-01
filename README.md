# kurort_engine

Operator-facing, ERP-grade Kurort-vertical Python module for **Hotel Rheinland in Bad Orb**
(Hessen KAG, Kurbeitragssatzung effective 2020-07-01). `kurort_engine` is the in-house
replacement for Resavio, purpose-built for Kurort workflows: Kurtaxe calculation, Meldeschein
generation, Heilbad predicate filing, DSGVO Art. 17 cascade, Kurkarte digital wallet, ESG
reporting, channel-manager MinStay enforcement, EV charging, and spa/wellness resource
management.

The module ships **83 modules across 15 subpackages**, and is operator-reachable via
`python -m kurort_engine` and the `kurort-engine` CLI binary.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Key Modules](#key-modules)
- [Accessibility Tenants](#accessibility-tenants)
  - [BFSG-EAA Self-Attestation](#bfsg-eaa-self-attestation-a11yguest_pwa)
  - [BITV 2.0 Disclosure](#bitv-20-disclosure-a11yguest_pwabitv20)
- [Repository Layout](#repository-layout)
- [License](#license)
- [Contact](#contact)

## Overview

Hotel Rheinland is a small (~33-room) Kurort-vertical hotel in Bad Orb, Hessen. It must comply
with the Hessisches Kurortegesetz (HKG), the Kurbeitragssatzung Bad Orb (effective 2020-07-01),
the Hessisches Kommunalabgabengesetz (KAG) for tax remittance, the Bundesmeldegesetz (BMG) for
Meldeschein obligations, and the Beherbergungsmeldepflicht (§29 BMG).

`kurort_engine` replaces the third-party Resavio system with an in-house implementation that:

- Implements all Kurort-vertical workflows natively — Kurtaxe, Meldeschein, Heilbad predicate
  filing, BFSG-EAA accessibility, Badekur Rechnung with §23 SGB V prescription, Kurpaket
  orchestrator, and Kurkarte digital wallet.
- Ships first-closer regulatory coverage: Hessen KAG, BFSG-EAA WCAG 2.1 AA, DSGVO Art. 17
  cascade, ESG/CSRD voluntary VSME, NIS2 supplier checklist, and the DATEV SKR 2027 bridge.
- Provides a reproducible synthetic demo generating 100 reservations spanning all 5 Hessen
  Bad Orb rate bands and both recognised exemption categories.

## Installation

```bash
git clone https://github.com/Knaeckebrothero/KurortEngine.git
cd KurortEngine
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The `[dev]` extra installs `pytest`, `pytest-cov`, and `ruff`. The build backend is hatchling
(PEP 621 metadata). Requires Python 3.11+.

> **The virtualenv must live at `./.venv`.** Several tests shell out to
> `./.venv/bin/{pytest,ruff,pip,kurort-engine}` by relative path and fail if the venv is
> located elsewhere. It is git-ignored, never committed.

## Usage

```bash
# CLI entry point — prints version + subcommands
python -m kurort_engine --help
python -m kurort_engine version

# Synthetic Bad Orb month demo (generates 100 reservations → CSV)
python -m kurort_engine.demos.synthetic_bad_orb_month

# After `pip install -e ".[dev]"` the CLI binary is available without PYTHONPATH=src
kurort-engine --help
kurort-engine version
kurort-engine demo
```

The synthetic demo writes a byte-for-byte reproducible CSV to
`src/kurort_engine/demos/out/synthetic_bad_orb_<yyyy_mm>.csv` (currently period `2025-06`,
deterministic seed `random.Random(2025)`).

## Testing

```bash
# Full suite — 177 tests across 42 files
PYTHONPATH=src pytest tests/

# Repository layout bundle only (F1+F2+F3)
PYTHONPATH=src pytest tests/test_repo_layout.py -v

# Lint
ruff check src/
```

`test_repo_layout.py` validates the F1+F2+F3 bundle: README exists, the pyproject readme path
resolves, `python -m kurort_engine --help` works, the demo prints operator-visible output, and
the `[project.scripts]` CLI binary entry is declared.

**Known issues when running the suite:**

- Three tests shell out to `pytest tests/` over the whole suite, which re-collects those same
  tests and recurses until killed — `test_repo_layout.py::test_ac6_full_pytest_suite_exits_zero`,
  `test_audit_isolation.py::test_ac2_full_suite_exits_zero`, and
  `test_predicate_filing_2026.py::test_ac5_full_test_suite_113_baseline_plus_5_new_passes_118_of_118`.
  Deselect them for a clean run.
- `test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback` passes in
  isolation but fails in a full run: `AuditLog._shared_entries` leaks state across tests.
  See `attic/repros/repo/005_audit_shared_state_pollution.py`.

## Key Modules

| Subpackage | Purpose |
|------------|---------|
| `kurort_engine.rates` | `Satzung`, `RateBand`, `load_profile` — Hessen Bad Orb Satzung profile loader |
| `kurort_engine.calculator` | `Guest`, `Reservation`, `calculate_kurtaxe_for_reservation` — per-reservation tax calculation |
| `kurort_engine.reporting` | `generate_monthly_remittance_csv` — Hessen KAG monthly remittance CSV export |
| `kurort_engine.rechnung` | `build_badekur_rechnung` — §23 SGB V Badekur prescription invoice |
| `kurort_engine.audit` | `AuditEntry`, `AuditLog` — append-only audit log |
| `kurort_engine.exemptions` | `Exemption` — geschaeftsreisender / schwerbehindert_100 exemption handling |
| `kurort_engine.meldeschein` | §29 BMG Meldeschein + AVV validation + BFSG scanner input |
| `kurort_engine.kurpaket_*` | Q5.7 Kurpaket orchestrator + templates + guest card + pricing + compliance |
| `kurort_engine.kurkarte_wallet` | Q5.3 Kurkarte digital wallet (Apple PKPass + Google Wallet) |
| `kurort_engine.predicate_filing` | Hessen Heilbad predicate filing + 2026 narrow Satzung validator |
| `kurort_engine.esg` | Q5.1 ESG/CSRD voluntary VSME + HCMI Scope 1+2 |
| `kurort_engine.ev_charging` | Q5.2 EV charging (e-bike / e-auto) with BFSG-AA compliance |
| `kurort_engine.kurgaste_retention` | DSGVO Art. 17 cascade + Art. 9 health-data audit |
| `kurort_engine.spa_wellness` | Spa/wellness resource management + Toskana Therme partner |
| `kurort_engine.demos` | Synthetic Bad Orb month demo (operator-facing entry) |
| `kurort_engine.profiles` | YAML Satzung profiles (Hessen Bad Orb, Bayern, etc.) |

## Accessibility Tenants

### BFSG-EAA Self-Attestation (`a11y.guest_pwa`)

`kurort_engine.a11y.guest_pwa` ships a BFSG-EAA Section 3(1) self-attestation tenant for the
Hotel Rheinland Bad Orb guest PWA booking flow. It self-attests WCAG 2.1 AA + EN 301 549
V3.2.1 conformance without external Lawyer or certification body dependency (Mix B SAFE per
iter-2 verdict Section 3 Pillar 1).

**Module surface:**

- `SELF_ATTESTATION_TS` — `"2026-07-10"` constant (ISO-8601 date).
- `run_wcag_aa_audit(html_or_url)` — axe-core CLI subprocess with manual fallback.
- `BFSGComplianceError` — domain error for unhandled axe-core failures.
- `__main__:main` — PEP 338 CLI entry point (`python -m kurort_engine.a11y.guest_pwa`).
- CLI binary `guest-pwa` (after `pip install -e ".[dev]"`).

**Pattern F chain extension:** `audit` + `kurkarte_wallet` + `meldeschein` + `f5_t2` (4 SHIPPED
anchors, AC-4). Resavio 2026-Q4 BFSG-AA parity asserted NEGATIVE (AC-5).

```bash
python -m kurort_engine.a11y.guest_pwa --help
guest-pwa --version
```

**Audit log:** every import and CLI invocation appends one entry to the SHIPPED
`kurort_engine.audit.AuditLog` with `actor="a11y.guest_pwa"` or `actor="a11y.guest_pwa.cli"`
and `payload.event` in `{"self_attestation", "wcag_aa_audit", "cli_invocation"}`.

See `spec/a11y_guest_pwa/spec.yaml` for the full 5 EARS-format ACs.

### BITV 2.0 Disclosure (`a11y.guest_pwa.bitv20`)

`kurort_engine.a11y.guest_pwa.bitv20` extends the SHIPPED `bfsg-eaa-guest-pwa-accessibility`
tenant with the Kurort-vertical BITV 2.0 (Barrierefreie-Informationstechnik-Verordnung 2.0)
`Barrierefreiheitserklaerung` disclosure for the guest PWA booking flow (Meldeschein check-in,
Kurkarte wallet, EV charging, spa/wellness).

**Public entry points:**

- `BITV20_TS_ISO8601` / `BITV20_DISCLOSURE_VERSION` — constants.
- `get_bitv20_conformance_statement()` — 5-section German Konformitaetserklaerung
  (Geltungsbereich, Stand der Vereinbarkeit, Nicht barrierefreie Inhalte, Erstellung dieser
  Erklaerung, Feedback-Mechanismus).
- `render_bitv20_disclosure_pdf(out_path)` — hand-crafted byte-blob PDF (`b"%PDF-1.4\n..."`
  magic, mirroring the meldeschein byte-blob pattern).
- `apply_bitv20_footer_to_pdf(existing_pdf, footer)` — appends a `%% BITV20-footer:` comment
  block before any `%%EOF`, preserves the `b"%PDF-"` prefix byte-identical, returns new bytes.

Re-exported ADDITIVELY from `kurort_engine.a11y.guest_pwa` alongside the SHIPPED WCAG 2.1 AA /
EN 301 549 V3.2.1 re-exports. Resavio 2026-Q4 lacks full BFSG-AA `Barrierefreiheitserklaerung`
parity; `kurort_engine` asserts NEGATIVE parity.

See `spec/a11y_guest_pwa_bitv20_disclosure/spec.yaml` for the binding 5 EARS-format ACs.

## Repository Layout

| Path | Contents |
|------|----------|
| `src/` | Package source — `kurort_engine` and `channel_manager_minstay` |
| `tests/` | Test suite (177 tests, 42 files) |
| `spec/` | Binding EARS-format acceptance criteria per feature, with lock files |
| `docs/` | Design notes and UI research |
| `attic/` | Unreconciled files from the originating agent workspace — not imported, not collected, safe to delete. See `attic/README.md` |

## License

Proprietary — All Rights Reserved. See the [LICENSE](LICENSE.txt) file for details.

## Contact

[Github](https://github.com/Knaeckebrothero) <br>
[Mail](mailto:OverlyGenericAddress@pm.me) <br>
