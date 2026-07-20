# Plan técnico — Editor científico accesible DISVIMAT (Python)

**Autor del plan:** generado a partir del [README.md](../README.md)
**Fecha:** 2026-07-12
**Objetivo:** aplicación en Python, mantenible y eficiente, utilizable en **escritorio** (Windows con NVDA y líneas braille como primer objetivo) y en **web**.

---

## 1. Visión

DISVIMAT es un editor científico (matemáticas y química) para personas con discapacidad visual. Todo el contenido se representa internamente en un formato propio —**DisvimatEditor** (MathML + Unicode español)— y a partir de él se generan las distintas *presentaciones*: glifos en pantalla, verbalización por síntesis de voz, braille de 8 puntos (línea braille vía NVDA), braille de 6 puntos (transcripción .BRA), XHTML, PDF y MP3.

La clave del diseño es la que ya apunta el README: **casi todo el comportamiento del editor está definido por tablas de correspondencia** (signo ↔ tecla, signo ↔ glifo, signo ↔ etiqueta hablada, signo ↔ br8, signo ↔ br6, comando ↔ pulsación…). Si las tablas comparten un único formato, un único editor de tablas sirve para mantener todo el sistema.

## 2. Decisiones previas (punto "Importante" del README)

### a) Formato de los elementos DisvimatEditor

Cada elemento del editor es un registro con identidad estable:

```
id:            "frac"              (identificador único, ASCII, inmutable)
tipo:          estructura | signo | comando
categoria:     aritmética | álgebra | química | navegación | ...
mathml:        "mfrac"             (correspondencia MathML, si aplica)
unicode:       "⁄"                 (correspondencia Unicode, si aplica)
aridad:        2                   (nº de huecos, para estructuras)
nivel:         2                   (nivel de usuario mínimo)
```

El **documento** en memoria es un árbol de nodos cuyos tipos son estos elementos (equivalente estructural a MathML, no a texto plano). Esto hace triviales la navegación por estructura, la selección semántica y las transcripciones.

### b) Formato único de las tablas

**JSON con esquema (JSON Schema / pydantic)**, un archivo por tabla, bajo `data/`:

- Legible y editable a mano y por herramientas.
- Validable automáticamente al cargar (errores claros para el mantenedor).
- Versionable en git (los cambios de tablas quedan en el historial).
- Variantes por lengua mediante sufijo: `labels.es.json`, `labels.en.json`.

Todas las tablas comparten la misma envoltura:

```json
{
  "tabla": "signos_teclas",
  "version": 1,
  "lengua": "es",
  "entradas": [ { "id": "frac", "teclas": "Ctrl+F", "condicion": null } ]
}
```

### c) Editor de tablas

**Una única herramienta** (módulo `tools/table_editor`) que lee el esquema de cada tabla y genera el formulario correspondiente. Se ofrece en las dos interfaces (escritorio y web) reutilizando el mismo núcleo de validación. Detecta conflictos (dos signos con la misma pulsación, ids duplicados) antes de guardar.

## 3. Arquitectura general

**Arquitectura hexagonal (puertos y adaptadores):** un núcleo en Python puro sin ninguna dependencia de interfaz, y dos adaptadores de presentación (escritorio y web) que consumen exactamente la misma API.

```
┌────────────────────────────────────────────────────────┐
│                    disvimat/core/                      │
│  documento (árbol) · elementos · tablas · comandos     │
│  filtros MathML/LaTeX · transcriptores br6/br8         │
│  perfiles · calculadora · i18n                         │
└──────────────┬───────────────────────┬─────────────────┘
               │                       │
   ┌───────────▼──────────┐  ┌─────────▼──────────────┐
   │ disvimat/desktop/    │  │ disvimat/web/          │
   │ wxPython + NVDA      │  │ FastAPI + XHTML/MathML │
   │ (UIA, línea braille) │  │ accesible (WCAG 2.2)   │
   └──────────────────────┘  └────────────────────────┘
```

### ¿Por qué esta separación y no un único framework "escritorio+web"?

Los frameworks que prometen ambas cosas con un solo código (Flet, Kivy…) **dibujan sobre canvas y son opacos para los lectores de pantalla**: inaceptable aquí. Para el público de DISVIMAT la accesibilidad manda:

- **Escritorio: wxPython.** Usa controles nativos de Windows (MSAA/UIA), que NVDA lee sin trabajo extra; la propia interfaz de NVDA está escrita en wxPython, y los módulos E1/B3 (entrada y salida por línea braille) exigen integración estrecha con NVDA (add-on propio en Python, mismo lenguaje).
- **Web: FastAPI + XHTML semántico con MathML.** MathML Core ya se renderiza nativamente en Chrome, Firefox y Safari, y los lectores de pantalla lo verbalizan. HTML semántico + ARIA + los mismos atajos de teclado definidos en las tablas.

