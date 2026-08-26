// Practice exam generator page.
//
// The exam-building logic is the Python translation of the R Shiny app
// (py/exam_common.py, py/engine_intro.py, py/engine_lh.py, py/generator.py),
// executed in the browser via Pyodide. The resulting .tex is compiled to PDF
// by the LaTeX-on-HTTP service (latex.ytotech.com), which returns the PDF
// directly with CORS enabled; we send the repo's examdesign.cls with every
// compile so the document class is pinned.

const LATEX_ENDPOINT = "https://latex.ytotech.com/builds/sync";
const PY_MODULES = ["exam_common.py", "engine_intro.py", "engine_lh.py", "generator.py"];

const params = new URLSearchParams(window.location.search);
const uniId = params.get("u");
const courseId = params.get("c");
const profId = params.get("p");

const statusLine = document.getElementById("status-line");
const generateBtn = document.getElementById("generate-exam");
const downloadArea = document.getElementById("download-area");
const compileLogEl = document.getElementById("compile-log");

let pyodide = null;
let config = null;
let clsText = null;
let banksLoaded = false;
let currentPdfUrl = null;

function notify(message, type) {
  const el = document.createElement("div");
  el.className = "notification " + type;
  el.textContent = message;
  document.getElementById("notifications").appendChild(el);
  setTimeout(() => el.remove(), 8000);
}

function setStatus(text) {
  statusLine.textContent = text;
}

function fail(message) {
  setStatus(message);
  notify(message, "error");
  throw new Error(message);
}

function comboBase() {
  return "courses/" + uniId + "/" + courseId + "/" + profId;
}

async function fetchOk(url, as) {
  const resp = await fetch(url);
  if (!resp.ok) fail("Failed to load " + url + " (HTTP " + resp.status + ")");
  if (as === "json") return resp.json();
  if (as === "bytes") return new Uint8Array(await resp.arrayBuffer());
  return resp.text();
}

function enabledBanks() {
  return config.banks.filter((b) => b.enabled);
}

function renderUi() {
  document.title = config.app_title;
  document.getElementById("app-title").textContent = config.app_title;
  document.getElementById("crumb-detail").textContent =
    " · " + config.university + " · " + config.course_name + " · " + config.professor;

  // Topic checkboxes: unique(full_bank$Topic) in bank-load order.
  const seen = new Set();
  const list = document.getElementById("topic-list");
  for (const bank of enabledBanks()) {
    if (seen.has(bank.topic)) continue;
    seen.add(bank.topic);
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = bank.topic;
    cb.className = "topic-cb";
    label.appendChild(cb);
    label.appendChild(document.createTextNode(bank.topic));
    list.appendChild(label);
  }

  document.getElementById("n-questions").value = config.default_n_questions;
  document.getElementById("coverage").innerHTML = config.coverage_html || "";
  document.getElementById("app-footer").textContent = config.footer || "";
}

