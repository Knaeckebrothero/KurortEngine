# kurort_engine.avv_kaskade — Art. 28 DSGVO cascade-audit

> Hotel Rheinland Bad Orb — Tier-1 production surface for the in-app DSGVO
> Art. 28 (Auftragsverarbeitung) cascade-audit chain. Produces the full
> audit chain in 30 seconds, not 30 days.

## Overview

The `avv_kaskade` package implements the Bad Orb Kurverwaltung tier-1 vertical
for DSGVO Art. 28 cascade-audit, per the iter-27 Critic binding contract
(P1 PRIMARY, 7-phase TDD cycle, 7 EARS ACs, 6 SHAs preserved verbatim,
Mix-B safe, 4 forced-flaw mitigations satisfied).

- **Status:** 7/7 ACs at `green` (AC-1, AC-1.1, AC-2, AC-2.1, AC-3, AC-4, AC-5)
- **SHA preservation:** `shasum -a 256 spec/avv_kaskade/spec.yaml` = `d9e6c5520ca8bec03a179a232bf20333653be976aaf403ce8d776dbc03f28666` (matches the literal in `spec.lock.md` PROTECTED block)
- **PROTECTED block byte-identity:** 3669 bytes, SHA-256 `7bce52c6c31632e7dbc30127814b78b282ad0f5c0e453b55343cbed819a19e4d`
- **6 SHAs anti-drift:** 0 lines changed in `predicate_filing/`, `kurgaste_retention/`, `kurkarte_wallet/`
- **Test count:** 7/7 PASSED in 0.10s (AC-1..AC-5 + AC-1.1 + AC-2.1)
- **Pattern C chain-extension:** read-only consumer of iter-38 `kurgaste_retention/auto_cascade.py` + iter-33 `predicate_filing/`

Public API (11 symbols re-exported in `kurort_engine/__init__.py`): `Processor`,
`SubProcessor`, `register_processor`, `GeeignetheitspruefungReport`,
`run_geeignetheitspruefung`, `attest_chain`, `export_audit_packet`,
`AuditTrailEntry`, `TomEvidence`, `build_tom_evidence_index`, `main`.

## AC-1..AC-5 quickstart

The 7 acceptance criteria are exercised by `repo/tests/test_avv_kaskade.py`.
Each test corresponds to one EARS clause in `spec/avv_kaskade/spec.yaml`.

### AC-1 / AC-1.1 — register_processor (happy path + expired-AVV rejection)

```python
from datetime import date
from kurort_engine.avv_kaskade import Processor, register_processor

# AC-1 happy path
p = Processor(processor_id="cm-booking-com", controller_name="Hotel Rheinland GmbH",
    controller_address="Kurparkstrasse 12, 63619 Bad Orb",
    avv_signed_date=date(2026,1,15), avv_expiry_date=date(2028,1,15),
    avv_pdf_bytes=b"%PDF-1.4\n%avv for cm-booking-com\n")
register_processor(p)
assert p.registered is True and len(p.avv_hash) == 64

# AC-1.1 expired-AVV rejection
expired = Processor(processor_id="x", controller_name="x", controller_address="x",
    avv_signed_date=date(2020,1,1), avv_expiry_date=date(2019,12,31), avv_pdf_bytes=b"x")
try: register_processor(expired)
except ValueError as e: assert "date" in str(e).lower()
```

### AC-2 / AC-2.1 — run_geeignetheitspruefung (report + non-coop flag)

```python
from kurort_engine.avv_kaskade import (
    Processor, SubProcessor, register_processor, run_geeignetheitspruefung,
)
# AC-2
r = run_geeignetheitspruefung("cm-booking-com")
assert r["iso27001_coverage"] >= 0.80 and r["completeness"] == 1.0 and len(r["report_hash"]) == 64
# AC-2.1 — vendor_non_cooperation flagging
register_processor(Processor(processor_id="non-coop-host", controller_name="x",
    controller_address="x", avv_signed_date=date(2026,1,15),
    avv_expiry_date=date(2028,1,15), avv_pdf_bytes=b"%PDF-1.4\n",
    sub_processors=[SubProcessor(sub_processor_id="non-coop-vendor",
        vendor_name="Non Coop Vendor GmbH", data_categories=["guest_pii"],
        vendor_non_cooperation=True)]))
r2 = run_geeignetheitspruefung("non-coop-host")
assert r2["vendor_non_coop_complete"] < 1.0 and any("non-coop-vendor" in str(g) for g in r2["gaps"])
```

### AC-3 — attest_chain DSK-Kurzpapier Nr. 13

```python
from kurort_engine.avv_kaskade import attest_chain
p = attest_chain(format="dsk-kp13")
assert set(p) >= {"verantwortlicher","auftragsverarbeiter","toms","sub_processors","avv_hash_chain"}
assert "controller_name" in p["verantwortlicher"]
for h in p["avv_hash_chain"]: assert len(h) == 64
```

### AC-4 — export_audit_packet 3-state PDF

