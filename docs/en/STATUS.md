# Project status — what exists and what is missing

**Languages:** [English](../en/STATUS.md) · [Español](../es/STATUS.md) · [Français](../fr/STATUS.md)

Audit against the module list of the original project brief
([README.md](../BRIEF.es.md)). Updated 2026-07-21.

Legend: **done** · **partial** — usable but incomplete · **pending** — not started.

## Summary

The editor is usable today for **linear arithmetic and elementary algebra**,
on the **desktop** (wxPython + NVDA) and on the **web** (FastAPI + native
MathML), with speech in English, Spanish and French, six-dot braille in
Spanish, XHTML import/export, Unicode braille export and an exact-arithmetic
calculator with a teacher's lock.

The two largest gaps are the **NVDA add-on** (braille displays and direct
speech, modules B3/E1) and **two-dimensional structures** (matrices and
tables, modules A10/B7).

## A) Operating modules

| Module | State | Notes |
|---|---|---|
| A1 Unicode/MathML → DisvimatEditor filter | **done** | Round trip verified by tests |
| A2 signs and structures → key strokes | **done** | `keys_signs.json`; strokes may be **chords** (`"Ctrl+G, P"`, the EDICO convention) resolved by a small state machine |
| A3 commands → key strokes | **partial** | Table done; the *conditions* grammar is not implemented. The `condition` field exists but `Keyboard` loads only unconditional entries, so a conditional binding would do nothing — neither work nor complain. Until the grammar exists, `integrity.unsupported_conditions` **fails the build** when a table uses it, rather than letting the binding go quiet |
| — keyboard profiles and user reassignment | **done** | Compatibility profiles (`data/keymaps/`, Lambda/EDICO) load over the defaults; a per-user keymap (`$DISVIMAT_USER_KEYMAP` or `~/.disvimat/user_keys.json`) loads last and wins. The `rebind` tool reassigns a key with conflict detection (refuses unknown commands and chord overlaps, warns on stolen strokes) |
| A4 alternative keys (numeric keypad) | **partial** | Four bindings only; the full keypad scheme is pending. They now work on **both** interfaces: the browser reports the keypad's `/` as key `"/"` like the main row, so the web read it as a division sign while the desktop inserted a fraction. Both adapters now derive their key names from `keys_platform.json` |
| A5 script / add-on designer | **done** | [Add-ons](ADDONS.md): a `register(registry)` function adds commands (key, speech, code) and exporters, found as installed packages or as `.py` files in `DISVIMAT_ADDONS`. Failures are contained |
| A6 help file (editable, per language) | **pending** | |
| A7 user profile configurator | **partial** | `profiles.json` limits elements per level and locks the calculator, and **the profile travels inside the `.dvm`**: opening a document builds the editor that document describes, so an exam prepared by the teacher imposes its restrictions on any machine. An editing interface for profiles is still missing |
| A8 calculator | **partial** | Exact fraction arithmetic, precedence, powers and exact roots; no variables, functions or trigonometry |
| A9 calculator locker | **done** | `calculator: false` in the profile (the `exam` profile) |
| A10 two-dimensional structures (tables, matrices, determinants) | **partial** | Matrices: insert (`Ctrl+Shift+M`), grid navigation, add row/column (`Alt+Down`/`Alt+Right`), read row by row, MathML `<mtable>` in and out, `.dvm`. Determinants/tables reuse the same node |
| A11 two-dimensional algorithms | **pending** | |

## B) Presentation modules

| Module | State | Notes |
|---|---|---|
| B1 glyph table | **done** | With linear templates for structures |
| B2 labels / speech per language | **done** | Editing feedback in English, Spanish, French (our tables); whole-expression reading via [MathCAT](MATHCAT.md) for English and Spanish |
| B3 br8 (NVDA and braille displays) | **partial** | The desktop speaks every action through the screen reader and pushes the current line to a connected braille display, via the NVDA/JAWS controller (`accessible_output2`). BR8 *input* and a dedicated add-on are still pending |
| B4 graphical presentation window | **done** | Native text control (desktop) and native MathML (web) |
| B5 braille transcriber | **done (external engines)** | Braille comes from a ladder ([BRAILLE.md](BRAILLE.md)): [MathCAT](MATHCAT.md) for math (CMU, UEB), [liblouis](BRAILLE.md) for text (official tables, e.g. French), our `br6` tables as last resort. Verified on 64-bit Python 3.13 |
| B6 br6 window | **partial** | The window shows and follows the transcription; navigating *inside* the braille window is not implemented |
| B7 presentation of 2D structures | **partial** | Linear form `[a,b;c,d]` on screen and native `<mtable>` on the web; a dedicated 2D window is still to come |
| B8 presentation of 2D algorithms | **pending** | |
| B9 sign-language messages | **pending** | |

