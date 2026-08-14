# Rheinland Reception Standard

**Product:** Hotel Rheinland ERP  
**Scope:** staff-facing reception and back-office UI  
**Status:** chosen theme direction

## Direction

**Rheinland Reception Standard** is a light-first, dark-capable operational theme for Hotel Rheinland's roughly 33-room Kurort reception desk. It combines the strongest information patterns from the three v1 studies but does **not** adopt their shared Catppuccin Mocha palette.

The theme is designed for a counter, not a marketing site. Its first tests are whether staff can:

- scan arrival and departure time, guest, room, proof state, blocker, and next action in seconds;
- distinguish “PDF erzeugt” from “unterschrieben” or “übermittelt”;
- work through Meldeschein and Kurtaxe-exemption details while a guest waits;
- read long names such as “Marianne von der Lindenberg-Steinberg” without clipping;
- resume an interrupted check-in without losing the selected guest or filter;
- use the interface in a bright lobby or a lower-light late shift without losing WCAG 2.1 AA contrast.

Hospitality warmth is present in the restrained Rhine blue, Kurpark green, rounded controls, and human German copy. It never displaces the queue or weakens an operational state.

## What was taken and rejected

The three studies use nearly the same dark Catppuccin foundation. Their meaningful difference is information architecture, so this direction synthesises their useful structures and replaces the shared dark-only purple identity.

| Study | Take | Reject |
|---|---|---|
| **Operational Clarity** | Primary structure: compact work rail, queue counts and filters, sticky dense rows, time → guest → room → proof/blocker → one next action, keyboard intent, selected-row context, and focused mobile cards. | Dark-only Catppuccin identity; 10 px persistent headers and 32 px essential targets; proof-taxonomy overload in the main work path; pastel outline colour as the only status cue. |
| **Modern Kurort Hospitality** | Calm shift pacing, per-arrival artefact strips, explicit interruption/resume context, and legally meaningful exceptions tied back to a form or queue row. | Large welcome panels and repeated prose that slow scanning; Kurort character expressed mainly through copy; small uppercase badges carrying too much meaning. |
| **Contemporary Hospitality** | Restrained human tone, selected-guest context during a conversation, and contextual evidence disclosure rather than a separate cockpit. | Service-card prominence that can displace the queue during a busy shift; decorative warmth and oversized hospitality composition; the same purple dark-only identity. |

## Research and mockup reconciliation

The earlier UI research and later mockups were produced separately, but their strongest recommendations converge. The research recommends **Today at Reception** as an arrivals queue with an artefact strip and compact Kurort Exception Radar, with evidence drawers secondary. The dashboard and arrivals mockups test those patterns against a shift-opening view, arrival waves, long names, validation, stale/offline states, interruption, and mobile cards.

Apply that convergence as follows:

- The queue remains the dominant surface; do not make a generic command centre or compliance cockpit.
- Each row keeps time, full guest name, room/stay, proof or blocker, and one next action visible.
- “Erzeugt” never implies submitted, delivered, installed, paid, or legally final. Use text as well as colour.
- Meldeschein and Kurtaxe issues appear as narrow exception states linked to the affected guest.
- Evidence drawers and detail panels are contextual secondary surfaces and must not replace the queue.
- Empty, loading, stale/offline, overflow, interruption, long-name, and validation states are first-class fit tests.
- Role names are navigation/persona language, not claims that authentication or RBAC exists.
- Housekeeping controls are outside this preview because the research found no local room-status backend contract.

## Design principles

1. **Queue first.** Arrival/departure time, guest, room, blocker, and next action form the strongest reading path.
2. **Evidence before decoration.** Regulatory completion and exceptions are text-labelled. Colour reinforces meaning; it never carries meaning alone.
3. **Compact, not cramped.** The default density fits a 33-room operation while preserving 44 px primary targets and clear row boundaries.
4. **German content is the fit test.** Components accept compound labels, long family names, umlauts, and multiline reasons without ellipsis by default.
5. **Calm under pressure.** One primary action per row or work area. Warning and danger are reserved for states that need intervention.
6. **AA is a token constraint.** A semantic token is not accepted for text or an essential indicator until its intended pairing has been calculated.
7. **Truth in status.** Prefer “PDF erzeugt · nicht übermittelt” to a vague green “Fertig”.

