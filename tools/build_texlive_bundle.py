"""Build assets/texlive-bundle.tar.gz: every TeX file the in-browser compiler
(SwiftLaTeX pdfTeX, vendor/swiftlatex) needs to compile the exams.

The generator page compiles in the browser when latex.ytotech.com fails.
SwiftLaTeX's own package server is gone, so the page loads this bundle and
writes its files into the engine before compiling.

Steps:
  1. Build coverage exams (build_corpus): for each course, every question of
     every bank any professor's config lists (enabled or not), portrait and
     landscape, plus a 3-version sample.
  2. Build the LaTeX format inside the engine from the local TeX Live, with
     English-only hyphenation patterns.
  3. Compile the coverage exams in the engine, answering its file lookups
     from the local TeX Live, and record every file it reads.
  4. Write the bundle: swiftlatexpdftex.fmt, pdftex.map cut down to the
     fonts the exams use (including those the format preloads), the font
     files those map lines name, and every file the exams read, flat.
  5. Compile the 3-version exams with only the bundle's files, as the
     browser does, before writing assets/texlive-bundle.tar.gz.

The engine stops at the first LaTeX error, so a question with an error
fails this build; fix the question and re-run.

Re-run after changing the exam preamble (py/engine_*.py) or
assets/examdesign.cls, or after adding questions that use new fonts or
symbols; tests/test_texlive_bundle.py checks the result. Requires TeX Live
(kpsewhich) and Node.js.

Run from the repo root:  python3 tools/build_texlive_bundle.py
"""

import glob
import gzip
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "py"))

import generator

BUNDLE = os.path.join(REPO, "assets", "texlive-bundle.tar.gz")
HARNESS = os.path.join(REPO, "tools", "swiftlatex_harness.js")
EXAMDESIGN_CLS = os.path.join(REPO, "assets", "examdesign.cls")
FORMAT_NAME = "swiftlatexpdftex.fmt"  # the format file the engine loads

# language.dat for the format: US English patterns only (the full TeX Live
# list would put every language's patterns into the format).
LANGUAGE_DAT = (
    "english\thyphen.tex\n=usenglish\n=USenglish\n=american\n"
    "dumylang\tdumyhyph.tex\nnohyphenation\tzerohyph.tex\n"
)


def course_banks(course_dir):
    """Every bank any professor of the course lists, once each, labeled with
    the first config's topic name. Returns (a config of the course, banks)."""
    banks, seen, cfg = [], set(), None
    for cfg_path in sorted(glob.glob(os.path.join(course_dir, "*", "config.json"))):
        cfg = json.load(open(cfg_path))
        for bank in cfg["banks"]:
            base = (os.path.join(os.path.dirname(cfg_path), "data")
                    if bank.get("local") else cfg["banks_base"])
            path = os.path.join(base, bank["file"])
            if path not in seen:
                seen.add(path)
                banks.append({"path": path, "topic": bank["topic"]})
    return cfg, banks