## C) Export modules

| Module | State | Notes |
|---|---|---|
| C1 XHTML | **done** | MathML that browsers render and screen readers speak |
| C2 PDF | **pending** | Planned via WeasyPrint, reusing the XHTML export |
| C3 braille export | **done** | Exports Unicode braille (U+2800…, `.brl`, UTF-8) from whichever engine is active (MathCAT / liblouis / tables). ASCII conversion is still available in code but is no longer the export format |
| C4 MP3 | **pending** | |

## D) Import modules

| Module | State | Notes |
|---|---|---|
| D1 XHTML | **done** | Undoable; clear errors for unsupported content |
| D2 LaTeX | **pending** | |

## E) Extension modules

| Module | State |
|---|---|
| E6 internationalisation | **done** — English, Spanish, French; adding a language is editing JSON |
| E1 br8 braille-display input | **pending** |
| E2 virtual braille keyboard | **pending** |
| E3 formula collections | **pending** |
| E4 mathematical dictionary | **pending** |
| E5 theorem store | **pending** |
| E7 handwriting input | **pending** |
| E8 custom symbols | **pending** |
| E9 voice control | **pending** |
| E10–E11 statistical and function graphs | **pending** |
| E12 graph sonification | **pending** |
| E13 interactive exercises | **pending** |
| E14 mathematical games | **pending** |

## F) Chemistry version

All of F1–F6 are **pending**. The groundwork exists: the catalogue already
carries a `category` field, so chemistry signs and structures are added as
data rather than as code.

## Cross-cutting gaps worth knowing

These are not in the original module list but matter for real use:

1. ~~No native document format.~~ **Done:** the `.dvm` format
   ([DOCUMENT.md](DOCUMENT.md)) saves and reopens the exact tree, with the
   language and profile it was written for. Save/Open on desktop and web.
2. ~~A document is a single line.~~ **Done:** documents are now
   **multi-line** — `Return` starts a line, arrow keys move between lines at
   the top level, and each line renders, speaks and brailles on its own.
3. ~~No NVDA add-on, so speech relies on the status line.~~ **Fixed:** the
   desktop now speaks every action through the screen reader and sends
   braille to the display. A dedicated add-on is still needed for BR8
   keyboard *input* (E1).
4. **Web sessions live in memory.** They no longer grow without bound: they
   expire when idle (`DISVIMAT_SESSION_TTL`, two hours by default) and
   their number is capped (`DISVIMAT_MAX_SESSIONS`, 500), least recently
   used discarded first. When a session expires the page opens a new one
   and **announces it aloud**, so nobody is left typing into an editor that
   has gone silent. There is still no authentication or persistence: the
   document is lost when the process restarts.
5. **Braille needs expert validation.** The engine is finished, the values
   are not: they must be checked against the CBE mathematical braille
   standard before any classroom use.
6. **Automated accessibility testing: half of it now exists.** The
   desktop's contract with the screen reader **is** checked in CI: a
   **Windows** job with wxPython builds the real window and verifies that
   every action is spoken (not merely shown on the status line), that the
   caret lands where the core put it, that the current line reaches the
   braille display, and that no braille is sent when there is no engine.
   CI used to run on Linux only, without wxPython, so those tests skipped
   themselves entirely and the build went green having tested nothing;
   `DISVIMAT_REQUIRE_DESKTOP=1` now turns that skip into a failure wherever
   wxPython is meant to be present.
   The **web** too: the structure a screen reader depends on is checked
   against the rendered page (a single `aria-live` region, the status bar
   deliberately outside it, `role="application"` with a name and
   instructions, `aria-*` references that resolve, unique ids, a skip link
   that lands somewhere, heading order, zoom allowed, `lang` per language).
   And `editor.js` went from no tests at all to a **vitest + jsdom** suite
   that evaluates the real file inside the real page and drives it with
   events: the keypad's `/`, the order of key strokes (one request in
   flight at a time), the live region, and recovering from an expired
   session out loud.
   Still missing: an **axe-core pass in a real browser** — what jsdom
   cannot give is computed contrast and visibility, so running it there
   would be false confidence — and scripted NVDA testing (Guidepup).

## Suggested next steps

Braille/speech (MathCAT + liblouis) and the document layer (`.dvm`,
multi-line) are done. What remains, in order of impact:

1. NVDA add-on for braille displays and direct speech (B3/E1) — MathCAT's
   own NVDA add-on is the reference implementation to follow.
2. Two-dimensional structures (A10/B7): matrices and tables.
3. PDF (C2) and MP3 (C4) export.
4. Mixed text + mathematics in a document (liblouis text braille then
   covers the prose parts).
