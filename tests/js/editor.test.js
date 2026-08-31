// The web client: what a screen reader is handed, and which stroke is sent.
//
// This file had no tests at all. Two changes went into it recently — the
// numeric keypad reaching the core, and recovering from an expired session
// out loud — and both had to be checked by hand in a browser. Now they are
// checked here.

import { describe, expect, test } from "vitest";
import { el, keydown, loadClient, settle } from "./harness.js";

describe("turning a key event into a canonical stroke", () => {
  test("the keypad's division key is told apart from the main row", async () => {
    // A browser reports both as key "/"; only `code` distinguishes them.
    const { window, server, dom } = await loadClient();
    keydown(window, { key: "/", code: "NumpadDivide" });
    await settle(dom);
    expect(server.strokes()).toEqual([{ keys: "NumDivide", character: null }]);
  });

  test("the main row's slash goes as a character", async () => {
    const { window, server, dom } = await loadClient();
    keydown(window, { key: "/", code: "Slash" });
    await settle(dom);
    expect(server.strokes()).toEqual([{ keys: "/", character: "/" }]);
  });

  test("a modified letter keeps its modifiers and is upper cased", async () => {
    const { window, server, dom } = await loadClient();
    keydown(window, { key: "f", code: "KeyF", ctrlKey: true });
    await settle(dom);
    expect(server.strokes()).toEqual([{ keys: "Ctrl+F", character: null }]);
  });

  test("a named key comes through under its table name", async () => {
    const { window, server, dom } = await loadClient();
    keydown(window, { key: "ArrowLeft", code: "ArrowLeft" });
    await settle(dom);
    expect(server.strokes()).toEqual([{ keys: "Left", character: null }]);
  });

  test("the keypad still types digits", async () => {
    const { window, server, dom } = await loadClient();
    keydown(window, { key: "1", code: "Numpad1" });
    await settle(dom);
    expect(server.strokes()).toEqual([{ keys: "1", character: "1" }]);
  });

  test("keys the editor does not claim are left to the browser", async () => {
    const { window, server, dom } = await loadClient();
    keydown(window, { key: "F5", code: "F5" });
    await settle(dom);
    expect(server.strokes()).toEqual([]);
  });

  test("one stroke at a time, however fast the user types", async () => {
    // The answers get quicker as they go, so a client that fired them all
    // at once would have them come back out of order. The queue is what
    // stops that: only one request may be in flight at a time.
    const { window, server, dom } = await loadClient();
    server.delay = (index) => Math.max(5, 50 - index * 10);
    for (const key of ["1", "2", "3", "4"]) {
      keydown(window, { key, code: "Digit" + key });
    }
    await settle(dom, 400);
    expect(server.strokes().map((s) => s.keys)).toEqual(["1", "2", "3", "4"]);
    expect(server.maxInFlight).toBe(1);
  });

  test("a code beats a key when both name the same physical key", async () => {
    // `code` is the more specific of the two and has to win: that is what
    // lets the keypad be told apart from the main row at all. No shipped
    // entry sets both, so the table is overridden to pin the decision.
    const { window, server, dom } = await loadClient({
      platformKeys: [
        { canonical: "Ambiguous", key: "x", code: null },
        { canonical: "Specific", key: null, code: "KeyX" },
      ],
    });
    keydown(window, { key: "x", code: "KeyX" });
    await settle(dom);
    expect(server.strokes()).toEqual([{ keys: "Specific", character: null }]);
  });
});

describe("reflecting the answer", () => {
  test("the expression, the caret and the status line are painted", async () => {
    const { window, document, server, dom } = await loadClient();
    server.text = "1+2";
    server.position = 2;
    server.speech = "plus";
    server.mathml = "<math><mn>1</mn></math>";
    keydown(window, { key: "+", code: "Equal" });
    await settle(dom);

    expect(el(document, "math").innerHTML).toBe("<math><mn>1</mn></math>");
    expect(el(document, "status").textContent).toBe("plus");
    const line = el(document, "line");
    expect(line.textContent).toBe("1+2");
    expect(line.querySelector(".caret")).not.toBeNull();
  });

  test("every action reaches the live region", async () => {
    const { window, document, server, dom } = await loadClient();
    server.speech = "fraction, blank 1";
    keydown(window, { key: "f", code: "KeyF", ctrlKey: true });
    await settle(dom);
    expect(el(document, "announcement").textContent).toBe("fraction, blank 1");
  });

  test("the same message twice is announced twice", async () => {
    // The region is cleared and set again on a timer precisely so the
    // synthesiser repeats an identical message instead of staying silent.
    const { window, document, server, dom } = await loadClient();
    const announcement = el(document, "announcement");
    server.speech = "plus";
    keydown(window, { key: "+", code: "Equal" });
    await settle(dom);
    expect(announcement.textContent).toBe("plus");

    let cleared = false;
    const observer = new window.MutationObserver(() => {
      if (announcement.textContent === "") cleared = true;
    });
    observer.observe(announcement, { childList: true, characterData: true, subtree: true });
    keydown(window, { key: "+", code: "Equal" });
    await settle(dom);
    observer.disconnect();

    expect(cleared).toBe(true);
    expect(announcement.textContent).toBe("plus");
  });
});

describe("when the session is gone", () => {
  test("a new one is opened and the user is told out loud", async () => {
    const { window, document, server, dom } = await loadClient();
    const before = server.sessions().length;
    server.failWith = 404;
    keydown(window, { key: "1", code: "Digit1" });
    await settle(dom, 120);

    expect(server.sessions().length).toBe(before + 1);
    // The status bar is deliberately not a live region, so the message has
    // to reach the announcement region or nobody hears it.
    expect(el(document, "announcement").textContent).toBe("session_expired");
  });

  test("any other error is spoken too, not only shown", async () => {
    const { window, document, server, dom } = await loadClient();
    server.failWith = 400;
    server.failDetail = "unsupported content";
    keydown(window, { key: "1", code: "Digit1" });
    await settle(dom, 120);

    expect(el(document, "status").textContent).toBe("unsupported content");
    expect(el(document, "announcement").textContent).toBe("unsupported content");
  });
});
