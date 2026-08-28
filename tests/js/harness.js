// Loading the real web client into a real DOM.
//
// editor.js is a plain script with top-level side effects: it grabs the
// page's elements and opens a session as soon as it runs. So it is not
// imported and picked apart — it is evaluated against the real index.html
// and then driven with real events, the way a browser drives it. Nothing
// here reimplements the client; a test that paraphrases the code it checks
// passes while the code is broken.

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const STATIC = path.join(ROOT, "src", "disvimat", "web", "static");
const DATA = path.join(ROOT, "data");

/** The browser half of keys_platform.json, in the shape app.py serves.
 *  The shape itself is pinned on the Python side by test_platform_keys.py. */
function platformKeys() {
  const table = JSON.parse(readFileSync(path.join(DATA, "keys_platform.json"), "utf8"));
  return JSON.stringify(
    table.entries.map((entry) => ({
      canonical: entry.canonical,
      key: entry.dom_key ?? null,
      code: entry.dom_code ?? null,
    })),
  );
}

/** The real page. Visible strings are irrelevant here, so each placeholder
 *  simply becomes its own name — only the key table has to be real. */
function page() {
  const template = readFileSync(path.join(STATIC, "index.html"), "utf8");
  const keys = platformKeys();
  return template.replace(/\{\{(\w+)\}\}/g, (_, name) => {
    if (name === "language") return "en";
    if (name === "platform_keys") return keys;
    return name;
  });
}

/** A recording stand-in for the server. */
export class FakeServer {
  constructor() {
    this.calls = [];
    this.text = "";
    this.position = 0;
    this.speech = "";
    this.mathml = "";
    /** Set to a status code to make the next call fail. */
    this.failWith = null;
    this.failDetail = "boom";
    /** Milliseconds each answer takes; a function of the call number. */
    this.delay = () => 0;
    this.inFlight = 0;
    this.maxInFlight = 0;
  }

  view() {
    return {
      session: "s1",
      text: this.text,
      position: this.position,
      speech: this.speech,
      mathml: this.mathml,
    };
  }

  fetch = async (url, options = {}) => {
    const body = options.body ? JSON.parse(options.body) : null;
    const index = this.calls.length;
    this.calls.push({ url: String(url), method: options.method ?? "GET", body });
    this.inFlight += 1;
    this.maxInFlight = Math.max(this.maxInFlight, this.inFlight);
    const wait = this.delay(index);
    if (wait) await new Promise((resolve) => setTimeout(resolve, wait));
    this.inFlight -= 1;
    if (this.failWith !== null) {
      const status = this.failWith;
      this.failWith = null;
      return {
        ok: false,
        status,
        json: async () => ({ detail: this.failDetail }),
      };
    }
    return { ok: true, status: 200, json: async () => this.view() };
  };

  /** Calls that sent a key stroke, in order. */
  strokes() {
    return this.calls.filter((c) => c.url.includes("/key")).map((c) => c.body);
  }

  sessions() {
    return this.calls.filter((c) => c.url.startsWith("/api/session?"));
  }
}

/** Build the page, stub the network and run the real client in it. */
export async function loadClient({ platformKeys = null } = {}) {
  const server = new FakeServer();
  let html = page();
  if (platformKeys) {
    // Let a test put an entry the shipped table does not have, so a
    // design decision that is currently unobservable can still be pinned.
    const open = '<script type="application/json" id="platform-keys">';
    const close = "</script>";
    const from = html.indexOf(open) + open.length;
    const to = html.indexOf(close, from);
    html = html.slice(0, from) + JSON.stringify(platformKeys) + html.slice(to);
  }
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "http://localhost/" });
  dom.window.fetch = server.fetch;
  dom.window.eval(readFileSync(path.join(STATIC, "editor.js"), "utf8"));
  await settle(dom);
  return { dom, server, window: dom.window, document: dom.window.document };
}

/** Let the client's promise queue and its announcement timer run out. */
export function settle(dom, ms = 60) {
  return new Promise((resolve) => dom.window.setTimeout(resolve, ms));
}

/** Send a keydown to the editor, the way a browser would. */
export function keydown(window, init) {
  const editor = window.document.getElementById("editor");
  editor.dispatchEvent(new window.KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    ...init,
  }));
}

export const el = (document, id) => document.getElementById(id);