# Tokens

## CSS naming model

- Raw ramps use `--color-<family>-<step>`.
- Components consume semantic tokens such as `--text-primary` or `--status-warning-bg`.
- Do not use raw status colours directly in components.
- Light values are the default. Dark values replace the same semantic names inside `@media (prefers-color-scheme: dark)` or an explicit `[data-theme="dark"]` override.

## Colour ramps

Ramps are implementation primitives, not guaranteed text/background pairs. Use the checked semantic combinations below.

### Neutral — cool slate

| Token | Hex |
|---|---|
| `--color-neutral-0` | `#FFFFFF` |
| `--color-neutral-50` | `#F7F9FA` |
| `--color-neutral-100` | `#F0F3F4` |
| `--color-neutral-200` | `#DDE4E7` |
| `--color-neutral-300` | `#C8D1D5` |
| `--color-neutral-400` | `#A5B2B8` |
| `--color-neutral-500` | `#78909A` |
| `--color-neutral-600` | `#52636B` |
| `--color-neutral-700` | `#35464E` |
| `--color-neutral-800` | `#233238` |
| `--color-neutral-900` | `#172329` |
| `--color-neutral-950` | `#0C1519` |

### Rhine — primary action and selection

| Token | Hex |
|---|---|
| `--color-rhine-50` | `#EAF7F9` |
| `--color-rhine-100` | `#D1EFF3` |
| `--color-rhine-200` | `#A8DDE5` |
| `--color-rhine-300` | `#80D1DF` |
| `--color-rhine-400` | `#45B2C5` |
| `--color-rhine-500` | `#1889A0` |
| `--color-rhine-600` | `#0B7088` |
| `--color-rhine-700` | `#075D73` |
| `--color-rhine-800` | `#064B5D` |
| `--color-rhine-900` | `#083A47` |
| `--color-rhine-950` | `#08272F` |

### Kurpark — successful, verified, ready

| Token | Hex |
|---|---|
| `--color-kurpark-50` | `#EFF9F3` |
| `--color-kurpark-100` | `#DCEFE5` |
| `--color-kurpark-200` | `#B9DFC9` |
| `--color-kurpark-300` | `#8FCCAA` |
| `--color-kurpark-400` | `#58AF82` |
| `--color-kurpark-500` | `#348D64` |
| `--color-kurpark-600` | `#23734F` |
| `--color-kurpark-700` | `#165C3A` |
| `--color-kurpark-800` | `#174A32` |
| `--color-kurpark-900` | `#173D2C` |
| `--color-kurpark-950` | `#0C251A` |

### Amber — attention and manual review

| Token | Hex |
|---|---|
| `--color-amber-50` | `#FFF9E8` |
| `--color-amber-100` | `#FFF0C7` |
| `--color-amber-200` | `#FFDC85` |
| `--color-amber-300` | `#F7C64B` |
| `--color-amber-400` | `#DBA520` |
| `--color-amber-500` | `#B78009` |
| `--color-amber-600` | `#8F6000` |
| `--color-amber-700` | `#704700` |
| `--color-amber-800` | `#5B3B08` |
| `--color-amber-900` | `#493710` |
| `--color-amber-950` | `#2C2007` |

### Red — blocked, invalid, failed

