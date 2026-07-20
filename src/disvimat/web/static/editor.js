"use strict";
// Cliente del editor web: captura las teclas, las normaliza al formato
// canónico de las tablas del núcleo y refleja la respuesta. No contiene
// ninguna lógica del editor: solo traduce eventos y pinta el estado.

const editor = document.getElementById("editor");
const math = document.getElementById("math");
const linea = document.getElementById("linea");
const estado = document.getElementById("estado");
const anuncio = document.getElementById("anuncio");

let sesion = null;
// Cola de envíos: encadena las peticiones para que el orden de las
// pulsaciones se conserve aunque el usuario teclee más rápido que la red.
let cola = Promise.resolve();

// Teclas especiales del navegador -> nombre canónico de las tablas.
const ESPECIALES = {
  ArrowLeft: "Left", ArrowRight: "Right", ArrowUp: "Up", ArrowDown: "Down",
  Home: "Home", End: "End", Tab: "Tab", Delete: "Delete",
  Backspace: "Backspace", Enter: "Return",
};

function combinacionCanonica(evento) {
  const mods = [];
  if (evento.ctrlKey) mods.push("Ctrl");
  if (evento.altKey) mods.push("Alt");
  if (evento.shiftKey) mods.push("Shift");
  let nombre;
  if (evento.key in ESPECIALES) {
    nombre = ESPECIALES[evento.key];
  } else if (mods.length && !(mods.length === 1 && mods[0] === "Shift")) {
    if (evento.key.length !== 1) return null;
    nombre = evento.key.toUpperCase();
  } else {
    return null; // tecla imprimible sin modificadores: se trata como carácter
  }
  return mods.length ? [...mods, nombre].join("+") : nombre;
}

function pintar(vista) {
  sesion = vista.sesion;
  math.innerHTML = vista.mathml || "";
  pintarLinea(vista.texto, vista.posicion);
  estado.textContent = vista.verbalizacion;
  anunciar(vista.verbalizacion);
}

// Anuncia en la región viva. Limpiar y volver a poner (en un temporizador,
// fiable aunque la pestaña no esté pintando) fuerza a la síntesis a repetir
// incluso cuando el texto es idéntico al anterior.
function anunciar(texto) {
  anuncio.textContent = "";
  setTimeout(() => { anuncio.textContent = texto; }, 30);
}

function pintarLinea(texto, posicion) {
  linea.textContent = "";
  linea.append(document.createTextNode(texto.slice(0, posicion)));
  const caret = document.createElement("span");
  caret.className = "caret";
  linea.append(caret);
  linea.append(document.createTextNode(texto.slice(posicion)));
}

async function peticion(url, opciones) {
  const respuesta = await fetch(url, opciones);
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({ detail: respuesta.statusText }));
    throw new Error(detalle.detail || "error");
  }
  return respuesta.json();
}

function iniciar() {
  // Arranca la cola con la creación de sesión: las primeras pulsaciones
  // esperan a que exista sesión en lugar de perderse.
  cola = peticion("/api/sesion", { method: "POST" })
    .then(pintar)
    .catch((e) => { estado.textContent = e.message; });
  return cola;
}

function enviarTecla(teclas, caracter) {
  // Encadena en la cola: no se envía la siguiente hasta pintar la anterior.
  cola = cola.then(async () => {
    if (!sesion) return;
    pintar(await peticion(`/api/sesion/${sesion}/tecla`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ teclas, caracter }),
    }));
  }).catch((e) => { estado.textContent = e.message; });
  return cola;
}

editor.addEventListener("keydown", (evento) => {
  const canonica = combinacionCanonica(evento);
  let teclas = canonica;
  let caracter = null;
  if (!canonica) {
    if (evento.key.length === 1 && !evento.ctrlKey && !evento.altKey) {
      caracter = evento.key;
      teclas = evento.key; // se intenta primero como signo (p. ej. "+")
    } else {
      return; // teclas como F5: dejar el comportamiento del navegador
    }
  }
  evento.preventDefault();
  enviarTecla(teclas, caracter);
});

document.getElementById("btn-calcular").addEventListener("click", () => {
  enviarTecla("Ctrl+Return", null);
  editor.focus();
});

document.getElementById("btn-exportar-xhtml").addEventListener("click", () => {
  window.open(`/api/sesion/${sesion}/exportar.xhtml`, "_blank", "noopener");
});

document.getElementById("btn-exportar-bra").addEventListener("click", () => {
  window.open(`/api/sesion/${sesion}/exportar.bra`, "_blank", "noopener");
});

document.getElementById("archivo").addEventListener("change", async (evento) => {
  const fichero = evento.target.files[0];
  if (!fichero) return;
  const xhtml = await fichero.text();
  try {
    pintar(await peticion(`/api/sesion/${sesion}/importar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ xhtml }),
    }));
  } catch (e) {
    estado.textContent = "No se pudo importar: " + e.message;
  }
  evento.target.value = "";
  editor.focus();
});

editor.focus();
iniciar().catch((e) => { estado.textContent = e.message; });
