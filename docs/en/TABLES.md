# The tables — how to change the editor without writing code

**Languages:** [English](../en/TABLES.md) · [Español](../es/TABLES.md) · [Français](../fr/TABLES.md)

Everything the editor does with a sign — the key that inserts it, how it is
drawn, spoken and transcribed — comes from the JSON tables in `data/`.

## The common envelope

Every table looks the same:

```json
{
  "table": "labels",
  "version": 1,
  "language": "en",
  "entries": [ { "id": "plus", "label": "plus" } ]
}
```

- `language` is `null` for language-independent tables; language-dependent
  ones also carry the suffix in the filename: `labels.fr.json`.
- Every `id` refers to the `elements.json` catalogue and matches
  `[a-z][a-z0-9_]*`. **Ids are never translated**: they are the stable
  identifier the whole system points at.

## The tables

| File | Brief module | Contents |
|---|---|---|
| `elements.json` | (decision "a") | catalogue: id, type, category, MathML/Unicode, arity, level |
| `keys_signs.json` | A2 | sign or structure → key stroke |
| `keys_commands.json` | A3 | command → key stroke |
| `keys_numpad.json` | A4 | numeric-keypad alternatives |
| `profiles.json` | A7 | profiles → maximum level and calculator lock |
| `glyphs.json` | B1 | glyph and linear template |
| `labels.<lang>.json` | B2 | speech label (with `parts` for structures) |
| `messages.<lang>.json` | — | program messages (calculator errors…) |
| `ui.<lang>.json` | E6 | interface strings (menus, buttons) |
| `br6.<lang>.json` | B5 | braille cells per element |
| `br6_text.<lang>.json` | B5 | braille cells per letter and digit |

## Common recipes

### Add a sign

1. In `elements.json`, add the element with its `unicode` (and `mathml` if
   it is a structure, plus its `arity`):
   ```json
   { "id": "infinity", "type": "sign", "category": "arithmetic", "unicode": "∞", "level": 3 }
   ```
2. Give it a key in `keys_signs.json`, a glyph in `glyphs.json` and a label
   in **every** `labels.<lang>.json`.
3. Add its braille cells to `br6.es.json`.
4. Run `pytest`: the integrity tests tell you if anything is missing.

### Change a shortcut

Edit the `keys` value in the relevant table. The names are canonical
(`Ctrl+F`, `Left`, `NumAdd`) and are the same on desktop and web. Tests
reject a stroke assigned twice.

### Add a language

Copy `labels.en.json`, `messages.en.json` and `ui.en.json` to your language
code, set `"language"` in each, and translate **the values only**. Anything
you do not translate falls back to English rather than failing.

Braille is different: see below.

### Add a braille table

`br6.<lang>.json` and `br6_text.<lang>.json` must be produced by someone
who knows that country's mathematical braille standard. They **do not fall
back** to another language on purpose: giving Spanish braille to a French
reader would be wrong. Without them the application simply disables its
braille features.

> **Important.** The current values of `br6.es.json` are **provisional**
> and must be reviewed against the CBE (Comisión Braille Española)
> mathematical braille standard before classroom use. The ASCII encoding of
> the braille export is Unicode (U+2800…, `.brl`).

## How structures are described

A structure has slots and describes itself three times:

- **Glyph**, with a linear `template` where `{1}`, `{2}`… are the slots:
  `"({1}∕{2})"` renders the fraction as `(2∕3)`.
- **Label**, with `parts` (`start`, `separator`, `end`) that make the
  linear reading: "fraction 2 over 3 end of fraction". `start` may be
  omitted, which is how "x to the power of 2" reads naturally.
- **Braille**, with the same three `parts`, each holding a list of cells.

A cell is written as its dots: `"1-4-5"`; `""` is the blank cell.

## Integrity

`tests/test_integrity.py` checks, on every build, that:

1. every entry refers to an id that exists in `elements.json`;
2. every sign and structure has a glyph and braille cells, and every
   element has a label in every language;
3. all languages define exactly the same message and interface ids;
4. no key stroke is assigned twice, not even across tables.

A broken table stops the build, not the user.
