# Practice Exam Generator

Static website that generates randomized multiple-choice practice exams (as
compiled PDFs) for courses of **The Emmett J. Vaughan Institute of Risk
Management & Insurance**, Tippie College of Business, The University of Iowa.

Students pick their university, course, and professor, select topics, and the
site assembles a randomized exam from that professor's test bank — a Python
translation, verified byte-for-byte, of the original R Shiny generators used
for FIN 3400 (Introduction to RMI) and FIN 4430 (Life / Health Insurance).

© 2026 Cameron Ellis and Meghan Esson. All rights reserved.

## How it works

- **GitHub Pages** serves everything statically — there is no backend.
- The exam-building logic (`py/`) is an exact Python port of the R code in
  `Functions and Options.R` + `app.R`. It runs **in the browser** via
  [Pyodide](https://pyodide.org), reading each professor's `.xlsx` test banks
  with `openpyxl`.
- The generated LaTeX (`examdesign` class) is compiled to PDF by the free
  [LaTeX-on-HTTP](https://github.com/YtoTech/latex-on-http) service at
  `latex.ytotech.com` (CORS-enabled, returns the PDF directly). The repo's
  `assets/examdesign.cls` is sent along with every compile so the document
  class is pinned.

Pipeline: select topics → sample questions → randomize answer choices
(`rc`) → format questions/blocks (`fq`/`fqb`) → assemble `.tex`
(`create_exam`) → compile → download `Practice_Exam.pdf`.

## Repository layout

```
index.html                 Landing page (university → course → professor)
generator.html + js/       The generator app (mirrors the Shiny UI)
py/
  exam_common.py           rc(), fq(), fqb(), make_fm() — shared engine code
  engine_intro.py          create_exam() for FIN 3400 (RMI Intro variant)
  engine_lh.py             create_exam() for FIN 4430 (Life/Health variant)
  generator.py             Bank loading + the generate handler (app.R port)
assets/examdesign.cls      LaTeX document class shipped with every compile
catalog.json               Universities / courses / professors shown on the landing page
courses/<university>/<course>/<professor>/
  config.json              That professor's bank list, topics, titles, coverage notes
  data/*.xlsx              That professor's own copy of the test banks
tests/                     R-vs-Python byte-level parity test (see below)
```

## Updating your test bank (professors)

Each professor/course combination owns its folder under
`courses/university-of-iowa/<course>/<your-name>/`:

1. **Edit questions**: replace or edit the `.xlsx` files in your `data/`
   folder. Required columns: `q_id`, `Text`, `a`, `b`, `c`, `d` (d may be
   empty), `correct` (`a`…`d`, multi like `acd`, or `none`), `extras`
   (`n` = exactly one correct answer, `y` = multi-select + "None of the
   above"), and optionally `block_id` / `b_info` for question blocks sharing
   context. LaTeX special characters in text must be escaped.
2. **Enable/disable topics**: in your `config.json`, flip a bank's
   `"enabled"` flag (this mirrors commenting banks in/out of
   `banks_to_load` in the original `app.R`). Order matters — it is the order
   topics appear in the sidebar.
3. **Exam sections**: each bank's `"group"` field (e.g. `"Midterm 1"`) is the
   collapsible section it appears under in the sidebar; the section's
   checkbox selects every topic in that exam at once. Group names and
   assignments are free-form per professor — rename them, regroup banks, or
   remove the `"group"` fields entirely to get a flat topic list.
3. Commit and push (or edit directly on GitHub). The site updates on the
   next Pages deploy — no build step.

## Adding a professor / course / university

1. Create `courses/<university>/<course>/<professor>/` with a `config.json`
   and a `data/` folder (copy an existing one as a template).
2. Add the professor (or course/university) to `catalog.json`.

## Exactness guarantee

`tests/run_parity.sh` runs the **original R engines** (copies in
`tests/reference/`) and the Python port over identical scenarios — synthetic
banks covering blocks, multi-answer, "none", 3-choice questions,
landscape/portrait, practice/real modes, plus real test-bank data — with the
random shuffle pinned to the same deterministic permutation in both
languages, and diffs the generated `.tex` byte-for-byte. All scenarios must
match. Requires local `Rscript` (tidyverse, readxl) and `python3`
(openpyxl).

The only intended behavioral differences from the Shiny apps:

- R's and Python's random number generators differ, so the same seed does
  not reproduce the same exam across the two implementations (a seed still
  reproduces the same exam within this site).
- PDF compilation happens on latex.ytotech.com instead of a local
  `pdflatex`/tinytex, and a failed compile shows the log instead of
  silently claiming success.

## Local development

Serve the folder with any static server, e.g.:

```bash
python3 -m http.server 8000
```

then open <http://localhost:8000>. (Opening `index.html` from `file://`
will not work — Pyodide and `fetch` need HTTP.)

---

Created by Dr. Cameron Ellis and Dr. Meghan Esson.
The Emmett J. Vaughan Institute of Risk Management & Insurance,
Tippie College of Business, The University of Iowa.
