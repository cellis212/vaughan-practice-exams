"""Parity test (Python side). Runs the Python engines with the RNG replaced
by the same deterministic rotation as tests/parity_test.R, over identical
scenarios, writing .tex outputs to tests/out_py/ for byte-level diffing.

Usage: python3 parity_test.py <out_dir> <intro_data_dir> <lh_data_dir>
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "py"))

import exam_common
import engine_intro
import engine_lh
import generator

out_dir, intro_data, lh_data = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out_dir, exist_ok=True)


def rotate_permutation(n):
    """Match rotate_sample in parity_test.R: sample(n) -> c(2:n, 1)."""
    if n <= 1:
        return [1]
    return list(range(2, n + 1)) + [1]


exam_common.r_sample_permutation = rotate_permutation


def synth_bank():
    rows = []
    d_vals = ["Choice D for q1", "Choice D for q2", None, "Choice D for q4",
              "Choice D for q5", "Choice D for q6", "Choice D for q7",
              "Choice D for q8", None, "Choice D for q10", "Choice D for q11",
              "Choice D for q12"]
    extras = ["n", "y", "y", "y", "n", "y", "n", "y", "y", "y", "y", "n"]
    correct = ["c", "ab", "b", "none", "a", "acd", "d", "bd", "none",
               "a", "c", "b"]
    block_id = [None, None, None, None, None, "B1", "B1", "B1", None,
                "B2", "B2", None]
    b_info = [None, None, None, None, None,
              "\\textbf{Questions in this block share the following scenario:} A firm faces a loss.",
              None, None, None,
              "\\textbf{Block two context:} Consider an insurance contract.",
              None, None]
    for i in range(12):
        rows.append({
            "Topic": "Synthetic Topic",
            "Text": "Question stem number " + str(i + 1) + " with some \\textbf{bold} text?",
            "a": "Choice A for q" + str(i + 1),
            "b": "Choice B for q" + str(i + 1),
            "c": "Choice C for q" + str(i + 1),
            "d": d_vals[i],
            "extras": extras[i],
            "correct": correct[i],
            "idea_id": None,
            "block_id": block_id[i],
            # q_id is numeric in R; as.numeric(1) renders as "1" in paste0
            "q_id": str(i + 1),
            "b_info": b_info[i],
        })
    return rows


qind_synth = [7, 3, 1, 6, 12, 2, 8, 10, 5, 11, 4, 9]
bank = synth_bank()

engine_intro.create_exam(bank=bank, qind=qind_synth, tit="Practice Exam:",
                         sem="Spring 2026", classnum="FIN 3400", numVer=1,
                         file=os.path.join(out_dir, "intro_practice_portrait.tex"),
                         frontPage=True, max_q=8, real_exam=False,
                         landscape=False)

engine_intro.create_exam(bank=bank, qind=qind_synth, tit="Practice Exam:",
                         sem="Spring 2026", classnum="FIN 3400", numVer=1,
                         file=os.path.join(out_dir, "intro_practice_landscape.tex"),
                         frontPage=True, max_q=8, real_exam=False,
                         landscape=True)

engine_intro.create_exam(bank=bank, qind=qind_synth, tit="Cumulative Final Exam:",
                         sem="Spring 2026", classnum="FIN 3400", numVer=3,
                         file=os.path.join(out_dir, "intro_real_portrait.tex"),
                         frontPage=True, max_q=8, real_exam=True,
                         landscape=False)

engine_lh.create_exam(bank=bank, qind=qind_synth, tit="Practice Exam:",
                      sem="Spring 2026", classnum="FIN 4430", numVer=1,
                      file=os.path.join(out_dir, "lh_practice_portrait.tex"),
                      frontPage=True, max_q=8, real_exam=False,
                      landscape=False)

engine_lh.create_exam(bank=bank, qind=qind_synth, tit="Practice Exam:",
                      sem="Spring 2026", classnum="FIN 4430", numVer=1,
                      file=os.path.join(out_dir, "lh_practice_landscape.tex"),
                      frontPage=True, max_q=8, real_exam=False,
                      landscape=True)

engine_lh.create_exam(bank=bank, qind=qind_synth, tit="Exam 3:",
                      sem="Spring 2026", classnum="FIN 4430", numVer=3,
                      file=os.path.join(out_dir, "lh_real_portrait.tex"),
                      frontPage=True, max_q=8, real_exam=True,
                      landscape=False)

bank_edge = [dict(r) for r in bank]
bank_edge[3]["b_info"] = "Stray context with no block id."
engine_lh.create_exam(bank=bank_edge, qind=qind_synth, tit="Practice Exam:",
                      sem="Spring 2026", classnum="FIN 4430", numVer=1,
                      file=os.path.join(out_dir, "lh_practice_blocknaedge.tex"),
                      frontPage=True, max_q=8, real_exam=False,
                      landscape=False)

# Real-data scenarios via the generator's bank loader (tests read_xlsx too)
full_intro = generator.load_full_bank([
    {"path": "Test Bank Topic 1.xlsx", "topic": "Topic 1"},
    {"path": "Test Bank Module 1 Math.xlsx", "topic": "Math For Module 1"},
], base_dir=intro_data)
engine_intro.create_exam(bank=full_intro,
                         qind=list(range(1, len(full_intro) + 1)),
                         tit="Practice Exam:", sem="Spring 2026",
                         classnum="FIN 3400", numVer=1,
                         file=os.path.join(out_dir, "intro_realdata.tex"),
                         frontPage=True, max_q=30, real_exam=False,
                         landscape=False)

full_lh = generator.load_full_bank([
    {"path": "Test Bank Module 3.xlsx", "topic": "Lecture"},
    {"path": "Test Bank Reading - Annuity Puzzle.xlsx", "topic": "Annuity Puzzle"},
], base_dir=lh_data)
engine_lh.create_exam(bank=full_lh,
                      qind=list(range(1, len(full_lh) + 1)),
                      tit="Practice Exam:", sem="Spring 2026",
                      classnum="FIN 4430", numVer=1,
                      file=os.path.join(out_dir, "lh_realdata.tex"),
                      frontPage=True, max_q=25, real_exam=False,
                      landscape=False)

print("Python parity outputs written to", out_dir)
