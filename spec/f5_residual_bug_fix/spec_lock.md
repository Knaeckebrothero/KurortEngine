---
title: spec_lock — f5_residual_bug_fix
type: spec_lock
status: active
feature: f5_residual_bug_fix
iteration: 18
phase: 1 (spec)
tdd_phase: spec
spec_source: spec/f5_residual_bug_fix/spec.yaml
spec_sha256: 3b8c2737868dd79afd615b2a4fe7b99d528e948496194967e5bbe3503302915f
ac_block_lines: 96
ac_block_bytes: 4709
ac_block_sha256: 92ef2918d7eb7f09aa482033a2fec66db989afa734a9111e8e35d3d74112e6c3
locked_at: 2026-07-13
locked_by: developer
---

# spec_lock — f5_residual_bug_fix

> **PROTECTED SECTION BELOW.** The fenced YAML block in
> `## Acceptance Criteria` is byte-identical to the canonical AC block in
> `spec/f5_residual_bug_fix/spec.yaml` (the trailing `# ---------------...---`
> divider lines + the `# not_included — explicit scope boundaries…` comment
> block, stopping at the line before `\nnot_included:`). No edit may be
> applied here without first rewriting `spec.yaml` and re-running the
> verify script.

## Provenance

| field | value |
|---|---|
| feature | `f5_residual_bug_fix` |
| intent | Repair the two HIGH-severity user-facing bugs in the F5 receptionist CLI handlers so the Meldeschein intake form accepts English-keyed payloads and the Kurtaxe / remittance handlers persist real data through the SHIPPED calculator and reporting primitives. |
| iteration | 18 |
| role | Developer |
| phase | 1 (spec) |
| tdd_phase | spec |
| spec.yaml path | `spec/f5_residual_bug_fix/spec.yaml` |
| spec.yaml SHA-256 | `3b8c2737868dd79afd615b2a4fe7b99d528e948496194967e5bbe3503302915f` |
| AC block lines | 96 |
| AC block bytes | 4709 |
| AC block SHA-256 | `92ef2918d7eb7f09aa482033a2fec66db989afa734a9111e8e35d3d74112e6c3` |
| baseline pytest | 132 (iter-16 close) — this fix adds 3 tests; full suite must stay green |

## Acceptance Criteria