| Token | Hex |
|---|---|
| `--color-red-50` | `#FFF1F1` |
| `--color-red-100` | `#F9DDDD` |
| `--color-red-200` | `#FFB5B7` |
| `--color-red-300` | `#EE8B90` |
| `--color-red-400` | `#DB6068` |
| `--color-red-500` | `#C13F49` |
| `--color-red-600` | `#A43139` |
| `--color-red-700` | `#8B2525` |
| `--color-red-800` | `#6E2729` |
| `--color-red-900` | `#4D2426` |
| `--color-red-950` | `#2D1214` |

### Blue — neutral information and generated artefacts

| Token | Hex |
|---|---|
| `--color-blue-50` | `#F0F7FC` |
| `--color-blue-100` | `#DCECF7` |
| `--color-blue-200` | `#B9DAEF` |
| `--color-blue-300` | `#8FC3E2` |
| `--color-blue-400` | `#5AA5CF` |
| `--color-blue-500` | `#3285B5` |
| `--color-blue-600` | `#246C98` |
| `--color-blue-700` | `#1A5A80` |
| `--color-blue-800` | `#124D70` |
| `--color-blue-900` | `#163443` |
| `--color-blue-950` | `#0D202A` |

## Semantic colour tokens

### Core surfaces and interaction

| Semantic token | Light | Dark | Use |
|---|---:|---:|---|
| `--canvas` | `#F4F6F7` | `#10191D` | Page background |
| `--surface` | `#FFFFFF` | `#18252B` | Cards, queue, fields |
| `--surface-raised` | `#FFFFFF` | `#213239` | Menus, drawers, dialogs |
| `--surface-subtle` | `#F0F3F4` | `#233238` | Headers, selected neutral areas |
| `--surface-hover` | `#EAF7F9` | `#213944` | Hover that is not the only signal |
| `--text-primary` | `#172329` | `#EEF4F5` | Body, headings, names |
| `--text-secondary` | `#52636B` | `#B7C6CC` | Metadata and helper text |
| `--text-disabled` | `#6E8189` | `#78909A` | Disabled text only; pair with disabled styling and `aria-disabled`/`disabled` |
| `--border-subtle` | `#C8D1D5` | `#455961` | Non-essential separators only |
| `--border-strong` | `#6E8189` | `#78909A` | Fields and essential component boundaries |
| `--primary` | `#075D73` | `#80D1DF` | Primary action and selected rail |
| `--primary-hover` | `#064B5D` | `#A8DDE5` | Hover |
| `--on-primary` | `#FFFFFF` | `#08272F` | Primary-button text |
| `--selection-bg` | `#EAF7F9` | `#213944` | Selected row background |
| `--selection-indicator` | `#075D73` | `#80D1DF` | 3 px selected-row edge |
| `--focus-ring` | `#A94700` | `#FFB36B` | 3 px focus ring with 3 px offset |
| `--scrim` | `rgb(12 21 25 / 64%)` | `rgb(0 0 0 / 72%)` | Modal backdrop |

`--border-subtle` is a visual separator, not the sole boundary of an interactive control. Inputs, buttons, checkboxes, focus rings, selected edges, and other essential UI use `--border-strong`, `--selection-indicator`, or `--focus-ring`.

### Operational states

| State | Light background | Light foreground | Dark background | Dark foreground | Meaning |
|---|---:|---:|---:|---:|---|
| Success / verified | `#DCEFE5` | `#165C3A` | `#173D2C` | `#A7E4C2` | Required local proof is present |
| Warning / review | `#FFF0C7` | `#704700` | `#493710` | `#FFDC85` | Staff action or manual review required |
| Danger / blocked | `#F9DDDD` | `#8B2525` | `#4D2426` | `#FFB5B7` | Invalid, failed, or action blocked |
| Information / generated | `#DCECF7` | `#124D70` | `#163443` | `#A8D8F0` | Neutral fact, preview, or generated output |

State labels must include a word or concise phrase such as `Anreisebereit`, `Meldeschein prüfen`, `Kurtaxe klären`, `PDF erzeugt`, or `Nicht verbunden`. Do not use a green/amber/red dot without text.

## Typography

### Font families