El coste de mantener dos capas de UI es bajo porque **las UIs son delgadas**: toda la lógica (qué hace cada tecla, cómo se transcribe, qué se verbaliza) vive en el núcleo y en las tablas.

## 4. Estructura del proyecto

```
disvimat/
├── pyproject.toml            # empaquetado, dependencias, ruff, mypy, pytest
├── data/                     # LAS TABLAS (formato único JSON, apartado 2b)
│   ├── elementos.json        #   catálogo DisvimatEditor (2a)
│   ├── teclas_signos.json    #   A2
│   ├── teclas_comandos.json  #   A3
│   ├── teclas_numpad.json    #   A4
│   ├── glifos.json           #   B1
│   ├── etiquetas.es.json     #   B2 (una por lengua)
│   ├── br8.es.json           #   B3
│   ├── br6.es.json           #   B5 (o tablas liblouis, ver §6)
│   └── perfiles/             #   A7: niveles de usuario
├── src/disvimat/
│   ├── core/
│   │   ├── documento.py      # árbol del documento, cursor, selección, undo
│   │   ├── elementos.py      # modelo de elemento DisvimatEditor
│   │   ├── tablas.py         # carga+validación de tablas (pydantic)
│   │   ├── comandos.py       # despacho comando→acción (A3), condicionantes
│   │   ├── teclado.py        # resolución pulsación→signo/comando (A2-A4, E2)
│   │   ├── filtros/          # A1, D: MathML↔árbol, LaTeX→árbol (lxml)
│   │   ├── transcripcion/    # B5: br6; B3: br8; B2: verbalización
│   │   ├── calculadora/      # A8, A9 (evaluación sobre el propio árbol)
│   │   ├── perfiles.py       # A7
│   │   └── i18n.py           # gettext, E6
│   ├── desktop/              # wxPython: ventana editor, ventana BR6 (B6),
│   │   │                     # ventanas de estructuras 2D (A10/A11/B7/B8)
│   │   └── nvda_addon/       # add-on NVDA para línea braille (B3, E1)
│   ├── web/                  # FastAPI: API REST/WebSocket + plantillas XHTML
│   ├── export/               # C1 XHTML, C2 PDF, C3 BRA, C4 MP3
│   └── tools/
│       └── table_editor/     # editor único de tablas (2c)
├── tests/                    # espejo de src/, + tests de accesibilidad
└── docs/
```

## 5. Correspondencia módulos README → plan

| README | Dónde vive | Fase |
|--------|-----------|------|
| A1 filtro MathML→Disvimat | `core/filtros/` | 1 |
| A2–A4 tablas de teclado | `core/teclado.py` + `data/teclas_*.json` | 1 |
| A5 scripts/add-ons | API pública del núcleo + scripts Python del usuario | 4 |
| A6 ayuda editable | XHTML editable, mismo visor | 3 |
| A7 perfiles | `core/perfiles.py` | 2 |
| A8–A9 calculadoras y bloqueo | `core/calculadora/` | 3 |
| A10–A11 estructuras/algoritmos 2D | ventanas hijas escritorio / paneles web | 3 |
| B1 glifos | `data/glifos.json` + render | 1 |
| B2 verbalización | `data/etiquetas.*.json` + `core/transcripcion/` | 1 |
| B3 br8/NVDA | add-on NVDA + `data/br8.*.json` | 2 |
| B4 presentación gráfica | UI escritorio/web | 1 |
| B5–B6 br6 + ventana BR6 | `core/transcripcion/` + ventana propia | 2 |
| B9 lengua de señas | vídeos/avatares — ampliación | 5 |
| C1–C4 exportación | `export/` | 2–3 |
| D (E1/E2) importación XHTML/LaTeX | `core/filtros/` | 2 |
| E1–E14 ampliaciones | diseñadas pero fuera del MVP | 4–5 |
| F química | mismas tablas con categoría "química" | 4 |

La numeración duplicada del README (dos bloques "E") se normaliza aquí como **D = importación** y **E = ampliaciones**.

## 6. Stack técnico

