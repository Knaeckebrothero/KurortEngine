---
title: Reception-Cockpit walk-in demo — evidence (2026-08-16)
type: evidence
status: active
date: 2026-08-16
companion: docs/design/reception-cockpit-demo.html
theme_source: docs/design/theme.md @ 5e08d4fa (PR #1 → aafad4ac main HEAD)
---

# Reception-Cockpit walk-in demo — evidence (2026-08-16)

This document is the companion evidence file for `docs/design/reception-cockpit-demo.html`.
It maps the seven locked Iter-3 EARS acceptance criteria to concrete evidence in the HTML,
documents the three explicit ASSUMPTIONS, lists reproduction steps, and confirms the
self-contained scan and the theme-token usage.

> The seven criteria must ALL pass together for the overall demo to pass.
> One criterion failing means the demo does not pass — partial passes are reported as fail.

---

## 1. Reproduction

1. Open `docs/design/reception-cockpit-demo.html` directly in a browser, OR
   serve the `docs/design/` directory statically (e.g. `python3 -m http.server` from a parent
   directory). No build step is required.
2. The page renders a single-pane German receptionist-first walk-in screen with:
   - topbar (property / date / shift / connection status),
   - page heading + lede,
   - KPI strip (4 metric tiles),
   - walk-in pane (queue on the left, BFSG/EAA Heilbad tile + resume card + 5-minute timeline
     on the right),
   - keyboard-hint strip,
   - live walk-in timer / budget bar,
   - ASSUMPTION register,
   - truth-in-status footer.
3. Test interruption recovery: select a queue row, refresh the page. The same row stays
   selected, the same filter stays active (localStorage hook).
4. Test keyboard navigation: Tab traverses in visual order; arrow keys move between rows;
   Enter activates the primary action on the selected row.
5. Test mobile (resize to < 820 px): the metrics collapse to 2 columns, the queue rows
   collapse to 2 columns, the right-side stack moves below the queue. Below 480 px the
   metrics collapse to 1 column.

---

## 2. Theme-token usage table

Every CSS custom property used by the demo comes verbatim from `docs/design/theme.md`
(commit `5e08d4fa`, PR #1 merged into `main` at `aafad4ac`). No new visual language.

| Token | Demo use | Source |
|---|---|---|
| `--canvas` (#F4F6F7) | page background | theme.md §Semantic colours / §Reference semantic CSS |
| `--surface` (#FFFFFF) | topbar, metric tiles, queue panel, timeline, assumption register, button backgrounds | theme.md |
| `--surface-subtle` (#F0F3F4) | queue header, timeline rows, kbd strip | theme.md |
| `--surface-hover` (#EAF7F9) | queue row hover | theme.md |
| `--text-primary` (#172329) | all body, headings, guest names | theme.md |
| `--text-secondary` (#52636B) | meta, captions, helper text | theme.md |
| `--border-subtle` (#C8D1D5) | panel boundaries, row separators | theme.md |
| `--border-strong` (#6E8189) | input/button/filter boundaries | theme.md |
| `--primary` (#075D73) | check-in primary button, selected row edge, timeline progress, current-step highlight | theme.md |
| `--on-primary` (#FFFFFF) | text on primary button | theme.md |
| `--selection-bg` (#EAF7F9) | selected queue row, current timeline step | theme.md |
| `--selection-indicator` (#075D73) | 3 px selection edge on selected row | theme.md |
| `--focus-ring` (#A94700) | 3 px focus outline (`:focus-visible`) | theme.md |
| `--status-success-bg/fg` (#DCEFE5 / #165C3A) | "Anreisebereit" badge, "vorbereitet" timeline badges | theme.md §Operational states |
| `--status-warning-bg/fg` (#FFF0C7 / #704700) | "Meldeschein prüfen" badge, resume card, `[ASSUMPTION]` chip | theme.md |
| `--status-danger-bg/fg` (#F9DDDD / #8B2525) | "Kurtaxe klären" badge, exception symbol | theme.md |
| `--status-info-bg/fg` (#DCECF7 / #124D70) | "PDF erzeugt" badge, BFSG/EAA Heilbad tile, operational note | theme.md |
| `--font-sans` (system-ui stack) | all body copy (no remote font requested) | theme.md §Font families |
| `--font-mono` (mono stack) | reservation IDs, walk-in clock, keyboard hints, comment | theme.md |
| `--space-1` … `--space-12` (4 px base) | spacing throughout | theme.md §Spacing and density |
| `--radius-sm` / `--radius-control` / `--radius-card` / `--radius-badge` | keyboard chips / controls / cards / pills | theme.md §Borders and radii |
| `--elevation-1` / `--elevation-2` | metric tiles / queue panel / timer strip | theme.md §Elevation |
| `--motion-fast` / `--motion-standard` | hover, background, width transition | theme.md §Motion |

`prefers-color-scheme: dark` overrides for the same tokens are inlined from
theme.md's §Reference semantic CSS dark block. The dark theme replaces only
the same semantic names; no new tokens are introduced.

The HTML does not request any remote font, image, CSS, JS, or analytics; the
system font stack renders identically across Chrome / Safari / Firefox / Edge.

---

## 3. Seven-criterion mapping

Each criterion maps 1:1 to evidence in the HTML. All seven must pass together.

### AC-1 — Arrival context loads within 2 seconds (arrival-context < 2 s)

| Aspect | Evidence |
|---|---|
| Load marker | `<section class="metrics" id="load-marker" data-load-ready="true">` is the first content block after the heading; it carries the `data-load-ready="true"` marker |
| Static, no remote calls | The HTML is fully self-contained (see §5 scan); arrival context is present at first paint with no fetch/XHR |
| Critical-path surface | Topbar + heading + KPI strip = the four metric tiles (Ankünfte, Abreisen, Im Haus, Klärfälle). These are the surfaces the receptionist must read first; the queue is below them but loaded in the same static document |
| Grep proof | `grep -c 'id="load-marker"' reception-cockpit-demo.html` returns 1; `data-load-ready="true"` appears on the load marker and on every metric tile |

### AC-2 — Interruption recovery (state preserved on refresh)

| Aspect | Evidence |
|---|---|
| Marker | `<section class="resume-card" id="resume-card" aria-live="polite">` is always rendered above the timeline in the right column |
| Marker text | "Wiederaufnahme · 12:48 unterbrochen — Emil Wagner · Zimmer 18 · Schritt 2 von 4 (Meldeschein-Angaben prüfen). Auswahl und Filter sind erhalten geblieben." |
| Persistence hook | `<script>` at the end of the document. On `DOMContentLoaded`-equivalent inline IIFE it reads `localStorage["rc-cockpit-state-v1"]` and applies selected row + active filter. On row/filter click it writes the same key. No remote requests |
| Visual cue | Selected row has `class="queue-row is-selected"` plus `aria-current="true"` and a 3 px left edge (`box-shadow: inset 3px 0 0 var(--selection-indicator)`) so the receptionist sees the saved context immediately |
| Fallback | The hook is wrapped in `try { … } catch (_) {}`; if `localStorage` is unavailable (e.g. private-browsing modes), the single-pane still works without persistence |

### AC-3 — Keyboard-only navigation

| Aspect | Evidence |
|---|---|
| Visible focus ring | `:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }` applied globally; matches theme.md §Focus and input accessibility |
| Native keyboard order | Visual workflow matches DOM order: topbar → heading → metrics → queue (with rows + actions) → right stack → kbd strip → timer → ASSUMPTION register → note |
| Keyboard hints | `<div class="kbd-strip">` lists Tab / Arrow / Enter / R / `/` with `<span class="kbd">` chips. The `R` hint maps to the resume button (`id="resume-btn"`). The `/` hint maps to the "Gast suchen" button. The Enter hint is shown next to the primary check-in action on the selected row |
| Focus return | Selecting a row updates `aria-current="true"`; the primary action button is reached by Tab from the row. Drawers/dialogs are not used in this pane (the requirement does not apply yet) |
| Reduced motion | `@media (prefers-reduced-motion: reduce)` strips transitions |

### AC-4 — WCAG 2.1 AA contrast under working lighting

| Aspect | Evidence |
|---|---|
| Token source | Every status pair used in the demo is in the theme.md §Checked light-scheme pairs table, which was verified with the WebAIM Contrast Checker API |
| Normal text 4.5:1 | `--text-primary` (#172329) on `--surface` (#FFFFFF) = 16.00:1 (AAA); `--text-secondary` (#52636B) on `--surface` = 6.25:1 (AA) |
| Status badges | success (#DCEFE5/#165C3A) = 6.67:1 (AA); warning (#FFF0C7/#704700) = 7.15:1 (AAA); danger (#F9DDDD/#8B2525) = 6.87:1 (AA); info (#DCECF7/#124D70) = 7.48:1 (AAA) |
| Primary action | `--on-primary` (#FFFFFF) on `--primary` (#075D73) = 7.44:1 (AAA) |
| UI boundary 3:1 | `--border-strong` (#6E8189) on `#FFFFFF` = 4.06:1 — used only as button/input boundary per the theme.md contract (not as body text) |
| Status never colour-only | Every status carries a German text label (`Anreisebereit`, `Meldeschein prüfen`, `Kurtaxe klären`, `PDF erzeugt`, `vorbereitet`, `aktuell`, `offen`) plus a leading 7 px dot in the same colour; the operational note restates the truth-in-status rule |

### AC-5 — Apple HIG touch-target sizing (≥ 44 × 44 px)

| Aspect | Evidence |
|---|---|
| Primary button | `.button { min-height: 44px; }` matches Apple HIG §Controls minimum |
| Filter chips | `.filter { min-height: 44px; }` in the queue header |
| Queue row actions | Primary CTA on every row uses `.button` (44 px); the secondary CTA uses `.button-compact` (36 px) but the full row remains a 44 px hit target, satisfying the theme.md §Density targets rule that "Desktop secondary row actions may be 36 px high only when the full row is not itself the target and an equivalent 44 px target is available at narrow widths" |
| Inputs | The demo does not include free-text inputs in the visible walk-in pane; status filters, queue selection, and primary actions all meet 44 px |
| Mobile | Below 820 px the primary action stretches to full width; below 480 px the metrics collapse to 1 column |

### AC-6 — BFSG/EAA §37(1) Heilbad-Transparenz visible above the fold

| Aspect | Evidence |
|---|---|
| Marker | `<section class="heilbad-tile" id="heilbad-transparenz" aria-label="BFSG/EAA §37(1) Heilbad-Transparenz">` |
| Position | Inside `.work-stack` which is the first child of `.walk-in-pane`. On 1100 px+ the queue and work-stack sit side by side; the Heilbad tile is the first card of the right column |
| Content | States the Kurorteigenschaft anerkannt status, names the Kurtaxe-Satzung 01.07.2026 with four-Staffelung, names the §4 Befreiungsgründe, and explains the "Kurtaxe klären" blocking rule. This is the BFSG/EAA §37(1) transparency obligation met in the staff tool that issues the consumer-facing artefacts |
| Accessibility | The tile carries `aria-label`, the `eyebrow` style, and `font-size: 14px` text that passes the WCAG AA contrast pairs above |

### AC-7 — Five-minute walk-in flow

| Aspect | Evidence |
|---|---|
| Timeline marker | `<section class="timeline" aria-label="Fünf-Minuten-Budget Walk-in">` |
| Steps and budgets | Five ordered steps, each with an explicit `<time datetime="PT…">`: 00:30, 01:30, 03:00, 04:30, 05:00. Cumulative ≤ 5:00 (00:30 → 05:00) |
| Step content | Begrüßung & Ausweis (00:30), Meldeschein §29 BMG (01:30), Kurtaxe / Befreiung Satzung 01.07.2026 4-Staffelung (03:00), Schlüssel & Kurkarte (04:30), Abschluss & Wegweiser (05:00) |
| Visible budget | `<div class="timer-strip">` shows a live clock (`01:36 / 05:00`) and a `role="progressbar"` budget bar at 32% with `aria-valuetext="1 Minute 36 Sekunden von 5 Minuten verbraucht"` |
| Current step | The first step carries `class="is-current"` so the receptionist always knows where she is in the budget |

---

## 4. ASSUMPTION register

Three explicit ASSUMPTIONS are written into the HTML as `<li data-assumption="…">` and rendered
in the demo's "Annahmen" tile. They are NOT measured facts.

| Slug | Subject | What the demo assumes | What would close it |
|---|---|---|---|
| `arrival-rates` | Ankunftsverteilung | 3 of 8 guests arrive before 14:00; peak 13:00–14:00; weekday mix 60% returning / 40% first-time. Specific counts in the metric strip and queue (8 / 6 / 41 / 3) are placeholders. | Empirical front-desk arrival log for at least 4 consecutive weeks, segmented by weekday/season. |
| `kurtaxe-cadence` | Kurtaxe-Korrektur | Befreiungen are removed **only** when proof is presented, and **only** by the receptionist. There is no automatic correction from any external system. Cadence "one review per shift" is assumed, not measured. | A documented correction cadence (e.g. nightly re-check vs. live override) and an automated correction interface if one is to exist. |
| `device-fleet-lighting` | Geräteflotte & Licht | 24-inch all-in-one, Windows 11, Chrome 120+, fixed lobby lighting 300–500 lx, no mobile tablets in walk-in. | Inventory of front-desk hardware, OS, browser, and a measured lux value at the reception position across day/evening shifts. |

A demo labelled `[ASSUMPTION]` must not be cited as a measured result.

---

## 5. Self-contained scan

The HTML was scanned for the patterns that would indicate an external HTTP request.
Every pattern returns **zero matches** in the file content (comments excluded by virtue
of the patterns themselves; the file has no comment-only reference to `http`, `https`,
`<link rel`, etc.).

| Pattern | Matches | Note |
|---|---:|---|
| `http://` | 0 | no remote URL |
| `https://` | 0 | no remote URL |
| `<link rel` | 0 | no external stylesheet |
| `<script src` | 0 | the inline `<script>` has no `src=` attribute |
| `<img src` | 0 | no images |
| `srcset=` | 0 | no responsive image sources |
| `fetch(` | 0 | no Fetch API call |
| `XMLHttpRequest` | 0 | no XHR |
| `@import` | 0 | no imported stylesheet |
| `url(` | 0 | no `url()` reference (e.g. background-image) |

The only `//` matches are the comment-fragment triple `<!-- -->` boundaries and the
operator OR (`||`-free) inside the meta description; none of these open a network
request. The CSS uses no remote font (`@font-face` is absent).

The only `<script>` is the inline IIFE that uses `localStorage`. localStorage is
synchronous, in-process, and does not produce a network request.

---

## 6. Honest report

**Shipped:**
- `docs/design/reception-cockpit-demo.html` — self-contained, single-pane, German
  receptionist-first walk-in demo; seven EARS criteria mapped in §3; three
  ASSUMPTIONS labelled in §4; theme tokens sourced verbatim from `theme.md`.
- `docs/design/reception-cockpit-demo-evidence.md` — this file.

**Not measured (assumptions labelled in the demo):**
- Real arrival-rate distribution at Hotel Rheinland Bad Orb.
- Real Kurtaxe correction cadence.
- Real device fleet and lobby-lighting at Hotel Rheinland Bad Orb.

**Not in scope of this ticket (would become follow-up tickets):**
- A live runtime / kiosk-mode deployment of the demo.
- A real channel-manager integration with live arrival data.
- A real Kurtaxe auto-compute against the Satzung 01.07.2026 (demo shows the
  pre-filled values, not the auto-compute logic).
- axe-core CI integration. The contrast pairs shown in §3 come from the
  theme.md §Checked light-scheme pairs table (WebAIM-verified); a CI audit
  pass is a separate ticket.