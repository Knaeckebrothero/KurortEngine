# KurortEngine

Operator-facing, ERP-grade Kurort-vertical Python package for **Hotel Rheinland
in Bad Orb** (Hessen KAG, Kurbeitragssatzung effective 2020-07-01) — the in-house
replacement for the hotel's third-party Resavio system.

`kurort_engine` covers the Kurort workflows natively: Kurtaxe calculation,
Meldeschein generation, Heilbad predicate filing, DSGVO Art. 17 cascade, Kurkarte
digital wallet, ESG reporting, channel-manager MinStay enforcement, EV charging
and spa/wellness resource management. **83 modules across 15 subpackages**, driven
from `python -m kurort_engine` or the `kurort-engine` binary.

- [Install](#install) · [Run](#run) · [Test](#test) · [Layout](#layout)
- [Subpackages](#subpackages) · [Known issues](#known-issues) · [Provenance](#provenance)

## Context

Hotel Rheinland is a ~33-room Kurort-vertical hotel in Bad Orb, Hessen. It must
comply with the Hessisches Kurortegesetz (HKG), the Kurbeitragssatzung Bad Orb
(effective 2020-07-01), the Hessisches Kommunalabgabengesetz (KAG) for tax
remittance, the Bundesmeldegesetz (BMG) for Meldeschein obligations, and the
Beherbergungsmeldepflicht (§29 BMG).

Beyond replacing Resavio's workflows, the package carries regulatory coverage
Resavio does not: Hessen KAG, BFSG-EAA WCAG 2.1 AA with a BITV 2.0
Barrierefreiheitserklärung, DSGVO Art. 17 cascade, ESG/CSRD voluntary VSME, NIS2
supplier checklist and a DATEV SKR 2027 bridge.

## Install

Python 3.11+. The build backend is hatchling (PEP 621 metadata).

```bash
git clone https://github.com/Knaeckebrothero/KurortEngine.git
cd KurortEngine
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`[dev]` adds `pytest`, `pytest-cov` and `ruff`. After an editable install both
console entry points are on PATH and **no `PYTHONPATH=src` is needed** — if you
find yourself setting it, the install did not take.

## Run

```bash
kurort-engine --help
kurort-engine version
kurort-engine demo

python -m kurort_engine --help                     # equivalent, without the binary
python -m kurort_engine.demos.synthetic_bad_orb_month
python -m kurort_engine.a11y.guest_pwa --help      # also: guest-pwa --help
```

The synthetic demo generates 100 reservations spanning all five Hessen Bad Orb
rate bands and both recognised exemption categories, and writes a byte-for-byte
reproducible CSV to `src/kurort_engine/demos/out/synthetic_bad_orb_<yyyy_mm>.csv`
(period `2025-06`, deterministic seed `random.Random(2025)`).

## Test

```bash
pytest tests/ -q
ruff check src/
```

**179 tests, ~10 s.** Current state: **177 passed, 2 failed** — both tracing to the
single open defect in [Known issues](#known-issues).

Two tests deliberately re-invoke pytest on the whole suite
(`test_repo_layout.py::test_ac6`, `test_audit_isolation.py::test_ac2`). Both are
guarded by environment sentinels so a child run returns early instead of
recursing; nesting stays bounded at two levels and peaks around five processes.
**If you add another suite-level subprocess test, give it the same guard.**

Several tests shell out to `.venv/bin/...` at the repository root, so they only
pass when the virtualenv is created in-tree as `.venv/` exactly as
[Install](#install) describes.

## Layout

```
src/kurort_engine/          the package — 83 modules, 15 subpackages
src/channel_manager_minstay/ Booking.com / HRS MinStay two-way sync
tests/                      42 test modules + fixtures
spec/                       8 locked feature contracts (spec.yaml + spec.lock.md)
docs/mockups/v1/            22 standalone UI mockup screens
docs/ui-research/hotel-erp/ UI research package: surface map, patterns, 3 ideas
docs/PROVENANCE.md          where this code came from and what was left behind
```

`spec/<feature>/spec.yaml` pairs an EARS-format acceptance-criteria contract with
a `spec.lock.md` whose lock metadata records a SHA-256 of the yaml. **Editing a
`spec.yaml` without updating its lock breaks that pairing silently** — see
`spec/avv_kaskade/verify_protected_block.py`.

YAML is first-class content here: the `spec/` contracts, the test fixtures, and
the Satzung/MinStay profiles under `src/**/profiles/` that `profile_loader` reads
at runtime. `.gitignore` deliberately carries no blanket `*.yaml` rule.

## Subpackages

| Subpackage | Purpose |
|---|---|
| `rates` | `Satzung`, `RateBand`, `load_profile` — Hessen Bad Orb Satzung profile loader |
| `calculator` | `Guest`, `Reservation`, `calculate_kurtaxe_for_reservation` |
| `reporting` | `generate_monthly_remittance_csv` — Hessen KAG monthly remittance export |
| `rechnung` | `build_badekur_rechnung` — §23 SGB V Badekur prescription invoice |
| `audit` | `AuditEntry`, `AuditLog` — append-only audit log |
| `exemptions` | `geschaeftsreisender` / `schwerbehindert_100` handling |
| `meldeschein` | §29 BMG Meldeschein + AVV validation + BFSG scanner input |
| `kurpaket_*` | Kurpaket orchestrator, templates, guest card, pricing, compliance |
| `kurkarte_wallet` | Kurkarte digital wallet (Apple PKPass + Google Wallet) |
| `predicate_filing` | Hessen Heilbad predicate filing + 2026 narrow Satzung validator |
| `esg` | ESG/CSRD voluntary VSME + HCMI Scope 1+2 |
| `ev_charging` | EV charging (e-bike / e-auto) with BFSG-AA compliance |
| `kurgaste_retention` | DSGVO Art. 17 cascade + Art. 9 health-data audit |
| `spa_wellness` | Spa/wellness resource management + Toskana Therme partner |
| `avv_kaskade` | AVV processor-chain cascade |
| `q64_checkout` | Checkout form, departure Meldung, commission split, Gutschein ledger |
| `a11y.guest_pwa` | BFSG-EAA WCAG 2.1 AA self-attestation + BITV 2.0 disclosure |
| `profiles` | YAML Satzung profiles (Hessen Bad Orb, Bayern) |
| `demos` | Synthetic Bad Orb month demo |

### `a11y.guest_pwa`

Self-attests WCAG 2.1 AA + EN 301 549 V3.2.1 conformance for the guest PWA
booking flow without an external certification dependency. Surface:
`SELF_ATTESTATION_TS`, `run_wcag_aa_audit(html_or_url)` (axe-core subprocess with
a manual fallback), `BFSGComplianceError`, and a `guest-pwa` CLI. Every import and
CLI invocation appends an entry to `kurort_engine.audit.AuditLog`.

Its `bitv20` submodule adds the German BITV 2.0 Barrierefreiheitserklärung:
`get_bitv20_conformance_statement()` returns the five-section
Konformitätserklärung, `render_bitv20_disclosure_pdf()` writes a hand-crafted PDF,
and `apply_bitv20_footer_to_pdf()` appends a footer while preserving the leading
`%PDF-` bytes. Contracts: `spec/a11y_guest_pwa/spec.yaml` and
`spec/a11y_guest_pwa_bitv20_disclosure/spec.yaml`.

## Known issues

Measured 2026-08-13 on a clean editable install. Full detail in
[`docs/PROVENANCE.md`](docs/PROVENANCE.md).

1. **`tests/test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback`
   leaks state across tests.** It asserts on `AuditLog._shared_entries`, which a
   *different* test populates, so it fails when run standalone. This is the only
   genuine product failure, and it causes the second one:
   `tests/test_audit_isolation.py::test_ac2_full_suite_exits_zero` spawns the
   suite and correctly reports that it is not green. Fix the leak and both go
   green together.
2. **`ruff check` reports 123 findings** (84 auto-fixable). Lint is not wired into
   CI for that reason; `.github/workflows/main.yml` is still the unmodified
   template stub.
3. **Paths inherited from the previous repository layout no longer resolve.**
   This code used to live in a subdirectory of a larger shared repository, and
   references to that layout survived the extraction:

   | pattern | lines | files | where |
   |---|---:|---:|---|
   | `repo/…` | 423 | 67 | `spec/` 201, `tests/` 103, `docs/` 103, `src/` 16 |
   | `output/…` | 211 | 12 | `docs/` 183, `spec/` 28 |

   Nothing executes them, so nothing fails — they are stale prose, comments and
   `test_oracle:` fields. The correction is mechanical (`repo/tests/` → `tests/`,
   `repo/src/` → `src/`), **except** for 70 `test_oracle` paths spread across six
   `spec/*/spec.yaml` files, many inside locked `acceptance_criteria` blocks:
   editing those requires applying the same change to the lock's verbatim copy
   and re-stamping its recorded hashes, per [Layout](#layout).

   The `output/…` references in `docs/ui-research/` are different in kind — they
   are that package's evidence anchors, pointing at material that was never part
   of this repository. Rewriting them would leave claims without support, so that
   package needs a judgement call rather than a search-and-replace.
4. **`tests/test_audit_isolation.py:222` carries a latent unsatisfiable
   assertion.** It asserts `"0 failed" in summary_line`, but pytest prints
   `"N failed, M passed"` only when something failed — an all-green run prints
   just `"M passed"`. It is unreachable today because the returncode assertion
   above it fires first. Fixing issue 1 will expose it. Same one-line fix already
   applied to `test_repo_layout.py`: accept `"0 failed" in tail or "failed" not
   in tail`.

## Provenance

This code was extracted on 2026-08-13 from a shared development repository that
mixed the product with a knowledge base, scratch files and three nested committed
virtualenvs — 8,747 files and 150 MB, of which 179 files and 2.1 MB were the
product. [`docs/PROVENANCE.md`](docs/PROVENANCE.md) records exactly what was
taken, what was left behind, and how the two divergent copies of
`kurort_engine` that existed in that repository were reconciled.

## License

Proprietary — All Rights Reserved. See [LICENSE.txt](LICENSE.txt).

## Contact

[GitHub](https://github.com/Knaeckebrothero) · [Mail](mailto:OverlyGenericAddress@pm.me)
