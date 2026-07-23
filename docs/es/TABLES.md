# Las tablas — cómo cambiar el editor sin escribir código

**Idiomas:** [English](../en/TABLES.md) · [Español](../es/TABLES.md) · [Français](../fr/TABLES.md)

Todo lo que el editor hace con un signo —la tecla que lo inserta, cómo se
dibuja, se lee y se transcribe— sale de las tablas JSON de `data/`.

## La envoltura común

Todas las tablas tienen la misma forma:

```json
{
  "table": "labels",
  "version": 1,
  "language": "es",
  "entries": [ { "id": "plus", "label": "más" } ]
}
```

- `language` es `null` en las tablas independientes del idioma; las que
  dependen de él llevan además el sufijo en el nombre: `labels.fr.json`.
- Todo `id` se refiere al catálogo `elements.json` y cumple
  `[a-z][a-z0-9_]*`. **Los ids no se traducen nunca**: son el identificador
  estable al que apunta todo el sistema.

## Las tablas

| Archivo | Módulo original | Contenido |
|---|---|---|
| `elements.json` | (decisión "a") | catálogo: id, tipo, categoría, MathML/Unicode, aridad, nivel |
| `keys_signs.json` | A2 | signo o estructura → pulsación |
| `keys_commands.json` | A3 | comando → pulsación |
| `keys_numpad.json` | A4 | alternativas del bloque numérico |
| `profiles.json` | A7 | perfiles → nivel máximo y bloqueo de calculadora |
| `glyphs.json` | B1 | glifo y plantilla lineal |
| `labels.<idioma>.json` | B2 | etiqueta hablada (con `parts` para estructuras) |
| `messages.<idioma>.json` | — | mensajes del programa (errores de cálculo…) |
| `ui.<idioma>.json` | E6 | cadenas de interfaz (menús, botones) |
| `br6.<idioma>.json` | B5 | celdas braille por elemento |
| `br6_text.<idioma>.json` | B5 | celdas braille por letra y dígito |

## Recetas habituales

### Añadir un signo

1. En `elements.json`, añada el elemento con su `unicode` (y `mathml` si es
   una estructura, además de su `arity`):
   ```json
   { "id": "infinity", "type": "sign", "category": "arithmetic", "unicode": "∞", "level": 3 }
   ```
2. Déle una tecla en `keys_signs.json`, un glifo en `glyphs.json` y una
   etiqueta en **todos** los `labels.<idioma>.json`.
3. Añada sus celdas braille a `br6.es.json`.
4. Ejecute `pytest`: los tests de integridad le dirán si falta algo.

### Cambiar un atajo

Edite el valor `keys` en la tabla correspondiente. Los nombres son
canónicos (`Ctrl+F`, `Left`, `NumAdd`) y son los mismos en escritorio y
web. Los tests rechazan una pulsación asignada dos veces.

Una pulsación puede ser un **acorde**: una secuencia separada por comas como
`"Ctrl+G, P"` (la convención que usa EdiCo para letras griegas y títulos).
La primera pulsación deja el teclado a la espera; la siguiente la completa.
Un acorde y una asignación simple no pueden solaparse: `"Ctrl+G"` y
`"Ctrl+G, P"` juntas se rechazan, porque tras `Ctrl+G` el editor solo puede
hacer una cosa.

### Reasignar una tecla como usuario, sin conflictos

El usuario no edita las tablas de fábrica. Sus reasignaciones personales
viven en un mapa de teclas que el editor carga **el último**, de modo que
una asignación del usuario gana sobre las de fábrica, sobre un perfil de
compatibilidad (Lambda, EdiCo) y sobre los add-ons. El archivo es
`$DISVIMAT_USER_KEYMAP` o `~/.disvimat/user_keys.json`.

La herramienta `rebind` lo edita con seguridad:

```bash
python -m disvimat.tools.rebind show "Ctrl+F"      # qué hace una pulsación
python -m disvimat.tools.rebind set fraction "Ctrl+B"
python -m disvimat.tools.rebind clear fraction
python -m disvimat.tools.rebind list
```

Antes de guardar, **rechaza** una asignación que no puede funcionar (un
comando inexistente, o un acorde que ensombrecería a otro) y **avisa**
cuando la nueva pulsación ya la usaba otro comando, nombrando al que la
pierde, para que una reasignación sea deliberada y nunca silenciosa.

### Añadir un idioma

Copie `labels.en.json`, `messages.en.json` y `ui.en.json` con el código de
su idioma, ponga `"language"` en cada uno y traduzca **solo los valores**.
Lo que no traduzca recurre al inglés en lugar de fallar.

El braille es distinto: véase más abajo.

### Añadir una tabla braille

`br6.<idioma>.json` y `br6_text.<idioma>.json` debe producirlos alguien que
conozca la signografía matemática braille de ese país. **No recurren** a
otro idioma a propósito: dar braille español a un lector francés sería
incorrecto. Sin ellas, la aplicación simplemente desactiva sus funciones
braille.

> **Importante.** Los valores actuales de `br6.es.json` son
> **provisionales** y deben revisarse contra la signografía matemática de
> la CBE (Comisión Braille Española) antes de usarse en el aula. La
> exportación braille es Unicode (U+2800…, `.brl`).
> provisional.

## Cómo se describen las estructuras

Una estructura tiene huecos y se describe a sí misma tres veces:

- **Glifo**, con una `template` lineal donde `{1}`, `{2}`… son los huecos:
  `"({1}∕{2})"` presenta la fracción como `(2∕3)`.
- **Etiqueta**, con `parts` (`start`, `separator`, `end`) que construyen la
  lectura lineal: "fracción 2 entre 3 fin de fracción". `start` puede
  omitirse, que es como "x elevado a 2" suena natural.
- **Braille**, con las mismas tres `parts`, cada una con su lista de celdas.

Una celda se escribe con sus puntos: `"1-4-5"`; `""` es la celda en blanco.

## Integridad

`tests/test_integrity.py` comprueba, en cada build, que:

1. toda entrada se refiere a un id existente en `elements.json`;
2. todo signo y estructura tiene glifo y celdas braille, y todo elemento
   tiene etiqueta en todos los idiomas;
3. todos los idiomas definen exactamente los mismos ids de mensajes y de
   interfaz;
4. ninguna pulsación está asignada dos veces, ni siquiera entre tablas.

Una tabla rota detiene la build, no al usuario.
