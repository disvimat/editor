# Estado del proyecto — qué existe y qué falta

**Idiomas:** [English](../en/STATUS.md) · [Español](../es/STATUS.md) · [Français](../fr/STATUS.md)

Auditoría frente a la lista de módulos del documento original del proyecto
([README.md](../BRIEF.es.md)). Actualizado el 21-07-2026.

Leyenda: **hecho** · **parcial** — usable pero incompleto · **pendiente** — sin empezar.

## Resumen

El editor ya sirve para **aritmética lineal y álgebra elemental**, en
**escritorio** (wxPython + NVDA) y en **web** (FastAPI + MathML nativo),
con voz en inglés, español y francés, braille de seis puntos en español,
importación y exportación XHTML, exportación braille Unicode y una calculadora de
aritmética exacta con bloqueo del profesor.

Las dos carencias mayores son el **add-on de NVDA** (líneas braille y voz
directa, módulos B3/E1) y las **estructuras bidimensionales** (matrices y
tablas, módulos A10/B7).

## A) Módulos de funcionamiento

| Módulo | Estado | Notas |
|---|---|---|
| A1 filtro Unicode/MathML → DisvimatEditor | **hecho** | Ida y vuelta verificada por tests |
| A2 signos y estructuras → pulsaciones | **hecho** | `keys_signs.json`; las pulsaciones pueden ser **acordes** (`"Ctrl+G, P"`, la convención de EdiCo) resueltos por una pequeña máquina de estados |
| A3 comandos → pulsaciones | **parcial** | Tabla hecha; falta la gramática de *condicionantes* (el campo `condition` existe y las entradas condicionales se ignoran) |
| — perfiles de teclado y reasignación del usuario | **hecho** | Los perfiles de compatibilidad (`data/keymaps/`, Lambda/EdiCo) se cargan sobre las tablas por defecto; un mapa de teclas por usuario (`$DISVIMAT_USER_KEYMAP` o `~/.disvimat/user_keys.json`) se carga el último y gana. La herramienta `rebind` reasigna una tecla con detección de conflictos (rechaza comandos inexistentes y solapamientos de acordes, avisa al robar una pulsación) |
| A4 teclas alternativas (bloque numérico) | **parcial** | Solo cuatro asignaciones; falta el esquema completo. Ya funcionan en **las dos** interfaces: el navegador informa del `/` del bloque numérico como tecla `"/"`, igual que el de la fila principal, así que la web lo leía como signo de división mientras el escritorio insertaba una fracción. Ambos adaptadores sacan ahora los nombres de `keys_platform.json` |
| A5 diseñador de scripts o add-ons | **hecho** | [Add-ons](ADDONS.md): una función `register(registry)` añade comandos (tecla, voz, código) y exportadores, descubiertos como paquetes instalados o como `.py` en `DISVIMAT_ADDONS`. Los fallos quedan contenidos |
| A6 archivo de ayuda (editable, por idioma) | **pendiente** | |
| A7 configurador de perfiles | **parcial** | `profiles.json` limita elementos por nivel y bloquea la calculadora; no hay interfaz para editar perfiles |
| A8 calculadora | **parcial** | Aritmética exacta de fracciones, precedencia, potencias y raíces exactas; sin variables, funciones ni trigonometría |
| A9 bloqueador de calculadora | **hecho** | `calculator: false` en el perfil (perfil `exam`) |
| A10 estructuras bidimensionales (tablas, matrices, determinantes) | **parcial** | Matrices: insertar (`Ctrl+Shift+M`), navegación por rejilla, añadir fila/columna (`Alt+Abajo`/`Alt+Derecha`), lectura por filas, MathML `<mtable>` ida y vuelta, `.dvm`. Determinantes/tablas reutilizan el mismo nodo |
| A11 algoritmos bidimensionales | **pendiente** | |

## B) Módulos de presentación

| Módulo | Estado | Notas |
|---|---|---|
| B1 tabla de glifos | **hecho** | Con plantillas lineales para estructuras |
| B2 etiquetas / verbalización por idioma | **hecho** | Voz de edición en inglés, español y francés (nuestras tablas); lectura de la expresión completa vía [MathCAT](MATHCAT.md) en inglés y español |
| B3 br8 (NVDA y líneas braille) | **parcial** | El escritorio habla cada acción por el lector de pantalla y envía la línea actual a la línea braille conectada, mediante el controlador de NVDA/JAWS (`accessible_output2`). Falta la *entrada* BR8 y un add-on propio |
| B4 ventana de presentación gráfica | **hecho** | Control de texto nativo (escritorio) y MathML nativo (web) |
| B5 transcriptor braille | **hecho (motores externos)** | El braille sale de una escalera ([BRAILLE.md](BRAILLE.md)): [MathCAT](MATHCAT.md) para matemáticas (CMU, UEB), [liblouis](BRAILLE.md) para texto (tablas oficiales, p. ej. francés), nuestras tablas `br6` como último recurso. Verificado en Python 3.13 de 64 bits |
| B6 ventana br6 | **parcial** | La ventana muestra y sigue la transcripción; falta navegar *dentro* de la ventana braille |
| B7 presentación de estructuras 2D | **parcial** | Forma lineal `[a,b;c,d]` en pantalla y `<mtable>` nativo en web; falta una ventana 2D dedicada |
| B8 presentación de algoritmos 2D | **pendiente** | |
| B9 mensajes en lengua de señas | **pendiente** | |

