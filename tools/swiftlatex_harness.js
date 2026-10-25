// Runs the SwiftLaTeX pdfTeX engine (vendor/swiftlatex) under Node, for
// building and testing assets/texlive-bundle.tar.gz. It loads the same worker
// script the browser uses and talks to it with the same messages.
//
// usage: node tools/swiftlatex_harness.js <job.json>
// job.json:
//   {
//     "resolver": "kpsewhich" | "none",
//         kpsewhich: answer the engine's file lookups from the local TeX Live
//                    (used to discover which files the exams need)
//         none:      answer every lookup "not found", as the browser does,
//                    so only files written into the work dir are available
//     "files": {"name": "/local/path"},   written into the engine's work dir
//     "steps": [{"cmd": "format", "out": "...", "log": "..."},
//               {"cmd": "compile", "main": "x.tex", "out": "...", "log": "..."}],
//     "record": "/path.json"               optional: every lookup the engine made
//   }
// Exits non-zero if any step fails.

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ENGINE_DIR = path.join(__dirname, "..", "vendor", "swiftlatex");
const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

// kpathsea file-format numbers used by the engine (kpse_file_format_type)
const KPSE_FORMAT_NAMES = {
  3: "tfm", 6: "bib", 7: "bst", 8: "cnf", 10: "fmt", 11: "map", 26: "tex",
  32: "type1 fonts", 33: "vf", 44: "enc files", 48: "pdftex config",
};
const requested = [];
const resolved = new Map();

function kpsewhich(format, name) {
  const key = format + "/" + name;
  if (!resolved.has(key)) {
    const args = KPSE_FORMAT_NAMES[format] ? ["-format=" + KPSE_FORMAT_NAMES[format], name] : [name];
    let found = null;
    try {
      found = execFileSync("kpsewhich", args, { encoding: "utf8" }).trim() || null;
    } catch (err) {
      found = null;
    }
    resolved.set(key, found);
  }
  return resolved.get(key);
}

// The engine looks up missing files with synchronous XHRs to
// <endpoint>pdftex/<format>/<name> (or pdftex/pk/<dpi>/<name> for bitmap
// fonts): 200 + "fileid" header = found, 301 = not found.
class LocalTeXLiveXHR {
  open(method, url) {
    this.url = url;
  }
  send() {
    const m = this.url.match(/pdftex\/(pk\/)?(\d+)\/(.+)$/);
    const entry = { pk: Boolean(m && m[1]), format: m ? Number(m[2]) : null, name: m ? m[3] : this.url, path: null };
    requested.push(entry);
    this.status = 301;
    if (job.resolver !== "kpsewhich" || !m || entry.pk) return;
    entry.path = kpsewhich(entry.format, entry.name);
    if (!entry.path) return;
    const bytes = fs.readFileSync(entry.path);
    this.response = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length);
    this.fileid = path.basename(entry.path);
    this.status = 200;
  }
  getResponseHeader(name) {
    return name === "fileid" ? this.fileid : null;
  }
}

globalThis.self = globalThis;
globalThis.XMLHttpRequest = LocalTeXLiveXHR;
// Emscripten prefers fetch() for the .wasm when it exists, but Node's fetch
// cannot load a file path; without it the engine reads the file directly.
delete globalThis.fetch;
const outbox = [];
globalThis.postMessage = (msg) => outbox.push(msg);

const enginePath = path.join(ENGINE_DIR, "swiftlatexpdftex.js");
new Function("require", "__dirname", "__filename", "module", "process", fs.readFileSync(enginePath, "utf8"))(
  require, ENGINE_DIR, enginePath, { exports: {} }, process
);

function send(data) {
  outbox.length = 0;
  globalThis.onmessage({ data });
  return outbox.slice();
}

async function main() {
  while (!outbox.some((m) => m.result === "ok")) await new Promise((r) => setTimeout(r, 20));

  for (const [name, src] of Object.entries(job.files || {})) {
    const reply = send({ cmd: "writefile", url: name, src: fs.readFileSync(src) })[0];
    if (!reply || reply.result !== "ok") throw new Error("could not write " + name);
  }

  for (const step of job.steps) {
    const started = Date.now();
    let res;
    if (step.cmd === "format") {
      res = send({ cmd: "compileformat" })[0];
    } else {
      send({ cmd: "setmainfile", url: step.main });
      res = send({ cmd: "compilelatex" })[0];
    }
    if (step.log) fs.writeFileSync(step.log, res.log || "");
    const label = step.cmd + (step.main ? " " + step.main : "");
    if (res.result !== "ok") {
      console.log(`${label}: FAILED (status ${res.status})`);
      console.log((res.log || "").split("\n").slice(-25).join("\n"));
      process.exitCode = 1;
      break;
    }
    fs.writeFileSync(step.out, Buffer.from(res.pdf));
    console.log(`${label}: ok in ${((Date.now() - started) / 1000).toFixed(1)} s`);
  }
  if (job.record) fs.writeFileSync(job.record, JSON.stringify(requested, null, 1));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