def build_corpus(out_dir):
    """Write the coverage exams into out_dir and return their .tex paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for course_dir in sorted(glob.glob(os.path.join(REPO, "courses", "*", "*"))):
        cfg, banks = course_banks(course_dir)
        full = generator.load_full_bank(banks, base_dir=REPO)
        topics = generator.unique_topics(full)
        tag = "_".join(os.path.relpath(course_dir, os.path.join(REPO, "courses")).split(os.sep))
        variants = (
            ("all_portrait", False, 1, len(full)),
            ("all_landscape", True, 1, len(full)),
            ("versions3", False, 3, min(75, len(full))),
        )
        for name, landscape, versions, n_questions in variants:
            result = generator.generate_exam(
                full, topics, n_questions, "11", landscape, cfg["engine"],
                cfg["semester"], cfg["classnum"], exam_dir=out_dir,
                num_versions_input=versions, title_input="Practice Exam:",
            )
            if result["status"] != "ok":
                raise SystemExit(f"Could not generate {tag} {name}: {result}")
            path = os.path.join(out_dir, f"{tag}_{name}.tex")
            with open(path, "w") as f:
                f.write(result["tex"])
            paths.append(path)
    # generate_exam also writes Practice_Exam.tex; it is not part of the corpus
    os.remove(os.path.join(out_dir, "Practice_Exam.tex"))
    return paths


def run_harness(job, work_dir):
    job_path = os.path.join(work_dir, "job.json")
    with open(job_path, "w") as f:
        json.dump(job, f)
    if subprocess.run(["node", HARNESS, job_path]).returncode != 0:
        raise SystemExit("The SwiftLaTeX engine failed; see its log above.")


def trimmed_font_map(map_path, fonts):
    """pdftex.map lines for the given font (TFM) names only, and the font and
    encoding files those lines name (<file.pfb, <file.enc)."""
    with open(map_path, "rb") as f:
        lines = f.read().decode("latin-1").split("\n")
    keep = [line for line in lines if line.split() and line.split()[0] in fonts]
    referenced = {name for line in keep for name in re.findall(r'<[<\[]?([^\s"]+)', line)}
    return ("\n".join(keep) + "\n").encode("latin-1"), referenced


def kpsewhich(name):
    found = subprocess.run(["kpsewhich", name], capture_output=True, text=True).stdout.strip()
    if not found:
        raise SystemExit(f"kpsewhich cannot find {name}")
    return found


def write_bundle(entries):
    """Deterministic .tar.gz (sorted names, zero timestamps) of {name: bytes}."""
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for name in sorted(entries):
                info = tarfile.TarInfo(name)
                info.size = len(entries[name])
                info.mode = 0o644
                info.mtime = 0
                tar.addfile(info, io.BytesIO(entries[name]))
    with open(BUNDLE, "wb") as f:
        f.write(buf.getvalue())


def main():
    with tempfile.TemporaryDirectory() as work:
        print("Generating coverage exams...")
        corpus = build_corpus(os.path.join(work, "corpus"))

        print("Building the LaTeX format in the engine...")
        language_dat = os.path.join(work, "language.dat")
        with open(language_dat, "w") as f:
            f.write(LANGUAGE_DAT)
        fmt = os.path.join(work, FORMAT_NAME)
        format_record = os.path.join(work, "format_requests.json")
        run_harness({
            "resolver": "kpsewhich",
            "files": {"language.dat": language_dat},
            "steps": [{"cmd": "format", "out": fmt, "log": os.path.join(work, "format.log")}],
            "record": format_record,
        }, work)

        print("Compiling the coverage exams in the engine...")
        record = os.path.join(work, "requests.json")
        files = {FORMAT_NAME: fmt, "examdesign.cls": EXAMDESIGN_CLS}
        files.update({os.path.basename(p): p for p in corpus})
        run_harness({
            "resolver": "kpsewhich",
            "files": files,
            "steps": [{"cmd": "compile", "main": os.path.basename(p),
                       "out": p[:-4] + ".pdf", "log": p[:-4] + ".log"} for p in corpus],
            "record": record,
        }, work)

        used = sorted({r["path"] for r in json.load(open(record)) if r["path"]})
        by_name = {}
        for path in used:
            name = os.path.basename(path)
            if name in by_name and by_name[name] != path:
                raise SystemExit(f"Two TeX Live files share the name {name}: {by_name[name]}, {path}")
            by_name[name] = path

        # Fonts the exams use: TFMs read while compiling, plus the ones the
        # format preloads (cmr10 etc.), whose metrics live inside the format
        # but still need pdftex.map lines to be embedded.
        preloaded = {r["name"] for r in json.load(open(format_record)) if r["path"] and r["format"] == 3}
        fonts = {os.path.splitext(n)[0] for n in by_name if n.endswith(".tfm")}
        fonts |= {os.path.splitext(n)[0] for n in preloaded}
        entries = {}
        for name, path in by_name.items():
            if name == "pdftex.map":
                entries[name], referenced = trimmed_font_map(path, fonts)
            else:
                with open(path, "rb") as f:
                    entries[name] = f.read()
        # Every font file the map points to must be present, or pdfTeX aborts
        # while embedding it.
        for name in sorted(referenced - set(entries)):
            with open(kpsewhich(name), "rb") as f:
                entries[name] = f.read()
        with open(fmt, "rb") as f:
            entries[FORMAT_NAME] = f.read()

        print("Checking the bundle on its own (as in the browser)...")
        bundle_dir = os.path.join(work, "bundle")
        os.makedirs(bundle_dir)
        for name, data in entries.items():
            with open(os.path.join(bundle_dir, name), "wb") as f:
                f.write(data)
        files = {name: os.path.join(bundle_dir, name) for name in entries}
        files["examdesign.cls"] = EXAMDESIGN_CLS
        samples = [p for p in corpus if p.endswith("_versions3.tex")]
        files.update({os.path.basename(p): p for p in samples})
        run_harness({
            "resolver": "none",
            "files": files,
            "steps": [{"cmd": "compile", "main": os.path.basename(p),
                       "out": p[:-4] + ".bundle.pdf"} for p in samples],
        }, work)
        write_bundle(entries)

    raw = sum(len(v) for v in entries.values())
    print(f"Wrote {os.path.relpath(BUNDLE, REPO)}: {len(entries)} files, "
          f"{raw / 1e6:.1f} MB uncompressed, {os.path.getsize(BUNDLE) / 1e6:.1f} MB compressed")


if __name__ == "__main__":
    main()
