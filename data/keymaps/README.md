# Keyboard profiles (keymaps)

A keymap makes DISVIMAT answer to **another editor's key strokes**, so a
user coming from Lambda or EDICO keeps the commands they already know.

A keymap is an ordinary key table, loaded **after** the built-in ones, so
each stroke it defines wins and everything it leaves out keeps the default
binding. That means a profile only has to list what differs.

```json
{
  "table": "keys",
  "version": 1,
  "language": null,
  "entries": [
    { "id": "fraction", "keys": "Ctrl+B" },
    { "id": "sqrt", "keys": "Ctrl+Shift+2" }
  ]
}
```

- `id` is a catalogue id from `../elements.json` (`fraction`, `calculate`,
  `next_slot`…), the same stable ids the rest of the project uses.
- `keys` is a canonical stroke: `"Ctrl+F"`, `"Left"`, `"NumAdd"`,
  `"Ctrl+Shift+R"`. These names are never translated.

Select one with the `DISVIMAT_KEYMAP` environment variable:

```
set DISVIMAT_KEYMAP=lambda
```

## Status of the bundled profiles

| File | State |
|---|---|
| `lambda.json` | **empty scaffold** — to be filled from the Lambda manual |
| `edico.json` | **empty scaffold** — to be filled from the EDICO manual |

They are deliberately empty: an empty profile behaves exactly like the
defaults, so nothing is broken, and inventing shortcuts we have not
verified would be worse than shipping none. Fill them in from the official
documentation of each editor, or by listing the shortcuts from a running
installation, and the migration is complete — **no code changes needed**.

`tests/test_keymaps.py` checks that every profile references ids that
exist, so a typo fails the build rather than silently doing nothing.
