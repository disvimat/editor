# Estado del proyecto — qué existe y qué falta

**Idiomas:** [English](../en/STATUS.md) · [Español](../es/STATUS.md) · [Français](../fr/STATUS.md)

Auditoría frente a la lista de módulos del documento original del proyecto
([README.md](../BRIEF.es.md)). Actualizado el 21-07-2026.

Leyenda: **hecho** · **parcial** — usable pero incompleto · **pendiente** — sin empezar.

## Resumen

El editor ya sirve para **aritmética lineal y álgebra elemental**, en
**escritorio** (wxPython + NVDA) y en **web** (FastAPI + MathML nativo),
con voz en inglés, español y francés, braille de seis puntos en español,
importación y exportación XHTML, exportación .BRA y una calculadora de
aritmética exacta con bloqueo del profesor.

Las dos carencias mayores son el **add-on de NVDA** (líneas braille y voz
directa, módulos B3/E1) y las **estructuras bidimensionales** (matrices y
tablas, módulos A10/B7).

## A) Módulos de funcionamiento

| Módulo | Estado | Notas |
|---|---|---|
| A1 filtro Unicode/MathML → DisvimatEditor | **hecho** | Ida y vuelta verificada por tests |
| A2 signos y estructuras → pulsaciones | **hecho** | `keys_signs.json` |
| A3 comandos → pulsaciones | **parcial** | Tabla hecha; falta la gramática de *condicionantes* (el campo `condition` existe y las entradas condicionales se ignoran) |
| A4 teclas alternativas (bloque numérico) | **parcial** | Solo cuatro asignaciones; falta el esquema completo |
| A5 diseñador de scripts o add-ons | **pendiente** | El núcleo es ya una API pública limpia, que es el requisito previo |
| A6 archivo de ayuda (editable, por idioma) | **pendiente** | |
| A7 configurador de perfiles | **parcial** | `profiles.json` limita elementos por nivel y bloquea la calculadora; no hay interfaz para editar perfiles |
| A8 calculadora | **parcial** | Aritmética exacta de fracciones, precedencia, potencias y raíces exactas; sin variables, funciones ni trigonometría |
| A9 bloqueador de calculadora | **hecho** | `calculator: false` en el perfil (perfil `exam`) |
| A10 estructuras bidimensionales (tablas, matrices, determinantes) | **pendiente** | |
| A11 algoritmos bidimensionales | **pendiente** | |

## B) Módulos de presentación

| Módulo | Estado | Notas |
|---|---|---|
| B1 tabla de glifos | **hecho** | Con plantillas lineales para estructuras |
| B2 etiquetas / verbalización por idioma | **hecho** | Inglés, español y francés |
| B3 br8 (NVDA y líneas braille) | **pendiente** | Necesita un add-on de NVDA propio |
| B4 ventana de presentación gráfica | **hecho** | Control de texto nativo (escritorio) y MathML nativo (web) |
| B5 transcriptor br6 | **parcial** | El motor está completo y dirigido por tablas; **los valores españoles son provisionales**. La costura de [MathCAT](MATHCAT.md) ya está puesta y aporta braille CMU normativo en cuanto se compile su enlace, lo que sustituye a revisar nuestras tablas a mano |
| B6 ventana br6 | **parcial** | La ventana muestra y sigue la transcripción; falta navegar *dentro* de la ventana braille |
| B7 presentación de estructuras 2D | **pendiente** | |
| B8 presentación de algoritmos 2D | **pendiente** | |
| B9 mensajes en lengua de señas | **pendiente** | |

## C) Módulos de exportación

| Módulo | Estado | Notas |
|---|---|---|
| C1 XHTML | **hecho** | MathML que los navegadores renderizan y los lectores verbalizan |
| C2 PDF | **pendiente** | Previsto con WeasyPrint, reutilizando la exportación XHTML |
| C3 BRA (braille de 6 puntos) | **parcial** | Funciona; depende de la revisión braille, y la codificación ASCII es la NABCC provisional |
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

1. **No hay formato de documento propio.** No existe "guardar" / "abrir":
   los documentos viajan solo por importación y exportación XHTML. Hace
   falta un formato `.dvm` que conserve el árbol, el idioma y el perfil.
2. **Un documento es una sola línea.** El árbol contiene una secuencia de
   expresión; no hay párrafos, varias líneas ni texto mezclado con
   matemáticas.
3. **No hay add-on de NVDA**, así que la voz depende de la línea de estado
   (escritorio) y de la región `aria-live` (web), en vez de hablar
   directamente.
4. **Las sesiones web viven en memoria** y desaparecen al reiniciar el
   proceso; no hay autenticación ni persistencia.
5. **El braille necesita validación experta.** El motor está terminado; los
   valores no: deben contrastarse con la signografía matemática de la CBE
   antes de cualquier uso en el aula.
6. **Faltan pruebas automáticas de accesibilidad.** La integridad de las
   tablas se verifica en CI, pero no hay pasada de axe-core sobre la página
   web ni pruebas de NVDA guionizadas; la accesibilidad se verifica a mano.

## Próximos pasos sugeridos

1. **Compilar el enlace Python de MathCAT** ([MATHCAT.md](MATHCAT.md)). El
   adaptador y la política de reserva ya están escritos y probados, así que
   ese único paso activa el braille CMU normativo y la lectura de notación,
   y zanja la cuestión del braille sin revisar nuestras tablas a mano.
2. Add-on de NVDA para líneas braille y voz directa (B3/E1); el propio
   add-on de MathCAT es la implementación de referencia a seguir.
3. Formato de documento propio con guardar y abrir, y documentos de varias
   líneas.
4. Estructuras bidimensionales (A10/B7): matrices y tablas.
5. Exportación a PDF (C2) y MP3 (C4).
