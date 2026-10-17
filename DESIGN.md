# The Inkling Design System

## Product register

Authenticated reading product. The interface should feel like a contemporary daily paper with the clarity of a dependable reading tool. Optimize for scanning, reading comfort, keyboard use, and clear source attribution.

## North Star

**A paper with a forest-green spine:** an evergreen navigation rail holds the edition together while the reader moves across a light, tactile page. The news itself stays quiet; one small orange-red editorial stamp marks the lead and the current issue.

## References and anti-references

- Reference: a bound field journal, a magazine's clear section labels, and the open margins of a well-set book page.
- Anti-reference: AI gradients, glass panels, dark video backdrops, glowing controls, generic SaaS metric cards, or rounded-card grids for every story.
- Do not imitate a specific newspaper masthead, logo, or licensed typeface.

## Palette

Runtime ownership is in `src/index.css`; this document records its semantic values. Components consume CSS variables rather than raw colors.

| Token          | Value     | Role                                           |
| -------------- | --------- | ---------------------------------------------- |
| `--paper`      | `#f0f1eb` | App canvas                                     |
| `--surface`    | `#fffefa` | Reading surface and form fields                |
| `--ink`        | `#252a26` | Main text                                      |
| `--muted`      | `#747a73` | Secondary copy                                 |
| `--rule`       | `#c9cec6` | Dividers and quiet borders                     |
| `--spine`      | `#203b34` | Persistent navigation rail                     |
| `--accent`     | `#d26747` | Lead marker, active navigation, primary action |
| `--accent-ink` | `#fffaf4` | Text on accent                                 |
| `--leaf`       | `#537261` | Positive status and saved signal               |
| `--danger`     | `#a43d32` | Errors and destructive intent                  |
| `--focus`      | `#245c9b` | Visible keyboard focus                         |

## Typography

- Display and story headlines: Instrument Serif, regular; system Georgia fallback.
- Interface, labels, body copy, and metadata: Inter, system sans-serif fallback.
- Masthead: display face, 42–64 px responsive, normal weight, tight leading.
- Lead headline: display face, 36–56 px responsive, line-height 1.02–1.12.
- Section headings: sans serif, 12–14 px, uppercase with restrained tracking.
- Reading body: 17–19 px, line-height 1.6–1.75, measure 58–72 characters.
- Metadata: sans serif, 12–13 px, muted; never below 12 px for essential information.

## Layout and density

- Wide reader shell: maximum 1500 px with a 224 px evergreen navigation spine and a flexible reading canvas.
- Masthead and publication date form an opening band above a vermilion issue stamp and the day's lead.
- Desktop home: a 7/5 lead-and-briefing split, followed by two-column story rows; reader topics remain secondary.
- Article text pages: a centered 680 px measure with persistent source and edition context.
- Archive: a compact chronological list grouped by date, not a masonry card wall.
- Mobile: single-column reading order, visible bottom-level destination links, and no horizontal scrolling.
- Use a 4 px spacing base with 8/12/16/24/32/48 px common steps.

## Shapes, elevation, and iconography

- Paper and page surfaces are square or use at most 4 px radius.
- Inputs use 3 px radius. Primary controls use 3 px radius and never pill styling.
- Flat surfaces are the default. Thin rules and whitespace create hierarchy; no glass blur or decorative drop shadows.
- Use Lucide line icons at 16–20 px beside text. Icon-only controls require an accessible name and tooltip/title.

## Motion

- Use short 120–180 ms opacity or color transitions for focus and selection.
- Avoid entrance choreography and parallax. Disable nonessential motion under `prefers-reduced-motion: reduce`.
- Loading keeps page and control geometry stable; use a compact status line rather than a shifting skeleton wall.

## Design tokens and runtime mapping

Runtime CSS variables in `src/index.css` are canonical for colors and type roles; this document mirrors those values. Reusable layout and control styles are authored in `src/index.css`, with semantic React components in `src/main.jsx`. Token drift is checked by comparing this table with the `:root` declarations and by inspecting rendered browser styles.

## Composition sketch

Desktop:

    ┌──────── forest spine ────────┬──────────── paper canvas ─────────────────┐
    │ The Inkling                  │ issue date / reader name                    │
    │ Today                        │ THE MORNING EDITION · subject tags          │
    │ Archive                      │ lead headline             editor's note     │
    │ My topics                    │ lead summary               top briefing      │
    │                              │ ─────────────────────────────────────────── │
    │ reader / sign out            │ latest stories in two quiet columns        │
    └──────────────────────────────┴───────────────────────────────────────────┘

Mobile keeps the paper canvas and replaces the spine with a narrow masthead plus a fixed three-destination bottom bar.

## Content and accessibility

- Use plain English, sentence case, clear dates, and named sources.
- Target WCAG 2.2 AA. Keep visible keyboard focus, semantic headings, landmark navigation, form labels, and live status announcements.
- Color is never the only carrier of status or feedback meaning.
- Dates use the UTC edition date as a date-only value and display without timezone conversion.