async function loadEngine() {
  setStatus("Loading exam engine…");
  pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  await micropip.install("openpyxl");

  pyodide.FS.mkdirTree("/app/py");
  for (const mod of PY_MODULES) {
    const src = await fetchOk("py/" + mod, "text");
    pyodide.FS.writeFile("/app/py/" + mod, src);
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/app/py')");

  setStatus("Loading question banks…");
  pyodide.FS.mkdirTree("/app/data");
  for (const bank of enabledBanks()) {
    const bytes = await fetchOk(comboBase() + "/data/" + bank.file, "bytes");
    const dest = "/app/data/" + bank.file;
    const dir = dest.substring(0, dest.lastIndexOf("/"));
    pyodide.FS.mkdirTree(dir);
    pyodide.FS.writeFile(dest, bytes);
  }

  // Load and combine banks (mirrors the top of app.R)
  pyodide.globals.set("banks_to_load_json", JSON.stringify(
    enabledBanks().map((b) => ({ path: b.file, topic: b.topic }))
  ));
  pyodide.runPython(`
import json
import generator

banks_to_load = json.loads(banks_to_load_json)
full_bank = generator.load_full_bank(banks_to_load, base_dir="/app/data")

def run_generation(sel_topics_json, n_questions, seed_input, landscape,
                   engine, semester, classnum):
    result = generator.generate_exam(
        full_bank,
        json.loads(sel_topics_json),
        n_questions,
        seed_input,
        landscape,
        engine,
        semester,
        classnum,
        exam_dir="/app/Exam",
    )
    return json.dumps(result)
`);

  clsText = await fetchOk("assets/examdesign.cls", "text");
  banksLoaded = true;
  generateBtn.disabled = false;
  setStatus("Ready.");
}

async function compilePdf(tex) {
  const payload = {
    compiler: "pdflatex",
    resources: [
      { main: true, content: tex },
      { path: "examdesign.cls", content: clsText },
    ],
  };

  const resp = await fetch(LATEX_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const buf = await resp.arrayBuffer();
  const bytes = new Uint8Array(buf);
  // A PDF starts with %PDF; anything else is an error/log payload.
  const isPdf = bytes.length > 4 && bytes[0] === 0x25 && bytes[1] === 0x50 &&
    bytes[2] === 0x44 && bytes[3] === 0x46;
  if (!resp.ok || !isPdf) {
    let log = new TextDecoder().decode(bytes);
    try {
      const parsed = JSON.parse(log);
      if (parsed.logs) log = typeof parsed.logs === "string" ? parsed.logs : JSON.stringify(parsed.logs, null, 2);
    } catch (e) { /* not JSON; show raw text */ }
    compileLogEl.textContent = log;
    compileLogEl.style.display = "block";
    fail("PDF compilation failed (HTTP " + resp.status + "). The compile log is shown below.");
  }
  compileLogEl.style.display = "none";
  return new Blob([bytes], { type: "application/pdf" });
}

function showDownloadButton(blob) {
  if (currentPdfUrl) URL.revokeObjectURL(currentPdfUrl);
  currentPdfUrl = URL.createObjectURL(blob);
  downloadArea.innerHTML = "";
  const a = document.createElement("a");
  a.className = "download-btn";
  a.href = currentPdfUrl;
  a.download = "Practice_Exam.pdf";
  a.textContent = "Download Exam PDF";
  downloadArea.appendChild(a);
}

async function onGenerate() {
  // req(input$sel_topics): with no topics selected, the Shiny handler
  // halts silently and nothing happens.
  const selTopics = Array.from(document.querySelectorAll(".topic-cb:checked"))
    .map((cb) => cb.value);
  if (selTopics.length === 0) return;

  const nRaw = document.getElementById("n-questions").value;
  const nQuestions = parseFloat(nRaw);
  if (!isFinite(nQuestions)) {
    notify("Number of Questions must be a number.", "error");
    return;
  }
  const seedInput = document.getElementById("seed-input").value.trim();
  const landscape = document.getElementById("landscape-mode").checked;

  generateBtn.disabled = true;
  try {
    setStatus("Generating exam…");
    const runGeneration = pyodide.globals.get("run_generation");
    const resultJson = runGeneration(
      JSON.stringify(selTopics), nQuestions, seedInput, landscape,
      config.engine, config.semester, config.classnum
    );
    const result = JSON.parse(resultJson);

    if (result.status === "error") {
      notify(result.message, "error");
      setStatus("Ready.");
      return;
    }
    if (result.status !== "ok") {
      setStatus("Ready.");
      return;
    }

    setStatus("Compiling PDF (this can take up to a minute)…");
    const blob = await compilePdf(result.tex);
    showDownloadButton(blob);
    notify("Exam generated successfully.", "message");
    setStatus("Ready.");
  } catch (err) {
    console.error(err);
    if (statusLine.textContent.indexOf("failed") === -1) {
      setStatus("Generation failed: " + err.message);
      notify("Generation failed: " + err.message, "error");
    }
  } finally {
    generateBtn.disabled = !banksLoaded;
  }
}

(async function init() {
  if (!uniId || !courseId || !profId) {
    document.getElementById("app-title").textContent =
      "Missing course selection — please start from the home page.";
    setStatus("");
    return;
  }
  try {
    config = await fetchOk(comboBase() + "/config.json", "json");
  } catch (err) {
    document.getElementById("app-title").textContent =
      "Unknown course/professor combination.";
    return;
  }
  renderUi();
  generateBtn.addEventListener("click", onGenerate);
  try {
    await loadEngine();
  } catch (err) {
    console.error(err);
    setStatus("Failed to load the exam engine: " + err.message);
  }
})();
