"""Check that assets/texlive-bundle.tar.gz lets the in-browser compiler
(SwiftLaTeX pdfTeX) build every exam the same way native pdflatex does.

Builds the coverage exams from tools/build_texlive_bundle.py (every question
of every bank, portrait and landscape, plus a 3-version sample), compiles each
  - in the SwiftLaTeX engine with only the bundle's files, every other lookup
    answered "not found" exactly as in the browser, and
  - with the local pdflatex,
then compares page counts and, on every page, every word and its position
(within 0.05 pt; the two pdfTeX versions round glyph positions differently
by about 0.001 pt).

Requires Node.js, TeX Live, and pdftotext (poppler). Takes several minutes.

Run from the repo root or tests/:  python3 tests/test_texlive_bundle.py
"""

import html
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location(
    "build_texlive_bundle", os.path.join(REPO, "tools", "build_texlive_bundle.py"))
bundle_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle_tool)


TOLERANCE_PT = 0.05
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">(.*?)</word>')


def page_words(pdf):
    """Per page, the list of (word, y, x) from pdftotext -bbox, sorted by word,
    then line, then position on the line."""
    out = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True,
                         text=True, check=True).stdout
    return [sorted((html.unescape(w), float(y), float(x)) for x, y, w in WORD.findall(page))
            for page in out.split("<page ")[1:]]


def same_page(a, b):
    return len(a) == len(b) and all(
        wa == wb and abs(ya - yb) <= TOLERANCE_PT and abs(xa - xb) <= TOLERANCE_PT
        for (wa, ya, xa), (wb, yb, xb) in zip(a, b))


def main():
    failures = []
    with tempfile.TemporaryDirectory() as work:
        corpus = bundle_tool.build_corpus(os.path.join(work, "corpus"))

        bundle_dir = os.path.join(work, "bundle")
        with tarfile.open(bundle_tool.BUNDLE) as tar:
            tar.extractall(bundle_dir, filter="data")
        files = {name: os.path.join(bundle_dir, name) for name in os.listdir(bundle_dir)}
        files["examdesign.cls"] = bundle_tool.EXAMDESIGN_CLS
        files.update({os.path.basename(p): p for p in corpus})

        engine_dir = os.path.join(work, "engine")
        os.makedirs(engine_dir)
        steps = [{"cmd": "compile", "main": os.path.basename(p),
                  "out": os.path.join(engine_dir, os.path.basename(p)[:-4] + ".pdf"),
                  "log": os.path.join(engine_dir, os.path.basename(p)[:-4] + ".log")}
                 for p in corpus]
        try:
            bundle_tool.run_harness({"resolver": "none", "files": files, "steps": steps}, work)
        except SystemExit as err:
            failures.append(str(err))

        native_dir = os.path.join(work, "native")
        os.makedirs(native_dir)
        shutil.copy(bundle_tool.EXAMDESIGN_CLS, native_dir)
        for tex in corpus:
            shutil.copy(tex, native_dir)
            subprocess.run(["pdflatex", "-interaction=nonstopmode", os.path.basename(tex)],
                           cwd=native_dir, capture_output=True)

        for tex in corpus:
            base = os.path.basename(tex)[:-4]
            engine_pdf = os.path.join(engine_dir, base + ".pdf")
            native_pdf = os.path.join(native_dir, base + ".pdf")
            if not os.path.exists(engine_pdf):
                failures.append(f"{base}: the engine produced no PDF")
                continue
            if not os.path.exists(native_pdf):
                failures.append(f"{base}: native pdflatex produced no PDF")
                continue
            engine_pages, native_pages = page_words(engine_pdf), page_words(native_pdf)
            if len(engine_pages) != len(native_pages):
                failures.append(f"{base}: {len(engine_pages)} pages in the engine, "
                                f"{len(native_pages)} natively")
                continue
            bad = [i + 1 for i, (a, b) in enumerate(zip(engine_pages, native_pages)) if not same_page(a, b)]
            if bad:
                failures.append(f"{base}: words or positions differ on pages {bad[:10]}")
            else:
                print(f"ok    {base}: {len(engine_pages)} pages match")

    if failures:
        for failure in failures:
            print("FAIL  " + failure)
        sys.exit(1)
    print("\nThe in-browser TeX bundle compiles every coverage exam like native pdflatex.")


if __name__ == "__main__":
    main()
