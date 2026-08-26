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
  [Pyodide](https://pyodide.org), reading the `.xlsx` test banks each
  professor's config selects with `openpyxl`.
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
banks/<course>/*.xlsx      The central test-bank store, one copy per course,
                           shared by every professor of that course
courses/<university>/<course>/<professor>/
  config.json              That professor's index into the central store:
                           which banks, topic labels, groups, titles
  data/*.xlsx              Optional professor-specific banks (only for
                           entries marked "local": true — none by default)
tools/                     Scripts that regenerate the parameterized banks
tests/                     R-vs-Python byte-level parity test (see below)
```

## Updating your test bank (professors)

The question banks live once, in the central per-course store
`banks/<course>/` (e.g. `banks/intro-to-rmi/`), and every professor of the
course draws from that same store. Your folder under
`courses/university-of-iowa/<course>/<your-name>/` holds only your
`config.json` — an index saying which banks you use, under what topic
labels and exam groups. Its `"banks_base"` field points at the store.

1. **Edit questions**: edit the `.xlsx` files in `banks/<course>/` —
   the edit reaches every professor of the course at once. Required
   columns: `q_id`, `Text`, `a`, `b`, `c`, `d` (d may be
   empty), `correct` (`a`…`d`, multi like `acd`, or `none`), `extras`
   (`n` = exactly one correct answer, `y` = multi-select + "None of the
   above"), and optionally `block_id` / `b_info` for question blocks sharing
   context. LaTeX special characters in text must be escaped.
   **Professor-specific questions**: to use your own version of a bank
   instead of the shared one, put the file in your own `data/` folder and
   mark that bank's config entry with `"local": true` — everyone else
   keeps the central copy.
2. **Enable/disable topics**: in your `config.json`, flip a bank's
   `"enabled"` flag (this mirrors commenting banks in/out of
   `banks_to_load` in the original `app.R`). Order matters — it is the order
   topics appear in the sidebar.
3. **Exam size presets**: the "Normal Exam Size" button fills in your
   config's `"normal_exam_size"` (default 75); "Every Question" fills in the
   total question count of the currently selected topics.
4. **Real exams**: set "Number of Versions" above 1 (and edit "Exam Title",
   e.g. `Exam 2:`) to generate an actual exam — the `examdesign` class
   renders all versions in one PDF with per-version question order and a
   version letter on each front page, with the same formatting as the
   practice exams. Check "Separate Files for Versions / Answer Keys" to
   instead download a zip of per-version exam and answer-key PDFs (the page
   boundaries are detected from the compiled document and split
   client-side).
5. **Exam sections**: each bank's `"group"` field (e.g. `"Midterm 1"`) is the
   collapsible section it appears under in the sidebar; the section's
   checkbox selects every topic in that exam at once. Group names and
   assignments are free-form per professor — rename them, regroup banks, or
   remove the `"group"` fields entirely to get a flat topic list.
6. Commit and push (or edit directly on GitHub). The site updates on the
   next Pages deploy — no build step.

## Auto-generated numbers for math questions

Math questions can draw **fresh numbers on every generation**, so the
numbers on a real exam will not match any practice exam a student has
printed, and every practice exam is a new problem set. A question opts in
via the optional `params` column plus `[[expr]]` placeholders in its text
and choice cells (the delimiter is `[[ ]]`, not `{ }`, because the cells
are full of LaTeX braces):

| column | content |
| --- | --- |
| `params` | one draw per line, e.g. `F = pick(10000, 20000, 50000)` then `p = pick(0.002, 0.005, 0.01)`; later lines can use earlier names (`prem = F * p * pick(2, 5, 10)`); `require(cond)` redraws until the condition holds |
| `Text` / `b_info` | `The policy pays \$[[num(F)]] with probability [[num(p,3)]].` |
| `a`…`d` | formulas: the correct one computes the right answer, the others encode plausible wrong methods, e.g. `[[dollar(prem - F*p)]]` vs `[[dollar(prem)]]` |
| `correct` | unchanged — the letter of the cell holding the correct formula (choices are still shuffled per exam, so its printed position varies) |

Available functions: `pick(v1, v2, ...)`, `steps(lo, hi, step)`,
`randint(a, b)`, `require(cond)`, `sqrt/exp/log/floor/ceil/abs/min/max/round`,
and the formatters `dollar(x, nearest=1)` (→ `\$1,235`; `dollar(x, 100)`
matches a "round to nearest 00s" instruction), `num(x, decimals,
nearest=None)` (commas, half-up rounding), and `pct(x, decimals)`
(`pct(0.05, 0)` → `5\%`). Plain arithmetic, comparisons, and
`a if cond else b` also work.

Rules of the game, enforced by `py/param_engine.py` at generation time:

- **Blocks share one draw**: put the scenario's `params` on the block's
  first row (the one with `b_info`); every row of the block can reference
  those names, so "based on the following information" numbers stay
  consistent across the block.
- **Choices are checked for collisions**: if two formulas round to the same
  printed value, the whole group is silently redrawn; a pair that *always*
  collides fails the generation with an error naming the question.
- **Seeds reproduce everything**: parameter draws come from the same seeded
  RNG as question sampling, so the "Random Seed" box reproduces an entire
  exam, numbers included. Generate a real exam with a private seed and you
  can re-print it identically later — while students, not knowing the seed,
  cannot regenerate your exam's numbers.
- Banks without a `params` column are completely unaffected.

The central "Test Bank Module 1 Math.xlsx" (`banks/intro-to-rmi/`) is fully
parameterized and doubles as a worked example;
`tools/build_param_math_bank.py` regenerates it. Math questions embedded in
a mixed bank work the same way — the central "Test Bank Topic 3.xlsx"
risk-pooling block (q18–q21) is parameterized in place via
`tools/build_param_topic3_block.py` while the other 46 questions are
untouched (a static row in a parameterized block simply passes through).
Because the store is shared, every professor's practice exams draw fresh
numbers from these banks automatically.
`tests/test_param_engine.py` stress-tests the engine and both banks (300
seeds each, plus independent recomputation of the correct answers).

## Adding a professor / course / university

1. Create `courses/<university>/<course>/<professor>/` with a `config.json`
   (copy an existing one as a template — it indexes the central
   `banks/<course>/` store, so no bank files need copying). A new course
   also gets its own `banks/<course>/` folder.
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