```yaml
acceptance_criteria:

  # -----------------------------------------------------------------
  # AC-A — Gap A fix (English-key Meldeschein payload acceptance)
  # -----------------------------------------------------------------
  - id: AC-A
    title: meldeschein_english_key_payload_accepted
    category: bug-fix / Gap A
    ears: |
      When the operator submits a JSON-stdin payload to the
      `meldeschein check-in` subcommand that uses the standard
      English-keyed intake form (last_name, first_name,
      date_of_birth, nationality, address, arrival_date,
      departure_date, optional passport_number), the handler
      shall normalise the payload to a MeldescheinForm instance
      whose German BMG §30 field names (familienname, vorname,
      geburtsdatum, staatsangehoerigkeit, anschrift, anreisedatum,
      abreisedatum, ausweis_seriennummer) are populated with the
      corresponding English-keyed values; `render(form)` shall
      then be called and the handler shall exit 0 with stdout
      containing the marker `Meldeschein emitted:`.
    template: event-driven
    test_oracle: tests/test_f5_residual_bug_fix.py::test_meldeschein_handler_accepts_english_keys
    rationale: |
      Closes the KeyError that receptionists hit when they submit
      the standard English-keyed intake form. The fix is
      payload-shape normalisation; the German MeldescheinForm
      dataclass itself is unchanged.
    shas: []
    confidence: high

  # -----------------------------------------------------------------
  # AC-B — Gap B / Kurtaxe fix (calculator pipeline)
  # -----------------------------------------------------------------
  - id: AC-B
    title: kurtaxe_handler_uses_calculator_pipeline
    category: bug-fix / Gap B
    ears: |
      When the operator submits a JSON-stdin payload to the
      `kurtaxe charge` subcommand that carries a reservation_id and
      the SHIPPED Reservation shape (arrival, departure, guests),
      the handler shall call
      `kurort_engine.calculator.calculate_kurtaxe_for_reservation`
      with the Reservation and the Hessen Bad Orb Satzung loaded
      via `kurort_engine.load_profile("hessen", "bad_orb")`, and
      shall print the resulting Decimal formatted as EUR with two
      decimal places alongside the reservation_id; the printed
      amount shall NOT equal an `amount_eur` field echoed from
      the payload.
    template: event-driven
    test_oracle: tests/test_f5_residual_bug_fix.py::test_kurtaxe_handler_uses_calculator_pipeline
    rationale: |
      The current stub echoes a payload field — the printed
      amount is operator-supplied, not derived. After the fix
      the printed amount is the calculator's Decimal output, so
      an operator who submits `amount_eur: 0.01` for a 3-night
      adult stay at the Bad Orb Hauptsaison rate gets the real
      rate × day_count, not 0.01 EUR.
    shas: []
    confidence: high

  # -----------------------------------------------------------------
  # AC-C — Gap B / remittance fix (real CSV data rows)
  # -----------------------------------------------------------------
  - id: AC-C
    title: remittance_handler_emits_real_data_rows
    category: bug-fix / Gap B
    ears: |
      When the operator invokes the `remittance generate`
      subcommand with `--year`, `--month`, and a JSON-stdin
      payload that carries a non-empty list of reservations whose
      `arrival` falls inside the (year, month) window, the
      handler shall pass that list to
      `kurort_engine.reporting.generate_monthly_remittance_csv`,
      and the resulting CSV shall contain the 12-column header
      row followed by at least one data row whose
      `subtotal_eur` column equals the rate_band × day_count for
      the first paying guest.
    template: event-driven
    test_oracle: tests/test_f5_residual_bug_fix.py::test_remittance_handler_emits_real_data_rows
    rationale: |
      The current stub always passes `reservations=[]` so the
      portal gets a header-only file. After the fix, with a
      non-empty in-window reservation stream, the CSV has at
      least one data row whose subtotal reconciles to
      `rate_per_day × day_count` per AC-4 in
      `repo/spec/<iter-12>/spec.yaml` (the spec pinned by
      `kurort_engine/reporting.py:AC4_HEADER_COLUMNS`).
    shas: []
    confidence: high

# ---------------------------------------------------------------------------
# not_included — explicit scope boundaries (per instructions §1).
# ---------------------------------------------------------------------------
# Anything listed here is OUT of this feature. The red/green phases
# may not write tests or code that exercises these.
```
## Traceability Matrix

| AC ID | title | test_oracle | spec section | status |
|---|---|---|---|---|
| AC-A | meldeschein_english_key_payload_accepted | `tests/test_f5_residual_bug_fix.py::test_meldeschein_handler_accepts_english_keys` | spec.yaml:55-79 (`AC-A`) | red |
| AC-B | kurtaxe_handler_uses_calculator_pipeline | `tests/test_f5_residual_bug_fix.py::test_kurtaxe_handler_uses_calculator_pipeline` | spec.yaml:84-109 (`AC-B`) | red |
| AC-C | remittance_handler_emits_real_data_rows | `tests/test_f5_residual_bug_fix.py::test_remittance_handler_emits_real_data_rows` | spec.yaml:114-139 (`AC-C`) | red |

**Matrix state:** 3 / 3 ACs at `red` (Phase 2 RED complete: 3 failing regression tests in `tests/test_f5_residual_bug_fix.py`).
Phase 2 (red) will write each test_oracle under `tests/test_f5_residual_bug_fix.py`
and flip the corresponding row to `red` upon a clean `AssertionError` from pytest.
Phase 3 (green) will flip them to `green` upon pytest exit 0.

## Spec anti-drift anchors

| anchor | value |
|---|---|
| spec.yaml path | `spec/f5_residual_bug_fix/spec.yaml` |
| spec.yaml SHA-256 | `3b8c2737868dd79afd615b2a4fe7b99d528e948496194967e5bbe3503302915f` |
| PROTECTED block SHA-256 | `92ef2918d7eb7f09aa482033a2fec66db989afa734a9111e8e35d3d74112e6c3` |
| PROTECTED block bytes | 4694 |
| PROTECTED block lines | 96 |
| baseline pytest | 132 (iter-16 close) |
| expected post-fix pytest | 132 + 3 = 135 |
| locked_at | 2026-07-13 |
| locked_by | developer |
