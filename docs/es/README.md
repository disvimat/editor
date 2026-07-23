# DISVIMAT — Editor científico accesible

**Idiomas:** [English](../en/README.md) · [Español](../es/README.md) · [Français](../fr/README.md)

DISVIMAT es un editor científico (matemáticas y, más adelante, química)
para personas ciegas y con baja visión. Funciona **en escritorio** y **en
web**, compartiendo un único núcleo, y presenta cada expresión de cuatro
maneras: en pantalla, hablada, en braille y en archivos exportables.

- [Arquitectura](ARCHITECTURE.md) — cómo está construido el proyecto y por qué.
- [Tablas](TABLES.md) — los datos que gobiernan el comportamiento del editor.
- [Formato de documento](DOCUMENT.md) — documentos multilínea y el formato `.dvm`.
- [Add-ons](ADDONS.md) — ampliar el editor sin tocar el núcleo.
- [Estado](STATUS.md) — qué está hecho y qué falta.
- [MathCAT](MATHCAT.md) — el motor externo de voz y braille.

## Requisitos

- Python 3.12 o superior.
- Para la interfaz de escritorio: wxPython (se instala automáticamente).
- Recomendado en Windows: el lector de pantalla [NVDA](https://www.nvaccess.org/).

## Instalación

```bash
python -m venv .venv
.venv\Scripts\pip install -e ".[desktop,web,dev]"
```

En Windows basta con hacer doble clic en `arrancar.bat`, que crea el
entorno la primera vez y después abre el editor de escritorio en español.

## Cómo arrancarlo

```bash
# Escritorio
python -m disvimat.desktop

# Web (después abrir http://127.0.0.1:8000/)
python -m disvimat.web.app
```

Dos variables de entorno configuran ambas interfaces:

| Variable | Significado | Valores |
|---|---|---|
| `DISVIMAT_LANG` | idioma de interfaz y de voz | `en` (por defecto), `es`, `fr` |
| `DISVIMAT_PROFILE` | perfil de usuario (A7) | `beginner`, `intermediate`, `advanced`, `exam` |
| `DISVIMAT_KEYMAP` | perfil de teclado — comandos de otro editor | `lambda`, `edico` (ver `data/keymaps/`) |
| `DISVIMAT_ADDONS` | carpeta de scripts de add-on | una ruta (ver [ADDONS](ADDONS.md)) |
| `DISVIMAT_DATA` | directorio de tablas | una ruta; por defecto `data/` |

En la web el idioma también es un parámetro: `http://127.0.0.1:8000/?language=es`.

## La voz y el lector de pantalla

El editor **habla cada acción** a través de su lector de pantalla (NVDA,
JAWS) o de SAPI: el signo o la estructura insertados, el hueco al que se ha
movido, el resultado de un cálculo y la palabra que termina al pulsar
espacio. Además envía la línea actual a la línea braille conectada.

Para ello hace falta `accessible_output2`, que instala el extra
`[desktop]`. Si falta, el editor sigue funcionando, pero la información solo
aparece en la barra de estado, que el lector de pantalla no lee por sí solo.

## Teclas

Los nombres de tecla son canónicos y no se traducen nunca, así que son los
mismos en todos los idiomas y en las dos interfaces.

| Teclas | Acción |
|---|---|
| `0-9`, letras | Insertar texto |
| `+` `-` `*` `/` `=` `<` `>` `%` `,` | Insertar el signo correspondiente |
| `Ctrl+F` | Fracción |
| `Ctrl+R` / `Ctrl+Shift+R` | Raíz cuadrada / raíz de índice |
| `Ctrl+P` / `Ctrl+B` | Potencia / subíndice |
| `Tab` | Siguiente hueco de la estructura |
| `←` `→` `Inicio` `Fin` | Mover el cursor |
| `↓` `↑` | Entrar / salir de una estructura |
| `Supr` / `Retroceso` | Borrar (una estructura se borra entera) |
| `Ctrl+Z` / `Ctrl+Y` | Deshacer / rehacer |
| `Ctrl+L` / `Ctrl+Shift+L` | Leer el elemento / la línea completa |
| `Ctrl+Intro` | Calcular el resultado |
| `Ctrl+I` / `Ctrl+E` | Importar / exportar XHTML (escritorio) |
| `Ctrl+6` | Ventana braille (escritorio) |

El bloque numérico también lleva `+`, `−`, `×` y `÷` (este último inserta
una fracción).

## Primer contacto

Teclee `1`, `+`, `Ctrl+F`, `2`, `Tab`, `3`. En pantalla aparece `1+(2∕3)`,
la línea se lee "1 más fracción 2 entre 3 fin de fracción" y `Ctrl+Intro`
responde "resultado: 5/3" como valor exacto.

## Desarrollo

```bash
.venv\Scripts\ruff check .      # estilo
.venv\Scripts\mypy              # tipado estricto del núcleo
.venv\Scripts\pytest            # pruebas
```

El código base —identificadores, comentarios y claves de las tablas— está
**en inglés** para que cualquiera pueda contribuir. Todo lo que el usuario
lee u oye vive en las tablas de `data/` y se traduce allí, nunca en el
código. Véase [TABLES.md](TABLES.md).

## Licencia

GPL-2.0-only. Autor: Carlos Daniel Ondo Angue (info@iataccess.org).
