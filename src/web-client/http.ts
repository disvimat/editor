/**
 * Talking to the FastAPI server.
 *
 * One of two ways to reach the core, and the one that needs a session:
 * the document lives in the server's memory and this holds the id of it.
 * The Pyodide backend needs none of that, which is the point of keeping
 * the difference behind {@link Backend}.
 */

import { BackendGone, type Backend, type Export, type View } from "./types.js";

interface SessionView extends View {
  readonly session: string;
}

interface ErrorDetail {
  readonly detail?: string;
}

async function request(url: string, options: RequestInit = {}): Promise<SessionView> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ErrorDetail;
    const message = body.detail ?? response.statusText ?? "error";
    throw response.status === 404 ? new BackendGone(message) : new Error(message);
  }
  return (await response.json()) as SessionView;
}

function json(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export class HttpBackend implements Backend {
  #session: string | null = null;

  constructor(private readonly language: string) {}

  async start(): Promise<View> {
    return this.#adopt(
      await request(`/api/session?language=${encodeURIComponent(this.language)}`, {
        method: "POST",
      }),
    );
  }

  async press(keys: string | null, character: string | null): Promise<View> {
    return this.#adopt(await request(this.#url("key"), json({ keys, character })));
  }

  async open(dvm: string): Promise<View> {
    return this.#adopt(await request(this.#url("open"), json({ dvm })));
  }

  async importXhtml(xhtml: string): Promise<View> {
    return this.#adopt(await request(this.#url("import"), json({ xhtml })));
  }

  async save(what: Export): Promise<void> {
    // The server sets Content-Disposition, so the browser offers the file.
    window.open(this.#url(`export.${what}`), "_blank", "noopener");
  }

  #adopt(view: SessionView): View {
    this.#session = view.session;
    return view;
  }

  #url(suffix: string): string {
    if (this.#session === null) throw new BackendGone("no session");
    return `/api/session/${this.#session}/${suffix}`;
  }
}