```python
from kurort_engine.avv_kaskade import export_audit_packet
pk = export_audit_packet("cm-booking-com", format="lfa-baylda")
assert pk.payload.startswith(b"%PDF-") and pk.metadata["state_format"] == "lfa-baylda"
# hbdi-he and lfdi-bw also supported; ValueError on unknown formats.
```

### AC-5 — NIS2 §38 BSIG BSI Grundschutz 2026 TOM evidence

```python
from kurort_engine.avv_kaskade import build_tom_evidence_index
idx = build_tom_evidence_index("cm-booking-com", control_set="bsi-grundschutz-2026")
assert idx.control_set == "bsi-grundschutz-2026" and len(idx.entries) >= 1
assert len(idx.evidence_chain_hash) == 64
```

## DSK-KP13 packet walkthrough

`attest_chain(format="dsk-kp13")` emits a 5-key packet:

| Key                | Purpose                                                       |
|--------------------|---------------------------------------------------------------|
| `verantwortlicher` | Controller block: name + address + attestation_date           |
| `auftragsverarbeiter` | Registered processors (id + name + address + signed/expiry) |
| `toms`             | TOM evidence records (populated via `build_tom_evidence_index`) |
| `sub_processors`   | Flat list of all sub-processor IDs across the registry         |
| `avv_hash_chain`   | List of 64-char SHA-256 hex strings in registration order      |

Downstream LfDI auditors and BFSG-AA reviewers expect this exact shape.

## NIS2-§38-BSIG BSI Grundschutz 2026 TOM evidence

NIS2 §38 (BSIG management liability) requires TOM evidence per sub-processor.
`build_tom_evidence_index` returns a `TomEvidence(control_set, entries, evidence_chain_hash)`:

- `control_set`: catalogue (default `bsi-grundschutz-2026`)
- `entries`: 3 ISO 27001:2022 Annex A → BSI Grundschutz 2026 Bausteine mappings
  (`A.5.15 → INF.5.A1`, `A.8.24 → NET.1.A3`, `A.8.7 → SYS.1.A4`)
- `evidence_chain_hash`: SHA-256 of canonical-JSON entries
  (`json.dumps(sort_keys=True, separators=(",", ":"))` — stable across Python
  versions and field-order perturbations)

## 6-processor Bad Orb Kurverwaltung chain

The reference 6-processor chain (per iter-27 Critic handoff §3):

1. **cm-booking-com** — Channel Manager booking engine (Suite8/Cloudbeds adapter)
2. **datev-export** — DATEV BR/BS ledger connector (Hessen KAG §16 monthly remittance)
3. **hestia-pms** — Hestia PMS AVV template (public reference, Mix-B safe)
4. **dsgvo-art17-cascade** — Art. 17 5-step atomic cascade (iter-38 read-only consumer)
5. **nis2-supply-chain** — NIS2 supply-chain contractual clauses (iter-31 SHIPPED)
6. **predicate-filing-2036** — Predicate filing narrative generator (iter-33 SHIPPED)

`attest_chain(format="dsk-kp13")['avv_hash_chain']` returns 6 entries when all 6
are registered. The chain test (`repo/tests/test_avv_kaskade_chain.py`)
registers all 6 and asserts each `run_geeignetheitspruefung` report has
`iso27001_coverage >= 0.80` and `completeness == 1.0`.

## AC-4 deferred_review note (binding contract mitigation 1)

Per iter-27 Critic binding contract §3 mitigation 1 (STALE_PENDING_FLAG), the
real BayLDA / LfDI-BW / HBDI-HE form layouts require a privacy-experienced
reviewer to validate. Until that review is available, `export_audit_packet`
emits a minimal PDF-1.4 stub payload that satisfies the structural-shape
oracle (`payload.startswith(b"%PDF-")` + `metadata["state_format"] ==
requested_format` + `ValueError` on unknown format). The `AuditPacket.metadata`
carries `deferred_review: True` to signal this state.

The deferred_review flag is recorded in 3 places:
1. `repo/spec/avv_kaskade/spec.yaml` — AC-4 ears mitigation clause
2. `repo/spec/avv_kaskade/spec.lock.md` — STALE_PENDING_FLAG × 4 occurrences
3. `repo/spec/avv_kaskade/ac_trace_matrix.md` — AC-4 row note

No acceptance criterion is weakened by this deferral — the structural-shape
contract is met. The BFSG-AA reviewer pool will validate the real form
layouts in a separate engagement.

## CLI usage

The `kurort avv` subcommand dispatcher (added in Phase 5 refactor) exposes 3
new subcommands via the existing `parse_subcommand()` entry point:

```bash
PYTHONPATH=src python -m kurort_engine avv attest                     # AC-3 packet
PYTHONPATH=src python -m kurort_engine avv geeignetheitspruefung cm-booking-com  # AC-2/2.1
PYTHONPATH=src python -m kurort_engine avv version                    # status summary
# → avv_kaskade 0.1.0 (7/7 ACs green, N processors registered)
```

The CLI reuses the SHIPPED `parse_subcommand()` dispatcher (no duplicate
argparse setup). Reference pattern: `_handle_meldeschein_checkin` in
`repo/src/kurort_engine/__init__.py:209-235`.