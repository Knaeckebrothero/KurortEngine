# F3 verification — inherited main issue

The exact full-suite gate exits 1 at `tests/test_demo.py::test_ac11_demo_synthetic_bad_orb_month_produces_reproducible_csv`: generated CSV uses CRLF while the fixture comparison expects LF. The dependent `tests/test_repo_layout.py::test_ac6_full_pytest_suite_exits_zero` also fails because its child suite sees that same assertion.

Attempted: all four exact AGENTS gates with real embedded Postgres; the exact full command reports **1 failed, 293 passed, 2 deselected**. A stable supplemental run with `--maxfail=0` reports **2 failed, 421 passed, 8 skipped, 2 deselected**; the only two failures are the above known main tests. No F3 test fails. Required app suite: **242 passed**; ruff check and format: exit 0.

Integrator update (2026-10-18): this is already fixed on main in `83b0992`; do not modify these files, note it in the PR and accept the gate when everything else passes. The branch remains based on the requested original main revision, so it does not cherry-pick an engine/test fix outside F3. Both raw failing exits are disclosed rather than relabelled as exit 0.

Instead: finish the platform, preserve all tests, capture the demo screens, and publish the F3 PR under this explicitly accepted inherited-gate exception. No unresolved F3 execution blocker remains.
