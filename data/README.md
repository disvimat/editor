# DisvimatEditor tables

Every correspondence table of the editor lives here, in the single agreed
format (prior decision "b" of the [brief](../docs/BRIEF.es.md)). Adding a
sign, changing a key stroke or translating a label means editing these
files: no Python involved.

Full guide, in three languages:
[English](../docs/en/TABLES.md) ·
[Español](../docs/es/TABLES.md) ·
[Français](../docs/fr/TABLES.md).

## Common envelope

```json
{
  "table": "table_name",
  "version": 1,
  "language": "en",
  "entries": [ ... ]
}
```

- `language` is `null` for language-independent tables; language-dependent
  ones also carry the suffix in the filename: `labels.fr.json`.
- Entry ids always reference the `elements.json` catalogue and match
  `[a-z][a-z0-9_]*`. Ids are never translated.

## Files

| File | Brief module | Contents |
|---|---|---|
| `elements.json` | (decision "a") | catalogue: id, type, category, MathML/Unicode, arity, level |
| `keys_signs.json` | A2 | sign or structure → key stroke |
| `keys_commands.json` | A3 | command → key stroke |
| `keys_numpad.json` | A4 | numeric-keypad alternatives |
| `profiles.json` | A7 | profile → maximum level and calculator lock |
| `glyphs.json` | B1 | glyph and linear `template` for structures |
| `labels.{en,es,fr}.json` | B2 | speech label (with `parts` for structures) |
| `messages.{en,es,fr}.json` | — | program messages (calculator errors…) |
| `ui.{en,es,fr}.json` | E6 | interface strings (menus, buttons) |
| `br6.es.json` | B5 | braille cells per element |
| `br6_text.es.json` | B5 | braille cells per letter and digit |

## Conventions

- **Key strokes** (`keys`): canonical English names, which is what wx and
  the browser emit: `"+"`, `"Left"`, `"Ctrl+F"`, `"Ctrl+Shift+R"`. They are
  never translated.
- **Conditions** (`condition`, optional): restricts when an entry applies
  (brief module A3); its grammar is not implemented yet, so conditional
  entries are ignored.
- **Cells**: dots of the braille cell, `"1-4-5"`; `""` is the blank cell.

## Braille warning

The values in `br6.es.json` are **provisional** and must be reviewed
against the CBE (Comisión Braille Española) mathematical braille standard
before classroom use; fixing them is editing this JSON, with no code
changes. The `.BRA` export currently uses the NABCC ASCII encoding, also
provisional (see `src/disvimat/core/transcription/braille.py`).

Braille tables **never fall back** to another language: mathematical
braille is normative and differs per country, so a language without tables
gets its braille features disabled instead of another country's braille.

## Integrity

`tests/test_integrity.py` checks on every build that ids exist, that every
sign and structure has a glyph and braille, that every element has a label
in every language, that all languages define the same message ids, and that
no key stroke is assigned twice. An inconsistent table breaks the build,
not the user.