## C) Módulos de exportación

| Módulo | Estado | Notas |
|---|---|---|
| C1 XHTML | **hecho** | MathML que los navegadores renderizan y los lectores verbalizan |
| C2 PDF | **pendiente** | Previsto con WeasyPrint, reutilizando la exportación XHTML |
| C3 exportación braille | **hecho** | Exporta braille Unicode (U+2800…, `.brl`, UTF-8) del motor activo (MathCAT / liblouis / tablas). La conversión a ASCII sigue en el código pero ya no es el formato de exportación |
| C4 MP3 | **pendiente** | |

## D) Módulos de importación

| Módulo | Estado | Notas |
|---|---|---|
| D1 XHTML | **hecho** | Deshacible; errores claros ante contenido no soportado |
| D2 LaTeX | **pendiente** | |

## E) Módulos de ampliación

| Módulo | Estado |
|---|---|
| E6 internacionalización | **hecho** — inglés, español, francés; añadir un idioma es editar JSON |
| E1 entrada por teclado br8 de línea braille | **pendiente** |
| E2 teclado braille virtual | **pendiente** |
| E3 colecciones de fórmulas | **pendiente** |
| E4 diccionario matemático | **pendiente** |
| E5 almacén de teoremas | **pendiente** |
| E7 entrada manuscrita | **pendiente** |
| E8 símbolos personalizados | **pendiente** |
| E9 control por voz | **pendiente** |
| E10–E11 gráficas estadísticas y de funciones | **pendiente** |
| E12 sonificación de gráficas | **pendiente** |
| E13 ejercicios interactivos | **pendiente** |
| E14 juegos matemáticos | **pendiente** |

## F) Versión como editor de química

F1–F6 están todos **pendientes**. El terreno está preparado: el catálogo ya
lleva un campo `category`, así que los signos y estructuras de química se
añaden como datos, no como código.

## Carencias transversales que conviene conocer

No están en la lista original de módulos, pero importan para el uso real:

1. ~~No hay formato de documento propio.~~ **Hecho:** el formato `.dvm`
   ([DOCUMENT.md](DOCUMENT.md)) guarda y reabre el árbol exacto, con el
   idioma y el perfil con que se escribió. Guardar/Abrir en escritorio y web.
2. ~~Un documento es una sola línea.~~ **Hecho:** los documentos son ahora
   **multilínea** — `Intro` crea línea, las flechas se mueven entre líneas
   en el nivel superior, y cada línea se presenta, se lee y se transcribe
   por separado.
3. ~~No hay add-on de NVDA, así que la voz depende de la línea de estado.~~
   **Corregido:** el escritorio ya habla cada acción por el lector de
   pantalla y envía braille a la línea. Sigue faltando un add-on propio
   para la *entrada* por teclado BR8 (E1).
4. **Las sesiones web viven en memoria.** Ya no crecen sin límite: caducan
   por inactividad (`DISVIMAT_SESSION_TTL`, dos horas por defecto) y su
   número está acotado (`DISVIMAT_MAX_SESSIONS`, 500), descartando la menos
   usada. Cuando una sesión caduca la página abre otra y **lo anuncia por
   voz**, para no dejar al usuario escribiendo en un editor mudo. Sigue sin
   haber autenticación ni persistencia: al reiniciar el proceso se pierde
   el documento.
5. **El braille necesita validación experta.** El motor está terminado; los
   valores no: deben contrastarse con la signografía matemática de la CBE
   antes de cualquier uso en el aula.
6. **Faltan pruebas automáticas de accesibilidad.** La integridad de las
   tablas se verifica en CI, pero no hay pasada de axe-core sobre la página
   web ni pruebas de NVDA guionizadas; la accesibilidad se verifica a mano.

## Próximos pasos sugeridos

El braille/voz (MathCAT + liblouis) y la capa de documento (`.dvm`,
multilínea) están hechos. Lo que queda, por orden de impacto:

1. Add-on de NVDA para líneas braille y voz directa (B3/E1); el propio
   add-on de MathCAT es la implementación de referencia a seguir.
2. Estructuras bidimensionales (A10/B7): matrices y tablas.
3. Exportación a PDF (C2) y MP3 (C4).
4. Texto y matemáticas mezclados en un documento (entonces el braille de
   texto de liblouis cubre las partes de prosa).
