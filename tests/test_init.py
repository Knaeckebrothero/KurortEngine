"""AC-6: public API namespace — 9 symbols re-exported, no side effects on import.

Test_oracle path recorded in spec.yaml:117.
This is the red-phase test for AC-6.

Contracts under test (from spec.yaml:107-117 and spec_lock.md:107-117):

  * ``from kurort_engine import <Symbol>`` works for each of the 9 spec-
    mandated public symbols: ``Satzung``, ``RateBand``, ``Reservation``,
    ``Guest``, ``Exemption``, ``calculate_kurtaxe_for_reservation``,
    ``generate_monthly_remittance_csv``, ``build_badekur_rechnung``,
    ``AuditEntry``.
  * Each of those symbols is reachable as an attribute of the package
    itself (``kurort_engine.<Symbol>``) and is the SAME OBJECT as the
    canonical implementation in its submodule.
  * ``kurort_engine`` ships a non-empty ``__version__`` string.
  * Importing ``kurort_engine`` MUST NOT mutate any of:
      - ``sys.stdout`` / ``sys.stderr``
      - ``os.environ``
      - the set of files in the current working directory
      - the set of files anywhere under ``src/kurort_engine/``

Per the AC-6 EARS contract ("the submodule shall not modify any symbol
outside the ``kurort_engine`` namespace, so importing ``kurort_engine``
does not mutate global state, write to stdout, or open files"), the
side-effect check is part of the AC, not an optional add-on.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

import kurort_engine


# The 9 spec-mandated public symbols (AC-6 EARS contract).
AC6_SPEC_SYMBOLS = (
    "Satzung",
    "RateBand",
    "Reservation",
    "Guest",
    "Exemption",
    "calculate_kurtaxe_for_reservation",
    "generate_monthly_remittance_csv",
    "build_badekur_rechnung",
    "AuditEntry",
)

# Submodule pairings for each re-exported symbol (AC-6 EARS contract).
AC6_SUBMODULE_PAIRS = {
    "Satzung": "rates",
    "RateBand": "rates",
    "Reservation": "calculator",
    "Guest": "calculator",
    "Exemption": "exemptions",
    "calculate_kurtaxe_for_reservation": "calculator",
    "generate_monthly_remittance_csv": "reporting",
    "build_badekur_rechnung": "rechnung",
    "AuditEntry": "audit",
}


# ---------------------------------------------------------------------------
# AC-6 master test — name matches spec.yaml:117 test_oracle verbatim
# ---------------------------------------------------------------------------


def test_ac6_public_api_is_import_clean_and_namespaced():
    """AC-6 master contract: 9 symbols re-exported, no import side effects.

    This is the test_oracle named in spec.yaml:117 and spec_lock.md:114.
    It bundles all four sub-contracts into a single assertion surface
    so that ``pytest -k test_ac6_public_api_is_import_clean_and_namespaced``
    can serve as the canonical AC-6 verdict command.

    Sub-contracts (each broken out into its own named test below for
    readable failure messages):

      (a) The 9 spec symbols are importable from ``kurort_engine``.
      (b) Each is the SAME OBJECT as its canonical submodule location.
      (c) ``__version__`` is a non-empty string.
      (d) Importing ``kurort_engine`` does not mutate global state
          (stdout/stderr/env/cwd/src tree).
    """
    # (a) all 9 spec symbols are importable
    for name in AC6_SPEC_SYMBOLS:
        assert name in dir(kurort_engine), (
            f"AC-6 contract violated: {name!r} is missing from "
            f"kurort_engine.__dict__"
        )
        obj = getattr(kurort_engine, name)
        assert obj is not None, f"AC-6 contract violated: kurort_engine.{name} is None"

    # (b) each is the same object as its canonical submodule location
    for name, submodule in AC6_SUBMODULE_PAIRS.items():
        pkg_obj = getattr(kurort_engine, name)
        sub_obj = getattr(getattr(kurort_engine, submodule), name)
        assert pkg_obj is sub_obj, (
            f"AC-6 contract violated: kurort_engine.{name} is NOT the same "
            f"object as kurort_engine.{submodule}.{name}"
        )

    # (c) __version__ is a non-empty string
    v = kurort_engine.__version__
    assert isinstance(v, str), f"AC-6 contract violated: __version__ not str"
    assert v.strip(), "AC-6 contract violated: __version__ is empty"

    # (d) import is side-effect free
    cwd_before = set(os.listdir(os.getcwd()))
    src_dir = Path(kurort_engine.__file__).parent  # type: ignore[arg-type]
    src_before = {str(p) for p in src_dir.rglob("*") if p.is_file()}
    stdout_before = sys.stdout
    stderr_before = sys.stderr
    env_before = dict(os.environ)

    importlib.reload(kurort_engine)

    cwd_after = set(os.listdir(os.getcwd()))
    src_after = {str(p) for p in src_dir.rglob("*") if p.is_file()}
    stdout_after = sys.stdout
    stderr_after = sys.stderr
    env_after = dict(os.environ)

    assert stdout_before is stdout_after
    assert stderr_before is stderr_after
    assert env_before == env_after
    assert cwd_before == cwd_after
    assert src_before == src_after


# ---------------------------------------------------------------------------
# AC-6 (a) — all 9 spec symbols are importable directly from kurort_engine
# ---------------------------------------------------------------------------


def test_ac6_all_nine_spec_symbols_are_importable_directly():
    """Every name in AC6_SPEC_SYMBOLS resolves via ``from kurort_engine import X``.

    Per AC-6 EARS: "expose its public API via a ``kurort_engine/__init__.py``
    re-export list that contains exactly the symbols [...]".
    """
    for name in AC6_SPEC_SYMBOLS:
        assert name in dir(kurort_engine), (
            f"AC-6 contract violated: {name!r} is missing from "
            f"kurort_engine.__dict__. Got: {sorted(dir(kurort_engine))}"
        )
        obj = getattr(kurort_engine, name)
        assert obj is not None, (
            f"AC-6 contract violated: kurort_engine.{name} is None"
        )


# ---------------------------------------------------------------------------
# AC-6 (b) — symbols are reachable via dotted access AND are the SAME object
#             as their canonical submodule location
# ---------------------------------------------------------------------------


def test_ac6_symbols_are_same_object_as_canonical_submodule():
    """Each re-export is the same object as the canonical submodule version.

    This guards against the common bug where an ``__init__.py`` does
    ``from foo.bar import X`` then accidentally re-binds to a copy or
    stub. The AC-6 contract is that the package re-exports the SAME
    object the submodule defines, so callers can use either form
    interchangeably.
    """
    for name, submodule in AC6_SUBMODULE_PAIRS.items():
        pkg_obj = getattr(kurort_engine, name)
        sub_obj = getattr(getattr(kurort_engine, submodule), name)
        assert pkg_obj is sub_obj, (
            f"AC-6 contract violated: kurort_engine.{name} is NOT the same "
            f"object as kurort_engine.{submodule}.{name} "
            f"(pkg={pkg_obj!r}, sub={sub_obj!r})"
        )


# ---------------------------------------------------------------------------
# AC-6 (c) — __version__ is a non-empty string
# ---------------------------------------------------------------------------


def test_ac6_kurort_engine_has_nonempty_version_string():
    """``kurort_engine.__version__`` is a non-empty ``str``.

    Per the AC-6 contract and the standard Python packaging convention,
    a re-export list is meaningless without a release marker. The spec
    pins ``__all__`` semantics (the ``__init__.py`` docstring also
    documents version 0.1.0), so the runtime must agree.
    """
    v = kurort_engine.__version__
    assert isinstance(v, str), (
        f"AC-6 contract violated: __version__ must be str, got {type(v).__name__}"
    )
    assert v, "AC-6 contract violated: __version__ is empty"
    assert v.strip(), "AC-6 contract violated: __version__ is whitespace-only"


# ---------------------------------------------------------------------------
# AC-6 (d) — importing kurort_engine does NOT mutate global state
# ---------------------------------------------------------------------------


def _list_repo_files():
    """Return (cwd_files, src_files) snapshot."""
    cwd_files = set(os.listdir(os.getcwd()))
    src_dir = Path(kurort_engine.__file__).parent  # type: ignore[arg-type]
    src_files = {str(p) for p in src_dir.rglob("*") if p.is_file()}
    return cwd_files, src_files


def test_ac6_importing_kurort_engine_does_not_mutate_global_state():
    """Importing ``kurort_engine`` does not mutate stdout/stderr/env/fs.

    Per AC-6 EARS: "importing ``kurort_engine`` does not mutate global
    state, write to stdout, or open files (other than on explicit user
    request)".

    Strategy: snapshot the four mutation surfaces BEFORE the import,
    perform the import (inside an ``importlib.reload`` so the test is
    self-contained and works even if kurort_engine was already imported),
    then snapshot AFTER and assert equality.
    """
    # Snapshot before.
    cwd_before, src_before = _list_repo_files()
    stdout_before = sys.stdout
    stderr_before = sys.stderr
    env_before = dict(os.environ)

    # (Re-)import. Reload is safe — re-running the module body is exactly
    # what we want to stress-test for side effects.
    importlib.reload(kurort_engine)

    # Snapshot after.
    cwd_after, src_after = _list_repo_files()
    stdout_after = sys.stdout
    stderr_after = sys.stderr
    env_after = dict(os.environ)

    # Assert no mutation.
    assert stdout_before is stdout_after, (
        "AC-6 contract violated: importing kurort_engine replaced sys.stdout"
    )
    assert stderr_before is stderr_after, (
        "AC-6 contract violated: importing kurort_engine replaced sys.stderr"
    )
    assert env_before == env_after, (
        "AC-6 contract violated: importing kurort_engine mutated os.environ. "
        f"Added keys: {set(env_after) - set(env_before)}. "
        f"Changed values: {[k for k in env_before if env_before.get(k) != env_after.get(k)]}."
    )
    assert cwd_before == cwd_after, (
        "AC-6 contract violated: importing kurort_engine changed cwd listing. "
        f"Added: {cwd_after - cwd_before}. Removed: {cwd_before - cwd_after}."
    )
    assert src_before == src_after, (
        "AC-6 contract violated: importing kurort_engine created or deleted "
        "files under src/kurort_engine/. "
        f"Added: {src_after - src_before}. Removed: {src_before - src_after}."
    )