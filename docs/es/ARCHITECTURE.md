# Arquitectura

**Idiomas:** [English](../en/ARCHITECTURE.md) · [Español](../es/ARCHITECTURE.md) · [Français](../fr/ARCHITECTURE.md)

## La idea que hay que retener

Casi todo el comportamiento del editor son **datos, no código**. Qué tecla
inserta qué signo, cómo se dibuja una fracción, cómo se lee, cómo se
transcribe a braille: todo vive en tablas JSON dentro de `data/`. Añadir un
signo, cambiar un atajo o traducir el editor a otro idioma es editar una
tabla, no escribir Python.

Era la petición del documento original —"un único formato de tablas, un
único editor de tablas"— y es la columna vertebral del diseño.

## Capas

El proyecto usa una arquitectura hexagonal (puertos y adaptadores): un
núcleo en Python puro que no sabe nada de interfaces, y adaptadores
delgados por encima.

```
┌──────────────────────────────────────────────────────────┐
│                    disvimat/core/                        │
│  document (árbol) · elements · tables · keyboard         │
│  presentation · speech · calculator · integrity          │
│  filters/mathml · transcription/braille · ui_text        │
└───────────────┬──────────────────────┬───────────────────┘
                │                      │
   ┌────────────▼───────────┐ ┌────────▼──────────────────┐
   │ disvimat/desktop/      │ │ disvimat/web/             │
   │ wxPython, controles    │ │ FastAPI + HTML semántico  │
   │ nativos que lee NVDA   │ │ con MathML nativo         │
   └────────────────────────┘ └───────────────────────────┘
```

`tests/test_architecture.py` hace cumplir la regla en la CI: importar el
núcleo nunca debe arrastrar `wx`, `fastapi` ni ninguna otra biblioteca de
interfaz.

### Por qué dos interfaces y no un framework único

Los frameworks que prometen "un solo código, escritorio y web" (Flet,
Kivy…) dibujan sobre un lienzo y son **invisibles para los lectores de
pantalla**. Para este público eso es descalificatorio. Así que cada
interfaz usa lo más accesible en su plataforma:

- **Escritorio: wxPython.** Controles nativos de Windows, expuestos por
  MSAA/UIA, que NVDA lee sin trabajo adicional. La propia interfaz de NVDA
  está escrita en wxPython, lo que también cuenta para el futuro add-on
  (módulos B3/E1).
- **Web: FastAPI + MathML.** MathML Core lo renderizan de forma nativa
  Chrome, Firefox y Safari, y los lectores de pantalla lo verbalizan: las
  matemáticas son contenido real, no una imagen.

El coste de dos interfaces es bajo porque **las interfaces son delgadas**:
traducen eventos a pulsaciones canónicas, se las pasan al núcleo y muestran
la respuesta. Todo el comportamiento es compartido.

## El documento

Un documento es un árbol, no una cadena:

- `Character` — un carácter de texto plano (un dígito, una letra).
- `Sign` — un signo del catálogo, sin huecos (`plus`, `equals`).
- `Structure` — una estructura del catálogo con huecos (`fraction` tiene dos).

El cursor es un camino que desciende por las estructuras más un índice en
la secuencia actual, y siempre está *entre* dos nodos. Como el documento es
estructural y no textual, moverse por estructuras, seleccionar un numerador
o transcribir a braille son operaciones naturales, no cirugía de cadenas.

Deshacer y rehacer trabajan con instantáneas del árbol completo: simple,
correcto y sobradamente rápido para el tamaño de una expresión matemática.

## El ciclo de edición

Cada pulsación sigue el mismo camino en las dos interfaces:

1. La interfaz normaliza el evento a la **forma canónica** de las tablas:
   `"Left"`, `"Ctrl+F"`, `"+"`. Esos nombres están en inglés y no se
   traducen nunca.
2. `Keyboard.resolve` la convierte en un elemento del catálogo, respetando
   el nivel del perfil de usuario (A7).
3. `Editor.press` la aplica: se ejecuta un comando, o se inserta un signo o
   una estructura.
4. El editor devuelve un `Result` con tres cosas: el **texto** lineal, la
   **posición** del caret y la cadena de **voz**.
5. La interfaz muestra el texto, coloca el caret y anuncia la voz: en la
   línea de estado en escritorio, en una región `aria-live` en la web.

Como los pasos 2 a 4 son compartidos, escritorio y web se comportan igual
por construcción, no por disciplina.

## Localización

Hay un único mecanismo de localización: **tablas JSON por idioma con
reserva al inglés**. La voz (`labels`), los mensajes del programa
(`messages`) y las cadenas de interfaz (`ui`) funcionan igual, así que un
traductor aprende un solo formato y no necesita compilar nada.

El braille es la excepción deliberada: las tablas `br6` **nunca recurren**
a otro idioma. El braille matemático es normativo y difiere por país (CBE
en España, UEB en inglés, NMB en francés), así que servir el braille de un
país a otro sería incorrecto. Cuando un idioma no tiene tabla braille, la
aplicación desactiva sus funciones braille en vez de adivinar.

## Mapa de módulos

| Documento original | Dónde vive |
|---|---|
| A1 filtro MathML | `core/filters/mathml.py` |
| A2–A4 tablas de teclado | `core/keyboard.py` + `data/keys_*.json` |
| A7 perfiles | `data/profiles.json`, aplicado en `core/keyboard.py` |
| A8–A9 calculadora y bloqueo | `core/calculator.py`, `core/editor.py` |
| B1 glifos | `data/glyphs.json` + `core/presentation.py` |
| B2 verbalización | `data/labels.*.json` + `core/speech.py` |
| B4 ventana de presentación | `desktop/app.py`, `web/static/` |
| B5–B6 braille y su ventana | `core/transcription/braille.py`, `desktop/app.py` |
| C1 exportación XHTML | `export/xhtml.py` |
| C3 exportación BRA | `core/transcription/braille.py` |
| D1 importación XHTML | `core/filters/mathml.py` |
| E6 internacionalización | `core/ui_text.py` + las tablas por idioma |

Lo que todavía falta está en [STATUS.md](STATUS.md).

## Reglas de mantenimiento

1. **El núcleo no importa nada de las interfaces** (lo verifica un test).
2. **El comportamiento vive en los datos, no en el código**: añadir un
   signo, una tecla o un idioma es editar tablas.
3. **El núcleo no contiene texto para el usuario.** Si el programa debe
   decir algo nuevo, recibe un id de mensaje y el texto va a una tabla.
4. **Un formato de tabla, un juego de comprobaciones de integridad.** Una
   tabla incoherente rompe la build, nunca al usuario.
5. **Tipado estricto** (`mypy --strict`) y tests para cada comportamiento.
