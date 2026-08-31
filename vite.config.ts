import path from "node:path";
import { defineConfig } from "vite";

// The bundle is committed to src/disvimat/web/static so that installing the
// Python package is enough to run the web editor: a teacher starting it
// from arrancar.bat has no Node, and should not need one. CI rebuilds it
// and fails if the committed file has drifted from these sources.
export default defineConfig({
  build: {
    outDir: path.resolve(import.meta.dirname, "src/disvimat/web/static"),
    emptyOutDir: false,
    // Readable output: this file is reviewed in diffs like any other.
    minify: false,
    target: "es2022",
    lib: {
      entry: path.resolve(import.meta.dirname, "src/web-client/editor.ts"),
      formats: ["iife"],
      name: "Disvimat",
      fileName: () => "editor.js",
    },
  },
});