```css
--font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--font-mono: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
```

No remote font is required. Use the mono stack only for reservation IDs, timestamps, hashes, and technical filenames—not for guest names or general body copy. Enable `font-variant-numeric: tabular-nums` for times, rooms when aligned, money, counts, and dates.

### Type scale

| Token | Size / line height | Weight | Use |
|---|---|---:|---|
| `--text-xs` | `12px / 16px` | 500 | Dense metadata, table labels; never the only presentation of critical instructions |
| `--text-sm` | `14px / 20px` | 400 | Secondary copy, queue metadata |
| `--text-body` | `16px / 24px` | 400 | Forms, notices, general copy |
| `--text-label` | `14px / 20px` | 650 | Field labels, buttons, status labels |
| `--text-section` | `20px / 28px` | 700 | Panel and work-area headings |
| `--text-page` | `28px / 34px` | 750 | Page title |
| `--text-display` | `36px / 42px` | 750 | Rare numeric summary or empty-state title; not routine dashboard decoration |

Weight tokens: `400` regular, `500` medium, `650` label emphasis, `700` strong, `750` page emphasis. If a platform cannot render 650/750 distinctly, fall back to 600/700.

### Content rules

- Guest names use at least `14px / 20px`, weight 700; the selected or next guest may use `16px / 24px`.
- Do not truncate a guest name in a routine queue. Allow two lines with `overflow-wrap: anywhere`. If a genuinely fixed-width view requires ellipsis, expose the full name on focus and in the accessible name.
- Form labels sit above fields. Placeholders never replace labels.
- Uppercase is limited to short eyebrows and table headings. Use at least 12 px and 0.04 em letter spacing.
- German error copy states the problem and next correction: `Befreiungsnachweis fehlt. Nachweis öffnen oder Befreiung entfernen.`

## Spacing and density

The base unit is 4 px.

| Token | Value | Typical use |
|---|---:|---|
| `--space-0` | `0` | Reset |
| `--space-1` | `4px` | Icon/text gap, dense stack |
| `--space-2` | `8px` | Control internals, badge gap |
| `--space-3` | `12px` | Compact row/card padding |
| `--space-4` | `16px` | Standard card padding and grid gap |
| `--space-5` | `20px` | Section internals |
| `--space-6` | `24px` | Page gutters and major groups |
| `--space-8` | `32px` | Large section separation |
| `--space-10` | `40px` | Empty-state internal rhythm |
| `--space-12` | `48px` | Large breakpoint gutter / visual pause |

### Density targets

- Primary buttons, text inputs, selects, and mobile navigation: minimum `44px` block size.
- Desktop secondary row actions may be `36px` high only when the full row is not itself the target and an equivalent 44 px target is available at narrow widths.
- Standard arrival row: `12px 16px` padding, minimum 64 px; grows for wrapped name or blocker copy.
- Dense table cells: `10px 12px`; table text remains at least 12 px, critical body/status text at least 14 px.
- Card and panel gap: 16 px. Page gutter: 24–32 px desktop, 16 px narrow.

## Borders and radii

| Token | Value | Use |
|---|---|---|
| `--border-1` | `1px solid` | Standard boundaries |
| `--border-3` | `3px solid` | Selection, status emphasis, focus-adjacent marker |
| `--radius-badge` | `999px` | Short status pills only |
| `--radius-sm` | `4px` | Keyboard hints and compact tags |
| `--radius-control` | `8px` | Buttons, inputs, filter chips |
| `--radius-card` | `12px` | Cards and panels |
| `--radius-modal` | `16px` | Dialogs and large drawers |

Radii signal a calm hospitality product but remain restrained. Do not turn data tables or full-width queue rows into disconnected pill cards.

## Elevation

