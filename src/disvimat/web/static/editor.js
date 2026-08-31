(function() {
	//#region src/web-client/types.ts
	/** The core is no longer there: the session timed out, or the server went. */
	var BackendGone = class extends Error {};
	//#endregion
	//#region src/web-client/http.ts
	/**
	* Talking to the FastAPI server.
	*
	* One of two ways to reach the core, and the one that needs a session:
	* the document lives in the server's memory and this holds the id of it.
	* The Pyodide backend needs none of that, which is the point of keeping
	* the difference behind {@link Backend}.
	*/
	async function request(url, options = {}) {
		const response = await fetch(url, options);
		if (!response.ok) {
			const message = (await response.json().catch(() => ({}))).detail ?? response.statusText ?? "error";
			throw response.status === 404 ? new BackendGone(message) : new Error(message);
		}
		return await response.json();
	}
	function json(body) {
		return {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body)
		};
	}
	var HttpBackend = class {
		language;
		#session = null;
		constructor(language) {
			this.language = language;
		}
		async start() {
			return this.#adopt(await request(`/api/session?language=${encodeURIComponent(this.language)}`, { method: "POST" }));
		}
		async press(keys, character) {
			return this.#adopt(await request(this.#url("key"), json({
				keys,
				character
			})));
		}
		async open(dvm) {
			return this.#adopt(await request(this.#url("open"), json({ dvm })));
		}
		async importXhtml(xhtml) {
			return this.#adopt(await request(this.#url("import"), json({ xhtml })));
		}
		async exportAs(what) {
			const response = await fetch(this.#url(`export.${what}`));
			if (!response.ok) {
				const body = await response.json().catch(() => ({}));
				throw new Error(body.detail ?? response.statusText);
			}
			return await response.text();
		}
		#adopt(view) {
			this.#session = view.session;
			return view;
		}
		#url(suffix) {
			if (this.#session === null) throw new BackendGone("no session");
			return `/api/session/${this.#session}/${suffix}`;
		}
	};
	//#endregion
	//#region src/web-client/editor.ts
	/**
	* Web editor client: captures key strokes, normalises them into the
	* canonical format of the core tables and reflects the answer. It holds no
	* editor logic: it only translates events and paints the state.
	*/
	function need(id) {
		const element = document.getElementById(id);
		if (element === null) throw new Error(`the page is missing #${id}`);
		return element;
	}
	var editor = need("editor");
	var math = need("math");
	var line = need("line");
	var status = need("status");
	var announcement = need("announcement");
	var language = document.body.dataset["language"] ?? "en";
	var backendGoneMessage = document.body.dataset["sessionExpired"] ?? "";
	var backend = new HttpBackend(language);
	var started = false;
	var queue = Promise.resolve();
	var BY_KEY = /* @__PURE__ */ new Map();
	var BY_CODE = /* @__PURE__ */ new Map();
	for (const entry of JSON.parse(need("platform-keys").textContent ?? "[]")) {
		if (entry.key !== null) BY_KEY.set(entry.key, entry.canonical);
		if (entry.code !== null) BY_CODE.set(entry.code, entry.canonical);
	}
	function specialKey(event) {
		return BY_CODE.get(event.code) ?? BY_KEY.get(event.key) ?? null;
	}
	function canonicalKeys(event) {
		const modifiers = [];
		if (event.ctrlKey) modifiers.push("Ctrl");
		if (event.altKey) modifiers.push("Alt");
		if (event.shiftKey) modifiers.push("Shift");
		let name = specialKey(event);
		if (name === null) {
			if (modifiers.length > 0 && !(modifiers.length === 1 && modifiers[0] === "Shift")) {
				if (event.key.length !== 1) return null;
				name = event.key.toUpperCase();
			} else return null;
		}
		return modifiers.length > 0 ? [...modifiers, name].join("+") : name;
	}
	/**
	* ``message`` overrides the speech that comes with the view, so a single
	* announcement reaches the live region (announcing twice in a row makes the
	* synthesiser skip or clip the first one).
	*/
	function paint(view, message) {
		started = true;
		math.innerHTML = view.mathml;
		paintLine(view.text, view.position);
		const speech = message ?? view.speech;
		status.textContent = speech;
		announce(speech);
	}
	function announce(text) {
		announcement.textContent = "";
		setTimeout(() => {
			announcement.textContent = text;
		}, 30);
	}
	function paintLine(text, position) {
		line.textContent = "";
		line.append(document.createTextNode(text.slice(0, position)));
		const caret = document.createElement("span");
		caret.className = "caret";
		line.append(caret);
		line.append(document.createTextNode(text.slice(position)));
	}
	async function handleError(error) {
		if (error instanceof BackendGone) try {
			paint(await backend.start(), backendGoneMessage);
			return;
		} catch (failure) {
			error = failure;
		}
		const message = error instanceof Error ? error.message : String(error);
		status.textContent = message;
		announce(message);
	}
	function start() {
		queue = backend.start().then((view) => paint(view)).catch((error) => {
			status.textContent = error instanceof Error ? error.message : String(error);
		});
		return queue;
	}
	function sendKeys(keys, character) {
		queue = queue.then(async () => {
			if (!started) return;
			paint(await backend.press(keys, character));
		}).catch(handleError);
		return queue;
	}
	editor.addEventListener("keydown", (event) => {
		const canonical = canonicalKeys(event);
		let keys = canonical;
		let character = null;
		if (canonical === null) {
			if (event.key.length === 1 && !event.ctrlKey && !event.altKey) {
				character = event.key;
				keys = event.key;
			} else return;
		}
		event.preventDefault();
		sendKeys(keys, character);
	});
	need("btn-calculate").addEventListener("click", () => {
		sendKeys("Ctrl+Return", null);
		editor.focus();
	});
	/** Hand a file to the user, wherever the core it came from was running. */
	function download(name, content) {
		const link = document.createElement("a");
		link.href = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
		link.download = name;
		link.click();
		URL.revokeObjectURL(link.href);
	}
	function onExport(id, what) {
		need(id).addEventListener("click", () => {
			backend.exportAs(what).then((content) => download(`document.${what}`, content)).catch(handleError);
		});
	}
	onExport("btn-save-dvm", "dvm");
	onExport("btn-export-xhtml", "xhtml");
	onExport("btn-export-braille", "brl");
	function onUpload(id, load) {
		need(id).addEventListener("change", async (event) => {
			const input = event.target;
			const file = input.files?.[0];
			if (file === void 0) return;
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
	start();
	//#endregion
})();
