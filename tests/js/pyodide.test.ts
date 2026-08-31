/**
 * The core running in WebAssembly, driven through the same interface the
 * HTTP client implements.
 *
 * This is the real thing: real Pyodide, the real wheel built from this
 * source tree, the real disvimat.bridge.Bridge. Pyodide runs under Node as
 * well as in a browser, so what would otherwise need a headless browser is
 * an ordinary test here.
 *
 * The wheel has to be built first (`python -m build --wheel`). Without it
 * these skip — unless DISVIMAT_REQUIRE_WHEEL is set, as CI does, where a
 * skip would quietly report a green build for untested code.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";
import { beforeAll, describe, expect, test } from "vitest";
import { PyodideBackend, reason, type PyodideRuntime } from "../../src/web-client/pyodide.js";
import type { View } from "../../src/web-client/types.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DIST = path.join(ROOT, "dist");

function wheelPath(): string | null {
  if (!existsSync(DIST)) return null;
  const found = readdirSync(DIST).find((name) => name.endsWith(".whl"));
  return found === undefined ? null : path.join(DIST, found);
}

const wheel = wheelPath();
if (wheel === null && process.env["DISVIMAT_REQUIRE_WHEEL"]) {
  throw new Error("no wheel in dist/: run `python -m build --wheel` before the tests");
}

function backend(language: string, profile: string | null = null): PyodideBackend {
  return new PyodideBackend({
    load: async () => (await loadPyodide()) as unknown as PyodideRuntime,
    wheel: async () => ({
      name: path.basename(wheel as string),
      bytes: new Uint8Array(readFileSync(wheel as string)),
    }),
    language,
    profile,
  });
}

describe.skipIf(wheel === null)("the core in WebAssembly", () => {
  let core: PyodideBackend;
  let first: View;

  beforeAll(async () => {
    core = backend("es");
    first = await core.start();
  }, 300_000);

  test("it starts on an empty document", () => {
    expect(first.text).toBe("");
    expect(first.mathml).toContain("<math");
  });

  test("a key stroke edits, and comes back spoken in the document's language", async () => {
    const view = await core.press("Ctrl+F", null);
    expect(view.text).toBe("(□∕□)");
    expect(view.speech).toContain("fracción");
  });

  test("the same canonical names the tables use reach the core", async () => {
    const fresh = backend("en");
    await fresh.start();
    // NumDivide is the keypad binding the browser could not send until the
    // platform table existed; here it goes straight into Python.
    expect((await fresh.press("NumDivide", null)).text).toBe("(□∕□)");
  }, 300_000);

  test("an exam file opens with its restrictions, with no server involved", async () => {
    const teacher = backend("es", "exam");
    await teacher.start();
    for (const key of ["1", "+", "2"]) await teacher.press(key, key);
    const exam = await teacher.exportAs("dvm");

    const student = backend("es");
    await student.start();
    const opened = await student.open(exam);
    expect(opened.text).toBe("1+2");
    const answer = await student.press("Ctrl+Return", null);
    expect(answer.speech).not.toContain("3");
  }, 600_000);

  test("a malformed document reports its reason, not a traceback", async () => {
    await expect(core.open("{not a document")).rejects.toThrow(/dvm|json|document/i);
    await expect(core.open("{not a document")).rejects.not.toThrow(/Traceback/);
  });
});

describe("reading a Python failure", () => {
  test("the sentence is kept and the traceback dropped", () => {
    const traceback = [
      "Traceback (most recent call last):",
      '  File "<exec>", line 1, in <module>',
      "disvimat.bridge.BridgeError: no braille source for language 'fr'",
    ].join("\n");
    expect(reason(new Error(traceback))).toBe("no braille source for language 'fr'");
  });

  test("anything else is passed through rather than swallowed", () => {
    expect(reason(new Error("network down"))).toBe("network down");
  });
});