Use borders for persistent grouping. Elevation is reserved for content that overlays or detaches from the document flow.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--elevation-0` | `none` | `none` | Inline panels, queue rows |
| `--elevation-1` | `0 1px 2px rgb(23 35 41 / 8%)` | `0 1px 2px rgb(0 0 0 / 28%)` | Dashboard cards |
| `--elevation-2` | `0 4px 16px rgb(23 35 41 / 12%)` | `0 6px 20px rgb(0 0 0 / 36%)` | Sticky command bar, popover |
| `--elevation-3` | `0 12px 32px rgb(23 35 41 / 18%)` | `0 16px 40px rgb(0 0 0 / 48%)` | Dialog and evidence drawer |

Do not use shadows to communicate selected, valid, invalid, or disabled state. Use the semantic border or state tokens.

## Motion

| Token | Value | Use |
|---|---:|---|
| `--motion-fast` | `120ms ease-out` | Hover/focus colour |
| `--motion-standard` | `180ms ease-out` | Drawer and disclosure |
| `--motion-slow` | `240ms ease-out` | Rare page-level transition |

Respect `prefers-reduced-motion: reduce` by removing non-essential transition and animation duration. Do not animate queue reordering without preserving focus and announcing the change.

# Component application

## Application shell

- Desktop work rail: 216–240 px. Collapse to a 64–72 px icon rail only when every icon has an accessible name and the current location remains visible.
- Show property, date, and shift context near the page title; avoid a large welcome hero.
- Current navigation uses background plus a 3 px Rhine indicator and text weight. Colour alone is insufficient.
- Search/command access may show `⌘ K` or `Ctrl K`, but the visible button copy remains `Gast suchen`.

## Summary metrics

- Show only operational counts that change the shift: arrivals, departures, occupied rooms, and blockers.
- A count includes a label and one short qualifier, for example `8 Ankünfte · 3 vor 14:00 Uhr`.
- Do not use status colour for the large number unless the entire card represents a warning or failure.

## Queue rows and tables

Recommended desktop order:

1. time / due window;
2. guest name and reservation ID;
3. room, people, nights;
4. proof state and/or blocker;
5. one visible next action.

Rules:

- Keep the row action visible; never reveal it only on hover.
- Use a 3 px selection edge plus a selection background.
- A warning row remains readable without the warning colour: `Meldeschein prüfen · Unterschrift fehlt`.
- Evidence can say `PDF erzeugt · nicht übermittelt`; never collapse both ideas into `Fertig`.
- Use tabular numerals for time, dates, room numbers in columns, and money.
- Sticky headers are permitted in scrollable dense tables; provide keyboard focus to the scroll area.
- At narrow widths replace the table with task cards, not a horizontally squeezed seven-column row. Preserve time, full name, blocker/status, and primary action.

## Status badges

A badge contains:

- a concise label;
- optional redundant shape/icon or leading dot;
- background and foreground from one checked state pair;
- sentence-case German text unless the label is an acronym.

Use:

- `Anreisebereit` — local required inputs present;
- `Meldeschein prüfen` — action required;
- `Kurtaxe klären` — blocked or legally relevant exception;
- `PDF erzeugt` — output exists, without implying submission;
- `Nicht verbunden` — current external status unavailable.

Avoid: `Fertig`, `OK`, or a colour-only dot when the scope of completion is ambiguous.

## Buttons

- One primary button per row or focused work area.
- Primary: Rhine background with `--on-primary`.
- Secondary: surface background, `--text-primary`, and `--border-strong`.
- Danger buttons are reserved for destructive actions, not routine validation failures.
- Button copy begins with the staff action: `Check-in fortsetzen`, `Nachweis prüfen`, `Fall öffnen`.
- Disabled controls remain labelled and use the native `disabled` attribute. Adjacent copy explains why when the reason is not obvious.

## Fields and dense regulatory forms

- Label above field; optional/required in text when ambiguity exists.
- Input minimum height 44 px and strong border.
- Invalid state uses red border, icon where helpful, `aria-invalid="true"`, and a text message linked with `aria-describedby`.
- Place the error summary before a long Meldeschein form and link to each invalid field.
- Group related values—identity, address, stay, exemption evidence—under short section headings rather than one uninterrupted page.
- Preserve entered data and show the exact blocked next step.
- For Kurtaxe exemption, show reason, proof state, and calculation consequence together.

## Notices and exception radar

- Use a 3 px leading edge, state background, state foreground, heading, and corrective action.
- The dashboard radar contains only current actionable exceptions. Deep AVV/retention evidence belongs in a contextual drawer.
- Warning is not used for neutral generated artefacts; information blue is used for previews and generated-but-not-submitted output.

## Evidence drawer and interruption marker

- Drawers open from a specific guest or artefact and retain the queue's selection/filter context.
- Drawer close returns focus to the trigger.
- Use elevation 3 and `--surface-raised`; do not make the drawer the default dashboard state.
- Interruption markers state guest, current step, saved context, and next action: `Emil Wagner · Schritt 2 von 4 · Fortsetzen`.

## Empty, loading, stale/offline, and overflow states

- **Empty:** retain date/filter context and offer one useful next action. Do not show a celebratory success state.
- **Loading:** use `aria-busy`, keep navigation/context visible, and do not show invented counts.
- **Stale/offline:** show the last verified time and block actions that require fresh data. Do not present old values as live.
- **Overflow/arrival wave:** group by current time window, keep current guests before later arrivals, and state how many items are outside the visible group.

# Accessibility contract

## Thresholds

- Normal text: at least **4.5:1**.
- Large text: at least **3:1** (18.66 px bold or 24 px regular and larger).
- Essential graphical objects and UI component boundaries: at least **3:1** against adjacent colours.
- Status never depends on colour alone.

Ratios below were checked with the WebAIM Contrast Checker API using the listed hex values. Ratios are rounded to two decimals as returned by the checker.

## Checked light-scheme pairs

| Foreground | Background | Ratio | Intended use | Result |
|---|---|---:|---|---|
| `#172329` | `#FFFFFF` | **16.00:1** | Primary text on surface | AAA normal text |
| `#52636B` | `#FFFFFF` | **6.25:1** | Secondary text on surface | AA normal text |
| `#FFFFFF` | `#075D73` | **7.44:1** | Text on primary action | AAA normal text |
| `#165C3A` | `#DCEFE5` | **6.67:1** | Success badge/notice | AA normal text |
| `#704700` | `#FFF0C7` | **7.15:1** | Warning badge/notice | AAA normal text |
| `#8B2525` | `#F9DDDD` | **6.87:1** | Danger badge/notice | AA normal text |
| `#124D70` | `#DCECF7` | **7.48:1** | Information/generated badge | AAA normal text |
| `#6E8189` | `#FFFFFF` | **4.06:1** | Essential border or large disabled text only | Passes 3:1 UI; **not allowed for normal body text** |
| `#A94700` | `#FFFFFF` | **5.85:1** | Focus ring against surface | Passes 3:1 UI |

