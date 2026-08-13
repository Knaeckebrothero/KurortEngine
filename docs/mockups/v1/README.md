# v1 UI mockups

Twenty-two standalone HTML screens for the staff-facing ERP, produced
2026-07-17. They are **design artefacts, not an implementation** — no build
step, no framework, no backend. Each file is fully self-contained (inline CSS
and JS, no external requests of any kind), so opening one in a browser is the
whole workflow:

```bash
xdg-open docs/mockups/v1/today_front_desk_dashboard.html   # Linux
open      docs/mockups/v1/today_front_desk_dashboard.html   # macOS
```

They came out of a design pass that was not completed; the screens themselves
survived and are worth keeping, which is why they live here rather than in the
code tree.

## Screens

**Start here** — `today_front_desk_dashboard.html` is the shift-opening view the
other screens hang off, and `design_system_components.html` is the component
inventory the rest are built from.

| Area | Screens |
|---|---|
| Shell | `application_shell_command_palette.html`, `login.html` |
| Front desk | `today_front_desk_dashboard.html`, `operational_alert_detail.html` |
| Arrivals / departures | `arrivals_queue.html`, `departures_queue.html` |
| Check-in flow | `checkin_overview.html`, `checkin_guest_details.html`, `checkin_meldeschein.html`, `checkin_kurtaxe_exemptions.html`, `checkin_kurkarte.html`, `checkin_document_review_completion.html` |
| Reservations | `new_reservation.html`, `reservation_detail.html`, `reservation_search_results.html`, `room_planning_calendar.html` |
| In-house | `inhouse_stay_detail.html`, `guest_profile.html` |
| Design system | `design_system_components.html` |
| Theme studies | `theme_contemporary_hospitality.html`, `theme_modern_kurort_hospitality.html`, `theme_operational_clarity.html` |

The check-in sequence is the one that maps directly onto shipped modules —
`checkin_meldeschein` to `kurort_engine.meldeschein` (§29 BMG),
`checkin_kurtaxe_exemptions` to `kurort_engine.exemptions`, and
`checkin_kurkarte` to `kurort_engine.kurkarte_wallet`.

## Relationship to the UI research

[`docs/ui-research/hotel-erp/`](../../ui-research/hotel-erp/README.md) is a
separate, earlier package: written *research* — surface maps, pattern synthesis
and three costed UI ideas — from a different effort. These mockups are drawn
screens. Neither supersedes the other, and they were not produced together, so
expect them to disagree. Where they do, the research states its evidence
anchors and the mockups do not.

## Caveats

- All data shown is invented. No screen is wired to `kurort_engine`.
- Three theme studies present competing visual directions. None was chosen.
- `Archive.zip` shipped alongside these in the source folder and was dropped:
  it was a byte-identical copy of the same 22 files.
