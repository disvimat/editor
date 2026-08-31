/**
 * Web editor client: captures key strokes, normalises them into the
 * canonical format of the core tables and reflects the answer. It holds no
 * editor logic: it only translates events and paints the state.
 */

import { HttpBackend } from "./http.js";
import { BackendGone, type Backend, type Export, type PlatformKey, type View } from "./types.js";

function need<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (element === null) throw new Error(`the page is missing #${id}`);
  return element as T;
}

const editor = need("editor");
const math = need("math");
const line = need("line");
const status = need("status");
const announcement = need("announcement");
const language = document.body.dataset["language"] ?? "en";
const backendGoneMessage = document.body.dataset["sessionExpired"] ?? "";

const backend: Backend = new HttpBackend(language);
let started = false;
// Send queue: chains requests so the order of key strokes is preserved even
// when the user types faster than the core answers.
let queue: Promise<void> = Promise.resolve();

// Canonical stroke names, served from data/keys_platform.json — the same
// table the desktop reads, so both interfaces answer a physical key the
// same way. BY_CODE is consulted first: it is the more specific of the two,
// and the keypad needs it (a browser reports the keypad's division key as
// key "/", exactly like the one on the main row).
const BY_KEY = new Map<string, string>();
const BY_CODE = new Map<string, string>();
for (const entry of JSON.parse(need("platform-keys").textContent ?? "[]") as PlatformKey[]) {
  if (entry.key !== null) BY_KEY.set(entry.key, entry.canonical);
  if (entry.code !== null) BY_CODE.set(entry.code, entry.canonical);
}

function specialKey(event: KeyboardEvent): string | null {
  return BY_CODE.get(event.code) ?? BY_KEY.get(event.key) ?? null;
}

function canonicalKeys(event: KeyboardEvent): string | null {
  const modifiers: string[] = [];
  if (event.ctrlKey) modifiers.push("Ctrl");
  if (event.altKey) modifiers.push("Alt");
  if (event.shiftKey) modifiers.push("Shift");
  let name = specialKey(event);
  if (name === null) {
    if (modifiers.length > 0 && !(modifiers.length === 1 && modifiers[0] === "Shift")) {
      if (event.key.length !== 1) return null;
      name = event.key.toUpperCase();
    } else {
      return null; // printable key without modifiers: handled as a character
    }
  }
  return modifiers.length > 0 ? [...modifiers, name].join("+") : name;
}

/**
 * ``message`` overrides the speech that comes with the view, so a single
 * announcement reaches the live region (announcing twice in a row makes the
 * synthesiser skip or clip the first one).
 */
function paint(view: View, message?: string): void {
  started = true;
  math.innerHTML = view.mathml;
  paintLine(view.text, view.position);
  const speech = message ?? view.speech;
  status.textContent = speech;
  announce(speech);
}

// Announce in the live region. Clearing and setting again (on a timer,
// reliable even when the tab is not painting) makes the synthesiser repeat
// the message even when it is identical to the previous one.
function announce(text: string): void {
  announcement.textContent = "";
  setTimeout(() => {
    announcement.textContent = text;
  }, 30);
}

function paintLine(text: string, position: number): void {
  line.textContent = "";
  line.append(document.createTextNode(text.slice(0, position)));
  const caret = document.createElement("span");
  caret.className = "caret";
  line.append(caret);
  line.append(document.createTextNode(text.slice(position)));
}

// Errors only reach the status bar, which is deliberately not a live region
// — so on its own it is silent. A core that has gone would therefore leave a
// screen reader user typing into an editor that has quietly stopped
// answering: start afresh instead and announce it out loud.
async function handleError(error: unknown): Promise<void> {
  if (error instanceof BackendGone) {
    try {
      paint(await backend.start(), backendGoneMessage);
      return;
    } catch (failure) {
      error = failure;
    }
  }
  const message = error instanceof Error ? error.message : String(error);
  status.textContent = message;
  announce(message);
}

function start(): Promise<void> {
  // The queue starts with the core coming up: the first key strokes wait
  // for it instead of being lost.
  queue = backend
    .start()
    .then((view) => paint(view))
    .catch((error: unknown) => {
      status.textContent = error instanceof Error ? error.message : String(error);
    });
  return queue;
}

function sendKeys(keys: string | null, character: string | null): Promise<void> {
  queue = queue
    .then(async () => {
      if (!started) return;
      paint(await backend.press(keys, character));
    })
    .catch(handleError);
  return queue;
}

editor.addEventListener("keydown", (event: KeyboardEvent) => {
  const canonical = canonicalKeys(event);
  let keys = canonical;
  let character: string | null = null;
  if (canonical === null) {
    if (event.key.length === 1 && !event.ctrlKey && !event.altKey) {
      character = event.key;
      keys = event.key; // tried first as a sign (e.g. "+")
    } else {
      return; // keys such as F5: keep the browser behaviour
    }
  }
  event.preventDefault();
  void sendKeys(keys, character);
});

need("btn-calculate").addEventListener("click", () => {
  void sendKeys("Ctrl+Return", null);
  editor.focus();
});

function onExport(id: string, what: Export): void {
  need(id).addEventListener("click", () => {
    void backend.save(what).catch(handleError);
  });
}

onExport("btn-save-dvm", "dvm");
onExport("btn-export-xhtml", "xhtml");
onExport("btn-export-braille", "brl");

function onUpload(id: string, load: (content: string) => Promise<View>): void {
  need<HTMLInputElement>(id).addEventListener("change", async (event: Event) => {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file === undefined) return;
    try {
      paint(await load(await file.text()));
    } catch (error) {
      await handleError(error);
    }
    input.value = "";
    editor.focus();
  });
}

onUpload("file-dvm", (content) => backend.open(content));
onUpload("file", (content) => backend.importXhtml(content));

editor.focus();
void start();
