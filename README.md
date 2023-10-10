# Editor científico accesible DISVIMAT

 ## Módulos

Carlos Daniel Ondó Angue
info@iataccess.org


Convendría que las tablas tuvieran un formato semejante que permitiera -o, al menos facilitara- el empleo de una única herramienta para su modificación.

Varias de las tablas podrían unificarse. Y, en consecuencia: también los módulos de modificación y la herramienta de edición.

Por "DisvimatEditor" se denomina el conjunto de elementos sobre los que operará el editor. Muy posiblemente: elementos MathML+Unicode español.

Importante. - Determinar previamente:
a) Formato y listado de elementos DisvimatEditor.
b) Formato de las tablas.
c) Editor de tablas.


A) Módulos de funcionamiento. -

A1 Filtro Unicode, MathML => DisvimatEditor (MathML+Unicode español)
Establece la correspondencia entre los códigos XHTML y los signos/códigos empleados por el editor.

A2 Tabla signos y estructuras DisvimatEditor (y tipificación) => Teclas combinadas.
Establece correspondencia entre signos a editar y pulsaciones.

A3 Tabla comandos DisvimatEditor (con condicionantes): navegación, selección, ejecución...  => Teclas combinadas
Establece correspondencia entre comandos y pulsaciones.

A4 Tabla signos y estructuras y comandos DisvimatEditor (y tipificación) => Teclas alternativas (con bloque numérico).
Establece correspondencia entre signos a editar y comandos a ejecutar, pulsaciones sobre el "bloque numérico".

A5 Diseñador de scripts o add-on's.
Facilitar la programación de acciones de diverso tipo sobre el editor en el lenguaje a decidir.

A6 Ayuda. Previsión según lengua.
Editor para el archivo de ayuda (Modificable en contenido y estructura).

A7 Configurador de perfiles de usuario. Previsión: según lengua.
Establece los signos y estructuras y comandos a ejecutar en cada nivel de usuario. Posibilidad de ligarlo a los módulos de correspondencia con pulsaciones.

A8 Módulo/s de calculadoras.
Calculadora/s ligada/s al editor (niveles)

A9 Bloqueador/limitador de calculadora
Limita y/o bloquea (por el profesor) las posibilidades de uso de la/ calculafora/s.

A10 Módulo de tratamiento de estructuras bidimensionales (tablas, matrices, determinantes).
Permite el tratamiento de las estructuras bidimensionales en ventana externa (pero ligada al editor).

A11 Módulo/s de tratamiento de algoritmos bidimensionales.
Permite el tratamiento de algoritmos bidimensionales en ventana externa (pero ligada al editor).


B) Módulos de presentación. -

B1 Tabla Editor_Disvimat => glifos DisvimatEditor
Permite la edición y asignación de glifos a los signos/estructuras del editor (lineal).

B2 Tablas DisvimatEditor => Etiquetas de nomenclatura (presentación en listas, línea de estado y verbalizaciones). Versiones según lengua.
Permite la edición y asignación de etiquetas textuales para lectura por la síntesis de voz a los signos/estructuras del editor (lineal).

B3 Tabla DisvimatEditor => br8 (NVDA y líneas braille). Previsión: según lengua.
Establece correspondencia entre signos editados (glifos) y signos br8 a presentar por línea braille. (Condicionantes NVDA)

B4 Presentación gráfica (ordinaria). Previsión font.
Ventana inserta de presentación/interacción de signos y expresiones editadas.

B5 Transcriptor DisvimatEditor => br6 (Ascii128). Previsión: según lengua.
Transcribe los signos y expresiones (matemáticas, de texto, de Química) en expresiones braille de 6 puntos. A presentar por pantalla, por línea braille y exportar.

B6 Módulo de presentación y navegación en ventana BR6.
Edita en ventana independiente la transcripción a braille de 6 puntos del contenido del documento en uso. Navegable.

B7 Módulo de presentación de estructuras bidimensionales.
A incluir en el correspondiente módulo de "tratamiento".

B8 Módulo/s de presentación de algoritmos bidimensionales.
A incluir en el correspondiente módulo de "tratamiento".

B9 Módulo de presentación de mensajes en lengua de señas.


C) Módulos de exportación. -

C1 Exportación de archivos .XHTML. Previsión de font y formatos.
Ligado al módulo de presentación/interacción por ventana gráfica ordinaria.

C2 Exportación de archivos .PDF. Previsión de font y formatos.
Ligado al módulo de presentación/interacción por ventana gráfica ordinaria.

C3 Exportación de archivos .BRA (braille de 6 puntos). Previsión: según lengua.
Ligado al módulo de transcripción a braille de 6 puntos. Con previsión de formato.

C4 Exportación de archivos .MP3. Previsión de parámetros y formatos. Previsión: según lengua.


D) Módulos de importación. -

E1 Importación de archivos .XHTML. Previsión de nuevos signos DisvimatEditor y transcripción de expresiones.
Ligado con módulo para filtro MathML => signos/estructuras DisvimatEditor.

E2 Importación de archivos en formatos Látex. Previsión de nuevos signos DisvimatEditor y transcripción de expresiones.


E) Módulos de ampliación:

E1 Entrada de información y control del sistema mediante “teclado BR8 de línea braille” (con NVDA). Previsión según modelo de línea braille.
Permitiría editar signos/estructuras y controlar el programa mediante teclado BR8 de líneas braille (condicionado a tabla de pulsaciones.

E2 Entrada de información y control del sistema mediante “teclado braille virtual" (definido en teclado QWERTY). Previsión de configuración de combinaciones de teclas y lengua.
Editor de signos/estructuras y controles del programa mediante teclado BR8 definido por correspondencia de teclas y funcionamiento de pulsaciones. 

E3 Colección/es (ampliable) de fórmulas y expresiones matemáticas.
Editor de archivo con índice y buscador. Ligado al editor.

E4 Diccionario de términos matemáticos

E5 Almacén de resultados matemáticos (teoremas)

E6 Versiones de interfaz y verbalización en otras lenguas (Internacionalización).

E7 Introducción de expresiones matemáticas manuscritas (ver: panel de entrada matemática de MS Windows).

E8 Creación de símbolos matemáticos personalizados.

E9 Control del software por voz. Control del programa. Introducción de fórmulas o expresiones matemáticas.

E10 Edición (generación) de gráficas de Estadística;
Presentación en ventana exterior, a partir de tabla de valores (ver Excel).

E11 Edición (generación) de gráficas reales de variable real (generales).
Presentación en ventana exterior, a partir de expresión algebraica (ver Excel).

E12 Sonificación de gráficos de Estadística y funciones reales.
Ver "MathTrax".

E13 Diseño de ejercicios interactivos.
Herramienta de autor para generación de documentos interactivos con recurso a posibilidades calculatorias del programa.

E14 Juegos matemáticos interactivos
Sudokus, cuadrados mágicos, cuadros latinos y grecolatinos, pirámides y montañas, caza de números...


F) Versión como editor de Química.

F1 Editor de expresiones lineales de Química.

F2 Editor de expresiones bidimensionales de Química.

F3 Editor de expresiones 3D de Química.

F4 Calculadora de pesos moleculares.

F5 Tabla periódica de elementos químicos.
Editor de tabla periódica de Mendeleieff, con posibilidad de selección de valores por elemento. Consulta a ficha configurable de elemento.

F6 Galería editable y ampliable de fórmulas químicas.