## Checked dark-scheme pairs

| Foreground | Background | Ratio | Intended use | Result |
|---|---|---:|---|---|
| `#EEF4F5` | `#18252B` | **14.10:1** | Primary text on surface | AAA normal text |
| `#B7C6CC` | `#18252B` | **8.93:1** | Secondary text on surface | AAA normal text |
| `#08272F` | `#80D1DF` | **9.02:1** | Text on primary action | AAA normal text |
| `#A7E4C2` | `#173D2C` | **8.34:1** | Success badge/notice | AAA normal text |
| `#FFDC85` | `#493710` | **8.61:1** | Warning badge/notice | AAA normal text |
| `#FFB5B7` | `#4D2426` | **7.86:1** | Danger badge/notice | AAA normal text |
| `#A8D8F0` | `#163443` | **8.55:1** | Information/generated badge | AAA normal text |
| `#78909A` | `#18252B` | **4.67:1** | Essential border and disabled text | AA normal text and 3:1 UI |
| `#FFB36B` | `#18252B` | **8.90:1** | Focus ring against surface | Passes 3:1 UI |

### Contrast caveats

- `--border-subtle` is deliberately not claimed as a 3:1 component boundary. It is for separators and grouping where shape/spacing already establishes the region.
- Light `--text-disabled` (`#6E8189` on white, 4.06:1) fails 4.5:1 for normal text. It may be used for disabled labels that are at least large-text size, or as an essential border. For small disabled explanatory copy use `--text-secondary` instead.
- Semi-transparent overlays and shadows are not claimed as accessibility indicators.
- Recalculate contrast if a token is placed on a different background, blended with opacity, or changed in implementation.

