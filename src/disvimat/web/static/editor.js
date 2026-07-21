"use strict";
// Web editor client: captures key strokes, normalises them into the
// canonical format of the core tables and reflects the answer. It holds
// no editor logic: it only translates events and paints the state.

const editor = document.getElementById("editor");
const math = document.getElementById("math");
const line = document.getElementById("line");
const status = document.getElementById("status");
const announcement = document.getElementById("announcement");
const language = document.body.dataset.language || "en";

let session = null;
// Send queue: chains requests so the order of key strokes is preserved
// even when the user types faster than the network answers.
let queue = Promise.resolve();

// Browser special keys -> canonical table name.
const SPECIAL_KEYS = {
  ArrowLeft: "Left", ArrowRight: "Right", ArrowUp: "Up", ArrowDown: "Down",
  Home: "Home", End: "End", Tab: "Tab", Delete: "Delete",
  Backspace: "Backspace", Enter: "Return",
};

function canonicalKeys(event) {
  const modifiers = [];
  if (event.ctrlKey) modifiers.push("Ctrl");
  if (event.altKey) modifiers.push("Alt");
  if (event.shiftKey) modifiers.push("Shift");
  let name;
  if (event.key in SPECIAL_KEYS) {
    name = SPECIAL_KEYS[event.key];
  } else if (modifiers.length && !(modifiers.length === 1 && modifiers[0] === "Shift")) {
    if (event.key.length !== 1) return null;
    name = event.key.toUpperCase();
  } else {
    return null; // printable key without modifiers: handled as a character
  }
  return modifiers.length ? [...modifiers, name].join("+") : name;
}

function paint(view) {
  session = view.session;
  math.innerHTML = view.mathml || "";
  paintLine(view.text, view.position);
  status.textContent = view.speech;
  announce(view.speech);
}

// Announce in the live region. Clearing and setting again (on a timer,
// reliable even when the tab is not painting) makes the synthesiser repeat
// the message even when it is identical to the previous one.
function announce(text) {
  announcement.textContent = "";
  setTimeout(() => { announcement.textContent = text; }, 30);
}

function paintLine(text, position) {
  line.textContent = "";
  line.append(document.createTextNode(text.slice(0, position)));
  const caret = document.createElement("span");
  caret.className = "caret";
  line.append(caret);
  line.append(document.createTextNode(text.slice(position)));
}

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail || "error");
  }
  return response.json();
}

function start() {
  // The queue starts with session creation: the first key strokes wait for
  // a session instead of being lost.
  queue = request(`/api/session?language=${encodeURIComponent(language)}`, { method: "POST" })
    .then(paint)
    .catch((e) => { status.textContent = e.message; });
  return queue;
}

function sendKeys(keys, character) {
  queue = queue.then(async () => {
    if (!session) return;
    paint(await request(`/api/session/${session}/key`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys, character }),
    }));
  }).catch((e) => { status.textContent = e.message; });
  return queue;
}

editor.addEventListener("keydown", (event) => {
  const canonical = canonicalKeys(event);
  let keys = canonical;
  let character = null;
  if (!canonical) {
    if (event.key.length === 1 && !event.ctrlKey && !event.altKey) {
      character = event.key;
      keys = event.key; // tried first as a sign (e.g. "+")
    } else {
      return; // keys such as F5: keep the browser behaviour
    }
  }
  event.preventDefault();
  sendKeys(keys, character);
});

document.getElementById("btn-calculate").addEventListener("click", () => {
  sendKeys("Ctrl+Return", null);
  editor.focus();
});

document.getElementById("btn-export-xhtml").addEventListener("click", () => {
  window.open(`/api/session/${session}/export.xhtml`, "_blank", "noopener");
});

document.getElementById("btn-export-bra").addEventListener("click", () => {
  window.open(`/api/session/${session}/export.bra`, "_blank", "noopener");
});

document.getElementById("file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const xhtml = await file.text();
  try {
    paint(await request(`/api/session/${session}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ xhtml }),
    }));
  } catch (e) {
    status.textContent = e.message;
  }
  event.target.value = "";
  editor.focus();
});

editor.focus();
start();
