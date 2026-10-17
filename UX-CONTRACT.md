# UX Contract

## Product context

- Audience: readers who want a concise personal overview of broad news.
- Primary jobs: set interests, read today's paper, follow original sources, give feedback, and revisit earlier editions.
- Target markets: general English-language web audience.
- Active locale: `en-US` interface copy; article content remains in publisher language.
- Time policy: editions are keyed to UTC calendar dates; display date-only values without timezone conversion.
- Accessibility target: WCAG 2.2 AA.
- Visual direction: [DESIGN.md](DESIGN.md).

## Business-context sources

| Domain / scope                         | Authoritative source                                   | Source type             | Reviewed date |
| -------------------------------------- | ------------------------------------------------------ | ----------------------- | ------------- |
| Reader outcomes and content            | `PRODUCT.md` and NaSCon '26 problem statement PDF      | Product brief           | 2026-10-17    |
| Account permissions and API operations | `app/web.py` authenticated routes                      | API implementation      | 2026-10-17    |
| Edition and feedback lifecycle         | `app/database/models.py`, `app/database/repository.py` | Data model / repository | 2026-10-17    |
| Billing and payment                    | None; not part of core reader                          | Not applicable          | 2026-10-17    |
| Data retention and deletion            | No account-deletion contract exists yet                | Open product decision   | 2026-10-17    |

## Visual contract

- Project DESIGN.md: `DESIGN.md`.
- Token ownership: runtime CSS is canonical; `DESIGN.md` mirrors it.
- Runtime token source: `src/index.css`.
- Shared behavior owner: semantic React components in `src/main.jsx`.
- Supported theme: warm light paper; browser forced-colors remains usable.
- Design-context owner: update this contract and CSS in the same change when a shared decision changes.

## Canonical UI map

| Capability        | Canonical owner                                         | Source of truth            | Allowed variants                          | Verification                         |
| ----------------- | ------------------------------------------------------- | -------------------------- | ----------------------------------------- | ------------------------------------ |
| Article selection | Not applicable; no bulk selection                       | —                          | —                                         | —                                    |
| Select/Listbox    | Native labeled select only for bounded topic preference | This contract              | Native                                    | Keyboard and browser check           |
| Date              | Date-only display helper                                | UTC edition key in API     | Typed display; no date picker             | Date-boundary review                 |
| Form              | Shared label/input styles and submit-state behavior     | This contract              | Account / preferences                     | Validation and failure recovery      |
| Scrollbar         | Global application stylesheet                           | DESIGN.md                  | Geometry exceptions documented by surface | Computed style and keyboard scroll   |
| Toast/status      | Shared inline status region                             | This contract              | success / info / error                    | Live-region and screen-reader review |
| CRUD              | API-owned edition lifecycle                             | `PRODUCT.md`, `app/web.py` | Create / read / feedback                  | API and browser flow                 |

## Component behavior

| Component    | Default                                      | Hover              | Focus                       | Active       | Disabled        | Busy                     | Error                              |
| ------------ | -------------------------------------------- | ------------------ | --------------------------- | ------------ | --------------- | ------------------------ | ---------------------------------- |
| Button       | Bordered or vermilion by intent              | Slight color shift | Visible blue outline        | Pressed tone | Muted and inert | Stable size, status text | Inline message                     |
| Icon button  | Text tooltip/name                            | Surface tint       | Visible blue outline        | Pressed tone | Muted and inert | Stable size              | Inline message                     |
| Input        | Paper surface, associated label              | Border darkens     | Visible blue outline        | n/a          | Muted           | n/a                      | Text, aria-invalid, described-by   |
| Secret input | Masked; password manager enabled             | Border darkens     | Visible blue outline        | n/a          | Muted           | Submit is disabled       | Generic auth failure               |
| Search       | Local title/source filter with clear control | Border darkens     | Visible blue outline        | n/a          | n/a             | n/a                      | Inline retry if archive load fails |
| Textarea     | n/a                                          | n/a                | n/a                         | n/a          | n/a             | n/a                      | n/a                                |
| Article list | Headline, source, date, summary, actions     | Underline or tint  | Focus ring on links/actions | n/a          | n/a             | Stable row geometry      | Page-level retry                   |

## Dataset navigation

- Archive is an exploratory, date-grouped bounded list; the API caps the initial history query at 100 editions.
- Search filters loaded archive titles locally and clears immediately.
- Empty, loading, failed, and ready states use visible text and retain the page structure.
- Returning from a story uses the browser's normal new-tab behavior; archive navigation stays in the app.
- No multi-select or bulk operation exists.

