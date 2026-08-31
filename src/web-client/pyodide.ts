/**
 * The core running in this tab, with no server at all.
 *
 * Pyodide is CPython compiled to WebAssembly, so the same Python package
 * the desktop runs is the one answering here — the same tables, the same
 * key resolution, the same exam restrictions read out of the document.
 * There is no session, because there is nothing to keep a session in: the
 * document is a file the student opens and saves.
 *
 * Everything crosses as a JSON string (see disvimat/bridge.py), so nothing
 * on this side has to marshal a Python object or remember to free a proxy.
 */

import { type Backend, type Export, type View } from "./types.js";

/** The Python object driving the editor: disvimat.bridge.Bridge. */
interface PyBridge {
  state(): string;
  press(keys: string | null, character: string | null): string;
  open(dvm: string): string;
  import_xhtml(xhtml: string): string;
  export(what: string): string;
}

/** The slice of Pyodide this needs, so a test can hand over a real one. */
export interface PyodideRuntime {
  loadPackage(names: string | string[]): Promise<unknown>;
  runPythonAsync(code: string): Promise<unknown>;
  runPython(code: string): unknown;
  FS: {
    mkdirTree(path: string): void;
    writeFile(path: string, data: Uint8Array): void;
  };
}

export interface PyodideOptions {
  /** Loads the runtime; in a browser this fetches pyodide.mjs. */
  readonly load: () => Promise<PyodideRuntime>;
  /** The disvimat wheel, already fetched. */
  readonly wheel: () => Promise<{ name: string; bytes: Uint8Array }>;
  readonly language: string;
  readonly profile?: string | null;
}

/**
 * The message to show for a failed call.
 *
 * Pyodide reports a Python exception as an Error carrying the traceback,
 * whose last line is `disvimat.bridge.BridgeError: what went wrong`. The
 * user should see the sentence, not the traceback.
 */
export function reason(error: unknown): string {
  const text = error instanceof Error ? error.message : String(error);
  const match = /(?:^|\n)[\w.]*(?:BridgeError|DvmError|ValueError):[ \t]*(.*)/.exec(text);
  return match?.[1]?.trim() || text.trim().split("\n").pop() || "error";
}

export class PyodideBackend implements Backend {
  #bridge: PyBridge | null = null;

  constructor(private readonly options: PyodideOptions) {}

  async start(): Promise<View> {
    const runtime = await this.options.load();
    await runtime.loadPackage("micropip");
    const { name, bytes } = await this.options.wheel();
    runtime.FS.mkdirTree("/wheels");
    // micropip reads the version out of the file name, so it is kept.
    runtime.FS.writeFile(`/wheels/${name}`, bytes);
    await runtime.runPythonAsync(`
import micropip
await micropip.install("pydantic")
await micropip.install("emfs:/wheels/${name}")
`);
    const profile = this.options.profile ?? null;
    runtime.runPython(`
from disvimat.bridge import Bridge
_bridge = Bridge(language=${quote(this.options.language)}, profile=${quote(profile)})
`);
    this.#bridge = runtime.runPython("_bridge") as PyBridge;
    return this.#view(this.#core().state());
  }

  async press(keys: string | null, character: string | null): Promise<View> {
    return this.#view(this.#core().press(keys, character));
  }

  async open(dvm: string): Promise<View> {
    return this.#view(this.#call(() => this.#core().open(dvm)));
  }

  async importXhtml(xhtml: string): Promise<View> {
    return this.#view(this.#call(() => this.#core().import_xhtml(xhtml)));
  }

  async exportAs(what: Export): Promise<string> {
    return this.#call(() => this.#core().export(what));
  }

  #core(): PyBridge {
    if (this.#bridge === null) throw new Error("the core has not started");
    return this.#bridge;
  }

  #call(run: () => string): string {
    try {
      return run();
    } catch (error) {
      throw new Error(reason(error));
    }
  }

  #view(payload: string): View {
    return JSON.parse(payload) as View;
  }
}

/** A Python literal for a string or None. */
function quote(value: string | null): string {
  return value === null ? "None" : JSON.stringify(value);
}