## Focus and input accessibility

- Every interactive control uses `:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }`.
- Do not remove outlines in favour of a subtle box shadow.
- Native keyboard order follows the visual workflow. Drawers/dialogs manage focus and return it to the trigger.
- Use `aria-live` for asynchronous queue success/error changes, but not for every filter hover or row selection.
- Respect reduced motion and never auto-dismiss an error before staff can read it.

# Reference semantic CSS

```css
:root {
  color-scheme: light dark;
  --canvas: #F4F6F7;
  --surface: #FFFFFF;
  --surface-raised: #FFFFFF;
  --surface-subtle: #F0F3F4;
  --surface-hover: #EAF7F9;
  --text-primary: #172329;
  --text-secondary: #52636B;
  --text-disabled: #6E8189;
  --border-subtle: #C8D1D5;
  --border-strong: #6E8189;
  --primary: #075D73;
  --primary-hover: #064B5D;
  --on-primary: #FFFFFF;
  --selection-bg: #EAF7F9;
  --selection-indicator: #075D73;
  --focus-ring: #A94700;
  --status-success-bg: #DCEFE5;
  --status-success-fg: #165C3A;
  --status-warning-bg: #FFF0C7;
  --status-warning-fg: #704700;
  --status-danger-bg: #F9DDDD;
  --status-danger-fg: #8B2525;
  --status-info-bg: #DCECF7;
  --status-info-fg: #124D70;
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --radius-sm: 4px;
  --radius-control: 8px;
  --radius-card: 12px;
  --radius-modal: 16px;
  --radius-badge: 999px;
  --elevation-1: 0 1px 2px rgb(23 35 41 / 8%);
  --elevation-2: 0 4px 16px rgb(23 35 41 / 12%);
  --elevation-3: 0 12px 32px rgb(23 35 41 / 18%);
}

@media (prefers-color-scheme: dark) {
  :root {
    --canvas: #10191D;
    --surface: #18252B;
    --surface-raised: #213239;
    --surface-subtle: #233238;
    --surface-hover: #213944;
    --text-primary: #EEF4F5;
    --text-secondary: #B7C6CC;
    --text-disabled: #78909A;
    --border-subtle: #455961;
    --border-strong: #78909A;
    --primary: #80D1DF;
    --primary-hover: #A8DDE5;
    --on-primary: #08272F;
    --selection-bg: #213944;
    --selection-indicator: #80D1DF;
    --focus-ring: #FFB36B;
    --status-success-bg: #173D2C;
    --status-success-fg: #A7E4C2;
    --status-warning-bg: #493710;
    --status-warning-fg: #FFDC85;
    --status-danger-bg: #4D2426;
    --status-danger-fg: #FFB5B7;
    --status-info-bg: #163443;
    --status-info-fg: #A8D8F0;
    --elevation-1: 0 1px 2px rgb(0 0 0 / 28%);
    --elevation-2: 0 6px 20px rgb(0 0 0 / 36%);
    --elevation-3: 0 16px 40px rgb(0 0 0 / 48%);
  }
}
```

`docs/design/theme-preview.html` applies this contract to the real **Today at Reception / arrivals queue** surface from the v1 mockups.