## Flow ledger

| Operation            | Trigger               | Pending                                         | Success destination                     | Success feedback                                 | Failure recovery                                                        | Focus outcome                      | Source ref                       |
| -------------------- | --------------------- | ----------------------------------------------- | --------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------- | -------------------------------- |
| Create edition       | Build today's paper   | Queued state and polling                        | Today reader                            | Ready status and article count                   | Retry only after failed status; do not duplicate a running or ready job | Keep trigger location stable       | `POST /api/papers`               |
| Edit topics          | Save preferences      | Disable duplicate submit                        | Preferences stay open                   | Saved status                                     | Preserve values and show inline retry                                   | Focus remains on save control      | `PUT /api/preferences/paper`     |
| Read story           | Open publisher link   | New tab opens                                   | Publisher's canonical article           | Opened signal sent in background                 | Keep edition readable if signal fails                                   | Browser manages new tab            | Product brief                    |
| Save story           | Save action           | Pending action label                            | Same edition                            | Saved state after server confirmation            | Restore unsaved state and show retry                                    | Focus remains with article action  | `POST /api/papers/{id}/feedback` |
| Skip story           | Not interested action | Pending action label                            | Same edition with story removed locally | Hidden for current session; skipped signal saved | Restore story and show error                                            | Move focus to next article heading | Feedback API                     |
| Download edition PDF | Download PDF          | Preparing PDF status                            | Current edition                         | Browser downloads the generated edition          | Show an inline error and allow retry                                    | Focus stays on download control    | `GET /api/papers/{id}/pdf`       |
| Search archive       | Type or clear         | Local synchronous filtering                     | Same archive                            | Result count                                     | Not applicable                                                          | Keep focus in search               | UX contract                      |
| Background edition   | Queue task            | Poll status without blocking reading navigation | Today reader when ready                 | Inline ready status                              | Failed state offers retry                                               | Completion never steals focus      | Celery edition task              |

## Navigation and responsive behavior

- Product destinations: Today, Archive, and My topics.
- Header shows the publication identity, current section, and signed-in reader menu.
- Mobile uses one-column reading order and a bottom navigation bar; desktop uses a compact left rail.
- The same actions and labels remain available at all viewport sizes.
- Focus lands on the destination page heading when a destination changes.
- Story links include the publisher name and open the original page in a new tab with `rel="noopener noreferrer"`.

## Overlays and feedback

- Avoid overlays for ordinary navigation. Authentication is a dedicated page state.
- Use one shared inline status/alert region for pending, saved, and error messages.
- Critical API errors remain visible until corrected or retried; never show raw exception text.
- No browser alert, confirm, or prompt.

## Async and resilience

- Edition creation is queued and idempotent per reader and UTC date; running or ready editions are returned as-is.
- Feedback writes are pessimistic; show saved/skipped state only after server confirmation.
- If the reader loses connectivity, retain the current edition view and show a stable connection error with retry.
- Poll queued/running editions at a bounded interval; stop on ready or failed and pause when the tab is hidden.
- Session expiry clears the local token and returns the reader to sign-in while preserving non-sensitive topic form state in memory.
- No offline write queue is claimed.

## Validation

- API request models validate topic count, field lengths, and allowed feedback actions.
- Forms use `noValidate`; show inline errors, associate them with fields, and preserve non-sensitive values.
- Disable duplicate submits while a write is pending.
- Auth failures remain generic and never reveal whether an email exists.

## Permission and clipboard

- Edition, archive, preferences, and feedback endpoints require authentication and enforce reader ownership.
- Unauthenticated readers see sign-in/register, not private editions.
- No clipboard feature is present.

## Migration status

- Migration ledger: this section and the sprint commits on `main`.
- Canonical primitives: CSS tokens in `src/index.css`; shared semantic components in `src/main.jsx`.
- Current slices: reader shell/onboarding, article actions, archive, PDF export, and hybrid TF-IDF plus LangChain ranking.
- Legacy payment and AI-only aggregator code is still being retired; don't add new UI paths to it.
- Rollback is by commit; edition snapshots remain backward-compatible JSON records.

## Verification

- Static commands: Ruff check/format, ESLint, Prettier, Vite production build, and premium UI audit.
- Browser matrix: loading, empty, ready, queue failure, topic save failure, keyboard, narrow viewport, reduced motion, and session expiry.
- Accessibility: semantic headings/landmarks, visible focus, labels, contrast, live status, and tab navigation.
- Canonical sibling workflow: existing account session in `src/main.jsx`; migrate auth to the paper shell without changing the API auth contract.