| Necesidad | Elección | Motivo |
|-----------|----------|--------|
| Lenguaje | Python ≥ 3.12 | requisito; tipado moderno |
| Núcleo XML/MathML | `lxml` | rápido (C), XPath, validación |
| Validación de tablas | `pydantic` v2 | esquemas declarativos, errores legibles |
| UI escritorio | `wxPython` | controles nativos → NVDA/UIA sin fricción |
| UI web | `FastAPI` + Jinja2 + MathML Core | API tipada; HTML accesible sin framework JS pesado |
| Transcripción br6 | `louis` (liblouis) | estándar mundial de transcripción braille, tablas españolas oficiales incluidas; evita reinventar B5 |
| Braille br8/línea | add-on NVDA (Python) | NVDA controla la línea braille; condicionantes de B3 |
| PDF (C2) | `weasyprint` | XHTML+CSS→PDF: reutiliza la exportación C1 |
| MP3 (C4) | SAPI5 (`pyttsx3`) en escritorio, TTS servidor en web + `pydub`/ffmpeg | voces del sistema del usuario |
| LaTeX (D2) | parser propio acotado o `latex2mathml` | entra por el mismo filtro que MathML |
| Cálculo (A8) | evaluador propio sobre el árbol (+ `sympy` opcional en niveles altos) | control fino de niveles y bloqueo A9 |
| i18n (E6) | `gettext` + tablas por lengua | estándar Python |
| Calidad | `pytest`, `ruff`, `mypy --strict` en core, CI GitHub Actions | mantenibilidad |

## 7. Accesibilidad como requisito de primera clase

- **Todo operable por teclado**, sin excepción; las pulsaciones se definen en tablas (A2–A4), nunca en código.
- **Escritorio:** controles nativos wx con nombre accesible; línea de estado leída por NVDA; pruebas manuales con NVDA + línea braille en cada release; add-on NVDA para br8.
- **Web:** WCAG 2.2 AA; MathML nativo con alternativa verbal (las etiquetas B2 sirven de `aria-label`); foco visible; sin trampas de foco; pruebas con NVDA+Chrome/Firefox.
- **Verbalización coherente:** la misma tabla B2 alimenta escritorio y web, de modo que el usuario oye lo mismo en ambos.
- **Tests automáticos de accesibilidad:** verificación de que toda entrada de `elementos.json` tiene etiqueta B2, glifo B1 y correspondencia br6/br8 (test de integridad de tablas), más axe-core sobre la web.

## 8. Fases de desarrollo

**Fase 0 — Cimientos (decisiones a+b+c).**
Definir `elementos.json` inicial (subconjunto: aritmética y álgebra elemental), esquemas pydantic de todas las tablas, esqueleto del proyecto, CI. *Sustituye al esqueleto Java actual (pom.xml, src/main/java), que se retira.*

**Fase 1 — MVP editor lineal (escritorio).**
Árbol de documento + cursor + undo; teclado por tablas (A2–A3); presentación gráfica B4 con glifos B1; verbalización B2 por línea de estado/NVDA; filtro A1 y exportación C1 (XHTML). → *Primer editor usable por un alumno.*

**Fase 2 — Braille e importación.**
Transcripción br6 con liblouis (B5) + ventana BR6 (B6) + exportación .BRA (C3); add-on NVDA y tabla br8 (B3); importación XHTML (D1); perfiles de usuario (A7); numpad (A4).

**Fase 3 — Web + cálculo.** *(hecha)*
Adaptador FastAPI reutilizando el núcleo completo; editor web accesible
(HTML semántico, MathML nativo, región `aria-live` única, teclas
canónicas en JS con cola de envíos); calculadora con aritmética exacta
de fracciones (A8) y bloqueo del profesor por perfil (A9), con mensajes
localizables (`mensajes.<lengua>.json`).
*Traslado a Fase 4:* PDF (C2), MP3 (C4), estructuras bidimensionales
(A10/B7) y ayuda (A6), para no mezclar interfaz web y generación de
formatos en una sola fase.

**Fase 4 — Química y extensibilidad.**
Módulos F (las tablas ya soportan categoría química); LaTeX (D2); API de scripts (A5); colecciones de fórmulas (E3); algoritmos 2D (A11/B8).

**Fase 5 — Ampliaciones E.**
Teclado braille virtual (E2), diccionario (E4), gráficas y sonificación (E10–E12), ejercicios y juegos (E13–E14), voz (E9), lengua de señas (B9), más lenguas (E6).

## 9. Flujo de ramas

- **`fase-N`**: una rama por fase del apartado 8 (`fase-0`, `fase-1`, ...); todo el desarrollo de la fase se hace ahí.
- **`dev`**: rama de integración y pruebas. Cada rama de fase se fusiona aquí y sobre ella se ejecutan la CI y las pruebas manuales de accesibilidad (NVDA, línea braille).
- **`main`**: solo recibe fusiones desde `dev` una vez validadas las pruebas.

## 10. Principios de mantenibilidad

1. **El núcleo no importa nada de UI** (se verifica con un test de imports).
2. **Comportamiento en datos, no en código:** añadir un signo, una tecla o una lengua = editar tablas, sin tocar Python.
3. **Un solo formato de tabla, un solo editor de tablas** (petición explícita del README).
4. **Cada transcriptor es un módulo independiente** con la misma interfaz (`transcribir(arbol) -> salida`), fácil de añadir/sustituir.
5. **Tipado estricto en el núcleo** (`mypy --strict`) y tests de integridad de tablas en CI: una tabla incoherente rompe la build, no al usuario.
