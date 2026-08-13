# Provenance

Extracted 2026-08-13 from the shared development repository this project used
before it had one of its own, at commit `7e00f47a` (last commit 2026-08-08).

That repository held 8,747 files / 150 MB and mixed four unrelated things:
the product, a knowledge base, scratch files, and committed virtualenvs. This repository is the product only — 179 extracted files / 2.1 MB,
plus the v1 UI mockups under `docs/mockups/v1/`.

## What was taken

| from (source repo) | to (here) | files |
|---|---|---|
| `repo/src/` | `src/` | 96 |
| `repo/tests/` | `tests/` | 48 |
| `repo/spec/` | `spec/` | 18 |
| `repo/docs/` | `docs/` | 12 |
| `repo/pyproject.toml`, `repo/README.md` | root | 2 |

`repo/` was already the package root — proper hatchling `pyproject.toml`
with `packages = ["src/kurort_engine"]` and `testpaths = ["tests"]` — so the
extraction is `repo/` minus the detritus, not a re-layout.

## What was deliberately left behind

| path | files | why |
|---|---:|---|
| `knowledge/` | 3,138 | a knowledge base, kept separately; not product code |
| `repo/.venv/`, `repo/repo/repo/.venv/` | 2,016 | committed virtualenvs, 76 MB, three nesting levels |
| `knowledge_iter6_check/` | 664 | a stray duplicate copy of the knowledge base |
| `archive/` | 1,241 | loop archive |
| `documents/external/` | 586 | external reference material |
| `.subagents/` | 238 | tooling scratch |
| `output/`, `retros/`, `notes/`, `tools/`, `skills/`, `tmp/`, `.worktrees/` | 623 | loop bookkeeping and scratch |
| 39 loose `*.txt` at the repo root | 39 | shell scratch that got committed |

## The two divergent code trees

The source repo carried `kurort_engine` in two places. They are not copies:

- `repo/src/kurort_engine/` — last touched **2026-07-28**, 14 subpackages, 88 files. **Authoritative — this is what
  became `src/` here.**
- `src/kurort_engine/q64_checkout/` (jobs-repo root) — last touched
  **2026-07-14**, 5 files. A stale fork written to the wrong path by an
  earlier developer turn; `repo/src/.../q64_checkout/` has since grown
  `checkout_form.py`, `gutschein.py` and `gutschein_ledger.py` past it.
  Same for `src/channel_manager_minstay/` (1 file, 07-03) vs
  `repo/src/channel_manager_minstay/` (8 files, 07-26).

The stale tree is **not** in this repository. It is kept outside it, in the
separate working copy, rather than discarded, because it holds one module with no
counterpart here —
`q64_checkout/f5_q64_checkout.py`, whose private helpers
(`_load_meldeschein_form`, `_is_german_guest`, `_build_checkout_form_de`,
`_build_checkout_form_foreign`) appear nowhere in the authoritative tree.
Its public `checkout()` entry point *does* exist in
`src/kurort_engine/q64_checkout/__init__.py`, so this is most likely
superseded work rather than lost work — but that was not verified line by
line, so it was kept.

## Verified state of the extracted suite (2026-08-13)

Clean `python -m venv` + `pip install -e ".[dev]"`, then the full suite.

| condition | result |
|---|---|
| as extracted, no venv in the repo | 169 passed, 8 failed |
| with a venv at the repo root (`.venv/`) | 174 passed, 3 failed — after **604 s** |
| after the AC-6 recursion fix (2026-08-13) | **177 passed, 2 failed in ~10 s** |

179 tests. The package imports and both console entry points (`kurort-engine`,
`guest-pwa`) work from the venv PATH with no `PYTHONPATH=src` workaround — which
satisfies most of the in-flight F-12 contract by construction.

### The AC-6 recursion, and its fix

`test_repo_layout.py::test_ac6_full_pytest_suite_exits_zero` shelled out to
`pytest tests/ -q`. That child run re-collected `test_repo_layout.py`, re-entered
AC-6, and spawned again, without limit — **139 nested pytest processes** and a
600 s timeout before the run was killed. It stayed hidden because
`pyproject.toml` sets `addopts = "-x"`, so an inner run aborted at its first
failure, and there was always a failure while the venv assumptions could not
hold. Repairing the suite is what armed it.

Fixed by mirroring the guard that `tests/test_audit_isolation.py` already used:
a `_REPO_LAYOUT_RECURSION_SENTINEL` env var, checked on entry and set in the
child's environment, so a child returns early instead of recursing. Two
regression tests pin both halves — the early return, and the fact that the child
actually inherits the sentinel. Nesting is now bounded at two levels and peaks
around five processes; the full suite runs in ~10 s.

Fixing the recursion exposed a second defect in the same test, previously
unreachable: it asserted `"0 failed"` appears in the summary, but pytest prints
`"N failed, M passed"` only when something failed — an all-green run prints just
`"M passed"`, making the assertion unsatisfiable by a passing suite. Both sites in
`test_repo_layout.py` now accept either spelling. The identical assertion at
`tests/test_audit_isolation.py:222` is still latent — see README Known issues 4.

### Remaining failures

Both trace to one root cause:

1. `test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback` —
   a genuine test-isolation leak: it asserts on `AuditLog._shared_entries`,
   populated by a *different* test, and fails standalone.
2. `test_audit_isolation.py::test_ac2_full_suite_exits_zero` — spawns the suite
   and correctly reports that it is not green, because of (1). Not a defect in
   itself.

## The in-flight F-12 contract was moved out, not carried

`spec.yaml` and `spec_lock.md` were left outside this repository. Three reasons:

- Their paths are written against the old `repo/` layout, so leaving them at this
  repo's root would reinstate the exact convention that caused three developer
  turns to deliver nothing.
- They cannot simply be rewritten: `spec_lock.md` records a SHA-256 of `spec.yaml`
  in its lock metadata, so a path rewrite silently breaks the lock discipline.
- Most of the contract is already satisfied by this extraction (entry points,
  imports, editable install), and its one remaining goal is the one that triggers
  the recursion above.

The restarted loop should author a fresh contract against the measured state
recorded here rather than inherit a stale one.
