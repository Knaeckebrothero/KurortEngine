# Hotel ERP UI Research Package

This directory preserves the useful output of UI design job
`2dbe6854-8b4f-4c63-9315-f761076cd7e1` and its Scholar subjob
`fe96c4c6`.

The package is **design research, not a frontend implementation**. It maps the
current CLI/module/test-backed Hotel Rheinland ERP to staff-facing UI concepts
and records unsupported contracts that a future implementation must define.

## Recommended starting point

Build a staff-facing **Today at Reception** prototype that combines:

1. the Today Arrivals Artifact Strip; and
2. a compact Kurort Exception Radar.

Use the AVV + Retention Evidence Drawer as a secondary contextual interaction.

## Ideas

- [`ideas/ui_001_today_arrivals_artifact_strip.md`](ideas/ui_001_today_arrivals_artifact_strip.md)
- [`ideas/ui_002_kurort_exception_radar.md`](ideas/ui_002_kurort_exception_radar.md)
- [`ideas/ui_003_avv_retention_evidence_drawer.md`](ideas/ui_003_avv_retention_evidence_drawer.md)

## Supporting research

- [`findings/phase1_ui_pattern_synthesis.md`](findings/phase1_ui_pattern_synthesis.md)
- [`findings/phase1_duplicate_risk_inventory.md`](findings/phase1_duplicate_risk_inventory.md)
- [`findings/ui_surface_map.md`](findings/ui_surface_map.md)
- [`findings/phase5_ui_idea_evidence_anchors.md`](findings/phase5_ui_idea_evidence_anchors.md)
- [`coverage_report.md`](coverage_report.md)

## Verification records

- [`findings/phase7_artifact_verification.md`](findings/phase7_artifact_verification.md)
- [`findings/phase7_final_verification.md`](findings/phase7_final_verification.md)

## Important caveats

The research found no existing browser frontend/API, durable persistence model,
or authentication/authorization model. Evidence labels such as `CLI-backed`,
`test-contract-backed`, `preview-only`, `stub-shaped`, and
`requires new API contract` must remain meaningful until those contracts exist.

The historical job's stale `completion.json` and unrelated accumulated project
outputs were intentionally not imported.
