"""kurort_engine.a11y — Kurort-vertical accessibility self-attestation tenant.

Iteration 3 ships ``kurort_engine.a11y.guest_pwa`` as a BFSG-EAA / EN 301 549
V3.2.1 / WCAG 2.1 AA self-attestation tenant per
``spec/a11y_guest_pwa/spec.yaml``. This parent namespace holds the
BFSG-EAA Barrierefreiheitserklaerung evidence surface so the obligation
(general 2025-06-28 / specific-services 2030-06-28) can be evidenced in
5 minutes via the audit-log event on first import of the ``guest_pwa``
sub-package.

The ``guest_pwa`` submodule is intentionally NOT eagerly re-exported here:
AC-1 callers reach it via ``import kurort_engine.a11y.guest_pwa`` (PEP 338
submodule path), and an eager ``from kurort_engine.a11y import guest_pwa``
in the parent init would create a self-referential circular import while
the parent package is still mid-initialization. The submodule is exported
flat at the top level of the submodule itself.
"""