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

function makeTopicLabel(topic) {
  const label = document.createElement("label");
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.value = topic;
  cb.className = "topic-cb";
  label.appendChild(cb);
  label.appendChild(document.createTextNode(topic));
  return label;
}

// One collapsible exam section: a select-all checkbox for the whole group,
// a click-to-expand header, and the group's individual topic checkboxes.
function makeGroupSection(name, topicNames) {
  const section = document.createElement("div");
  section.className = "topic-group";

  const header = document.createElement("div");
  header.className = "group-header";

  const groupCb = document.createElement("input");
  groupCb.type = "checkbox";
  groupCb.className = "group-cb";
  groupCb.title = "Select all " + name + " topics";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "group-toggle";
  const chevron = document.createElement("span");
  chevron.className = "chevron";
  chevron.textContent = "▸";
  const labelSpan = document.createElement("span");
  labelSpan.textContent = name;
  const countSpan = document.createElement("span");
  countSpan.className = "group-count";
  countSpan.textContent = "(" + topicNames.length +
    (topicNames.length === 1 ? " topic)" : " topics)");
  toggle.appendChild(chevron);
  toggle.appendChild(labelSpan);
  toggle.appendChild(countSpan);

  header.appendChild(groupCb);
  header.appendChild(toggle);
  section.appendChild(header);

  const inner = document.createElement("div");
  inner.className = "group-topics";
  const topicCbs = [];
  for (const t of topicNames) {
    const label = makeTopicLabel(t);
    topicCbs.push(label.querySelector("input"));
    inner.appendChild(label);
  }
  section.appendChild(inner);

  toggle.addEventListener("click", () => {
    const open = section.classList.toggle("open");
    chevron.textContent = open ? "▾" : "▸";
  });

  groupCb.addEventListener("change", () => {
    for (const cb of topicCbs) cb.checked = groupCb.checked;
    groupCb.indeterminate = false;
  });

  function syncGroupCb() {
    const n = topicCbs.filter((cb) => cb.checked).length;
    groupCb.checked = n === topicCbs.length && n > 0;
    groupCb.indeterminate = n > 0 && n < topicCbs.length;
  }
  for (const cb of topicCbs) cb.addEventListener("change", syncGroupCb);

  return section;
}

function renderUi() {
  document.title = config.app_title;
  document.getElementById("app-title").textContent = config.app_title;
  document.getElementById("crumb-detail").textContent =
    " · " + config.university + " · " + config.course_name + " · " + config.professor;

  // Topic checkboxes: unique(full_bank$Topic) in bank-load order, sectioned
  // by each bank's configured "group" (e.g. Midterm 1/2/3). Groups are
  // config-driven per professor/course, not hardcoded; a config with no
  // groups renders the original flat list.
  const seen = new Set();
  const topics = [];
  for (const bank of enabledBanks()) {
    if (seen.has(bank.topic)) continue;
    seen.add(bank.topic);
    topics.push({ topic: bank.topic, group: bank.group || null });
  }

  const list = document.getElementById("topic-list");
  if (!topics.some((t) => t.group)) {
    for (const t of topics) list.appendChild(makeTopicLabel(t.topic));
  } else {
    const groupOrder = [];
    const grouped = new Map();
    for (const t of topics) {
      const g = t.group || "Other Topics";
      if (!grouped.has(g)) {
        grouped.set(g, []);
        groupOrder.push(g);
      }
      grouped.get(g).push(t.topic);
    }
    for (const g of groupOrder) {
      list.appendChild(makeGroupSection(g, grouped.get(g)));
    }
  }

  document.getElementById("n-questions").value = config.default_n_questions;
  document.getElementById("coverage").innerHTML = config.coverage_html || "";
  document.getElementById("app-footer").textContent = config.footer || "";

  // Question-count presets. "Normal Exam Size" comes from the config
  // (per professor/course; defaults to 75). "Every Question" fills in the
  // total question count across the currently selected topics once the
  // banks are loaded.
  const normalSize = config.normal_exam_size || 75;
  const normalBtn = document.getElementById("preset-normal");
  normalBtn.textContent = "Normal Exam Size (" + normalSize + ")";
  normalBtn.addEventListener("click", () => {
    document.getElementById("n-questions").value = normalSize;
  });

  document.getElementById("preset-every").addEventListener("click", () => {
    const sel = Array.from(document.querySelectorAll(".topic-cb:checked"))
      .map((cb) => cb.value);
    if (sel.length === 0) {
      notify("Select at least one topic first.", "error");
      return;
    }
    pyodide.globals.set("every_sel_json", JSON.stringify(sel));
    const count = pyodide.runPython(
      "sum(1 for r in full_bank if r['Topic'] in set(json.loads(every_sel_json)))"
    );
    document.getElementById("n-questions").value = count;
  });
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
  document.getElementById("preset-every").disabled = false;
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
