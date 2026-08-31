/**
 * What the client and the core agree on.
 *
 * The web client holds no editor logic: it turns events into canonical key
 * strokes, hands them over and reflects the answer. These are the shapes
 * that cross that line.
 */

/** What the interface must reflect after each action (the core's Result). */
export interface View {
  readonly text: string;
  readonly position: number;
  readonly speech: string;
  readonly mathml: string;
}

/** One canonical stroke name and how this platform reports it. */
export interface PlatformKey {
  readonly canonical: string;
  readonly key: string | null;
  readonly code: string | null;
}

/** The formats a document can be handed back to the user in. */
export type Export = "dvm" | "xhtml" | "brl";

/** The editing core, wherever it happens to be running.
 *
 * Today it is a FastAPI server a fetch away. Under Pyodide it is Python
 * compiled to WebAssembly in this very tab, with no server and no session
 * at all. The page above this interface does not need to know which.
 */
export interface Backend {
  /** Begin, and give the initial state. */
  start(): Promise<View>;
  /** Apply a canonical stroke, a printable character, or both. */
  press(keys: string | null, character: string | null): Promise<View>;
  /** Open a `.dvm`, under the language and profile the document declares. */
  open(dvm: string): Promise<View>;
  /** Replace the content with an imported XHTML document. */
  importXhtml(xhtml: string): Promise<View>;
  /** The whole document in the given format, ready to be handed over. */
  exportAs(what: Export): Promise<string>;
}

/** The core is no longer there: the session timed out, or the server went. */
export class BackendGone extends Error {}
