# F8 verification blocker

## What is blocked

The exact AGENTS full-suite gate does not pass in this workspace. F8 is implemented, but the global verification requirement remains unmet. The failing test is `tests/test_repo_layout.py::test_ac6_full_pytest_suite_exits_zero`, whose nested full pytest process exceeds its existing 600-second deadline. This is not claimed to be a pre-existing failure on main: the main full suite was not reproduced independently.

## What was attempted

Both runs used the unchanged required command and mandatory database mode:

```sh
KURORT_TEST_REQUIRE_DB=1 .venv/bin/python -m pytest -q \
  --deselect tests/test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback \
  --deselect tests/test_audit_isolation.py::test_ac2_full_suite_exits_zero
```

1. With the app gate running concurrently: **1 failed, 553 passed, 8 skipped, 2 deselected, 1 warning in 1245.12s**, exit 1.
2. With no concurrent suite or demo server: **1 failed, 553 passed, 8 skipped, 2 deselected, 1 warning in 1253.96s**, exit 1.

Both fail with:

```text
subprocess.TimeoutExpired: Command '[.../.venv/bin/pytest, tests/, -q]' timed out after 600 seconds
```

The test invokes that child at `tests/test_repo_layout.py:841` with `timeout=600`. The source/test tree remained unchanged during both final runs. Serialization did not resolve the failure, so resource contention is not a confirmed explanation. The precise performance attribution remains unproven. Neither timeout, test assertions, mandatory deselections nor recursion sentinels were altered. No third gate variation was attempted.

Captured evidence is in the job output (not committed): `output/logs/f8-gate-full.log` and `.exit` for the final serialized run; `output/logs/f8-gate-full-concurrent.log` and `.exit` for the prior run. Pytest uses `-x`, so tests after this failure in the outer collection are not verified by this gate; the timed-out child is not claimed to have passed.

## What passed instead

- Required-DB app gate: **388 passed, 1 warning in 626.90s**, exit 0.
- Focused F8 acceptance tests: **12 passed, 1 warning in 44.18s**, exit 0.
- Focused reservation-audit regression: **5 passed, 75 deselected, 1 warning in 24.88s**, exit 0.
- Definition validation: `OK .../inventur.yaml`, exit 0.
- Ruff check: `All checks passed!`, exit 0.
- Ruff format check: `87 files already formatted`, exit 0.
- Real Chromium: 52 screenshots at 1280/390 px, no horizontal overflow, quantity inputs at least 44 px high; recalculation, live sum, HTTP 422 input retention and save/linked-detail interactions pass without JavaScript errors.

The eight existing Helm-render skips reflect missing Helm in this workspace; the changed raw kitchen realm configuration has its own passing test. The two deselections are those mandated by AGENTS, not added F8 exceptions.

## Handoff

Per the task's explicit blocked-work rule, publish the PR with this blocker rather than loosen a test or claim green. Before merging, investigate the nested whole-suite deadline versus full seed/test runtime in the appropriate scope and rerun the exact gate. F8 adds no runtime dependency, migration, regulatory-library change or seed.py modification. F7 supplies the intentionally retained kitchen start target `/apps/haccp`; that separate integration dependency and the unrun live Keycloak/Helm rollout are disclosed in the PR.
