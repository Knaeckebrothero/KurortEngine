# attic — unreconciled files from the agent workspace

Nothing here is imported by `src/`, collected by `tests/`, or packaged by
`pyproject.toml` (`testpaths = ["tests"]`, `packages = ["src/kurort_engine"]`).
It is kept only so the extraction from the Gitea project repo is lossless.

**You can delete this whole directory** once you have looked it over. Everything
in it also still exists in the Gitea repo `srw/project-68137e29-jobs`, branch
`main`, at commit `098bf3fe`.

## Why these files exist

The agents that built this project worked in a shared workspace where the
project source lived under `repo/`. A shell-CWD bug (fixed 2026-08-01 in
`f41970ae`; see `docs/issues/shell_cwd_drifts_and_the_anchor_is_unreachable.md`
in the Superhuman-Remote-Worker repo) meant `run_command`/`shell_execute` kept
a drifting working directory while `write_file` resolved from the workspace
root. Same relative path, two different destinations.

The result: some files were written to the workspace root instead of `repo/`,
and in places to a nested `repo/repo/`. Those copies were never reconciled.

## Contents

### `workspace-root/src/` — parallel implementation of `q64_checkout`

Written in the **same commit** as `repo/src/.../q64_checkout/` (loop iter 6,
2026-07-14 09:55:03, PR #99) but with different content — two attempts at the
same spec landing in two places.

The `repo/` version is canonical: it is what `tests/` targets, it has 7 modules
to this copy's 5, and it kept evolving afterwards. The one file here with no
counterpart, `f5_q64_checkout.py`, is **not** missing work — in the canonical
tree `f5_q64_checkout` is a namespace object built in `checkout_form.py`
(`f5_q64_checkout = _F5Q64Checkout()`) and re-exported from `__init__.py`,
which is the shape the tests assert against.

`channel_manager_minstay/__init__.py` here is stale: last written 2026-07-03,
against a canonical copy last written 2026-07-26. Its own todo text reads
"Update `repo/src/channel_manager_minstay/__init__.py`" — the drift bug caught
in the act.

### `workspace-root/spec/`, `workspace-root/spec.yaml`, `workspace-root/spec_lock.md`

Root-level spec copies that diverge from `spec/`:

- `spec/avv_kaskade/ac_trace_matrix.md` — differs from the canonical copy, same
  commit date (2026-07-09).
- `spec/p1_predicate_filing_2026_fix_axis/spec.yaml` — 2026-07-12, superseded by
  the canonical 2026-07-14 copy.
- `spec.yaml` + `spec_lock.md` — the workspace-root "active spec" pair for the
  F-12 systemic-import-failure fix bundle (iter-3, branch `job/0550d87c`),
  2026-07-26. Process state, not a project spec.

One root spec was **not** atticked: `spec/f5_residual_bug_fix/` was promoted into
`spec/` because `tests/test_f5_residual_bug_fix.py:3` names it as its contract
and no copy existed under `repo/spec/`.

### `workspace-root/head_version.py`

A red-phase test for AC-5 (Badekur Rechnung layout, §23 SGB V) written to the
workspace root on 2026-06-27 instead of `tests/`. Superseded by
`tests/test_rechnung.py`.

### `repros/` — bug reproduction scripts (the most promotable thing here)

13 standalone repro scripts written against this codebase, each naming the
contract it violates and, in several cases, the sha256 of the PROTECTED spec
block it was derived from. They were emitted as job output (`output/repros/`),
never wired into `tests/`.

These are worth promoting into the project proper if you want them — they are
real engineering artifacts, not scratch. In particular
`005_audit_shared_state_pollution.py` documents the live defect that makes
`tests/test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback`
pass in isolation but fail in a full-suite run (`AuditLog._shared_entries`
leaks across tests).

Split by where they were written, because the two copies of `005` differ:

- `repros/workspace-root/` — 11 scripts from the workspace root `output/repros/`
- `repros/repo/` — 2 scripts from `repo/output/repros/` (`005`, `006`)

### `nested-repo-spec/`

From `repo/repo/spec/` — the doubly-nested drift path. Content differs from the
canonical `spec/p1_predicate_filing_2026_fix_axis/`, and `spec.lock.md` (dot
spelling) has no canonical counterpart under that name.
