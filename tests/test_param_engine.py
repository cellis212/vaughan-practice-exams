"""Tests for py/param_engine.py and the parameterized math bank.

Run from the repo root or tests/:  python3 tests/test_param_engine.py

Covers:
  1. Engine unit behavior: substitution, formatting, block-shared params,
     require() redraws, duplicate-choice redraws, hard failures, and the
     static-bank pass-through (identity + zero RNG consumption).
  2. The converted "Test Bank Module 1 Math.xlsx" (Ellis copy): stress
     instantiation over many seeds; every placeholder resolves, every
     question's choices are distinct, and the correct-answer cell of a
     sample of questions matches an independent recomputation.
  3. End-to-end generate_exam(): deterministic under a seed, varying
     across seeds, and no leftover [[ ]] markers in the .tex.
"""

import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "py"))

import exam_common
import generator
import param_engine
from param_engine import ParamError

ELLIS_DATA = os.path.join(REPO, "courses", "university-of-iowa",
                          "intro-to-rmi", "ellis", "data")

failures = []


def check(name, cond, detail=""):
    if cond:
        print("ok   ", name)
    else:
        print("FAIL ", name, detail)
        failures.append(name)


def expect_raises(name, exc, fn):
    try:
        fn()
    except exc:
        print("ok   ", name)
        return
    except Exception as e:  # noqa: BLE001 - report the wrong exception type
        print("FAIL ", name, "raised", type(e).__name__, str(e))
        failures.append(name)
        return
    print("FAIL ", name, "did not raise")
    failures.append(name)


def row(**kw):
    base = {"Topic": "T", "Text": "t", "a": "1", "b": "2", "c": "3",
            "d": "4", "extras": "y", "correct": "a", "idea_id": None,
            "block_id": None, "q_id": "1", "b_info": None, "params": None}
    base.update(kw)
    return base


# ---------------------------------------------------------------- unit: fmt
check("dollar basic", param_engine.dollar(1234.6) == "\\$1,235")
check("dollar nearest 100", param_engine.dollar(2481, 100) == "\\$2,500")
check("dollar negative", param_engine.dollar(-450) == "-\\$450")
check("dollar half-up", param_engine.dollar(450.5) == "\\$451")
check("num decimals", param_engine.num(2.236, 2) == "2.24")
check("num half-up", param_engine.num(2.675, 2) == "2.68")
check("num commas+nearest",
      param_engine.num(123439999, 0, 1000) == "123,440,000")
check("pct", param_engine.pct(0.05, 0) == "5\\%")
check("pct decimals", param_engine.pct(0.00001, 4) == "0.0010\\%")

# ------------------------------------------------------- unit: substitution
rng = random.Random(1)
r = row(Text="EV is [[dollar(p*L)]] with p=[[num(p,1)]]",
        a="[[dollar(p*L)]]", b="[[dollar(L)]]", c="\\$0",
        d="[[dollar((1-p)*L)]]",
        params="p = pick(0.2)\nL = pick(500)")
out = param_engine.instantiate_group([r], rng)[0]
check("substitution text", out["Text"] == "EV is \\$100 with p=0.2",
      repr(out["Text"]))
check("substitution choices",
      (out["a"], out["b"], out["c"], out["d"]) ==
      ("\\$100", "\\$500", "\\$0", "\\$400"), repr(out))
check("original row untouched", r["a"] == "[[dollar(p*L)]]")

# Block rows share the head row's environment.
head = row(q_id="1", block_id="B", b_info="F is [[num(F)]]",
           params="F = pick(1000)\np = pick(0.1)",
           a="[[dollar(F*p)]]", b="[[dollar(F)]]", c="x", d="y")
tail = row(q_id="2", block_id="B", a="[[dollar(F*(1-p))]]", b="z", c="w",
           d=None)
outs = param_engine.instantiate_group([head, tail], rng)
check("block shared env",
      outs[0]["b_info"] == "F is 1,000" and outs[0]["a"] == "\\$100"
      and outs[1]["a"] == "\\$900", repr(outs))

# require() redraws until satisfied; deterministic under a seed.
r2 = row(params="x = pick(1, 2, 3, 4)\nrequire(x >= 3)", a="[[x]]",
         b="s", c="t", d="u")
vals = set()
for seed in range(40):
    rr = random.Random(seed)
    vals.add(param_engine.instantiate_group([r2], rr)[0]["a"])
check("require filters draws", vals == {"3", "4"}, repr(vals))

# Duplicate formatted choices force a redraw; an always-duplicate pair
# fails loudly with the question named.
r3 = row(params="x = pick(1, 2)", a="[[x]]", b="[[3-x]]", c="9", d="8")
o3 = param_engine.instantiate_group([r3], random.Random(0))[0]
check("collision redraw", o3["a"] != o3["b"], repr(o3))
r4 = row(q_id="77", params="x = pick(5)", a="[[x]]", b="[[x]]", c="9", d="8")
expect_raises("always-duplicate fails loudly", ParamError,
              lambda: param_engine.instantiate_group([r4], random.Random(0)))

# Malformed templates fail immediately with ParamError.
expect_raises("unknown name", ParamError,
              lambda: param_engine.instantiate_group(
                  [row(a="[[nope]]", params="x = pick(1)")],
                  random.Random(0)))
expect_raises("disallowed call", ParamError,
              lambda: param_engine.instantiate_group(
                  [row(params="x = __import__('os')")], random.Random(0)))
expect_raises("unbalanced marker", ParamError,
              lambda: param_engine.instantiate_group(
                  [row(a="[[x", params="x = pick(1)")], random.Random(0)))

# Static rows: identity pass-through, zero RNG consumption.
static_rows = [row(), row(q_id="2", block_id="S",
                          b_info="ctx"), row(q_id="3", block_id="S")]
rng_a = random.Random(42)
before = rng_a.random()
rng_b = random.Random(42)
out_static = param_engine.instantiate_bank(static_rows, rng_b)
check("static rows identical objects",
      all(o is s for o, s in zip(out_static, static_rows)))
check("static rows consume no RNG", rng_b.random() == before)

# ------------------------------------------ the converted math bank itself
bank = generator.load_full_bank(
    [{"path": "Test Bank Module 1 Math.xlsx", "topic": "Math"}],
    base_dir=ELLIS_DATA)
check("bank has 21 questions", len(bank) == 21, str(len(bank)))
check("all rows parameterized or placeholdered",
      all(r.get("params") or r["block_id"] is not None for r in bank))

marker = re.compile(r"\[\[|\]\]")
FIELDS = ["Text", "a", "b", "c", "d", "b_info"]


def parse_amount(s):
    """Numeric value of a formatted choice like '\\$1,235', '2.24', '5\\%'."""
    t = s.replace("\\$", "").replace("\\%", "").replace(",", "").strip()
    return float(t)


n_instances = 0
seen_correct = {}
for seed in range(300):
    rr = random.Random(seed)
    inst = param_engine.instantiate_bank(bank, rr)
    for orow in inst:
        for f in FIELDS:
            v = orow.get(f)
            if isinstance(v, str) and marker.search(v):
                check("no leftover markers (seed %d q %s)" % (seed, orow["q_id"]),
                      False, repr(v))
        choices = [orow[k].strip() for k in ("a", "b", "c", "d")
                   if orow[k] is not None]
        if len(set(choices)) != len(choices):
            check("distinct choices (seed %d q %s)" % (seed, orow["q_id"]),
                  False, repr(choices))
        seen_correct.setdefault(orow["q_id"], set()).add(orow["a"])
    n_instances += 1
print("ok    stress: 300 seeds instantiated cleanly")

varying = [qid for qid, vals in seen_correct.items() if len(vals) > 1]
check("every question's correct answer varies across seeds",
      len(varying) == len(seen_correct),
      "constant: " + str(sorted(set(seen_correct) - set(varying))))

# Independent recomputation of a sample of correct answers. Parameters are
# recovered from the printed question text, so this checks the whole chain
# (draw -> text -> correct formula) for internal consistency.
inst = param_engine.instantiate_bank(bank, random.Random(2026))
by_qid = {int(r["q_id"]): r for r in inst}

# q19: text shows p (as a percent) and n; correct = 1 - (1-p)^n.
q19 = by_qid[19]
m = re.search(r"there's a (\d+)\\% chance.*?has (\d+) policyholders",
              q19["Text"], re.S)
p, n = int(m.group(1)) / 100.0, int(m.group(2))
check("q19 correct recomputed",
      abs(parse_amount(q19["a"]) - round(1 - (1 - p) ** n, 2)) < 1e-9,
      q19["a"] + " vs p=%s n=%s" % (p, n))

# q15: two-point table; correct = p * L.
q15 = by_qid[15]
m = re.search(r"\\\$([1-9][\d,]*)\s*&\s*(0\.\d)", q15["Text"])
L, p = parse_amount(m.group(1)), float(m.group(2))
check("q15 correct recomputed",
      abs(parse_amount(q15["a"]) - p * L) < 0.5, q15["a"])

# q2/q3 (block 1): b_info shows F and p; the question text shows prem.
q2, q3 = by_qid[2], by_qid[3]
m = re.search(r"pays \\\$([\d,]+).*?year is ([\d.]+)\.", q2["b_info"], re.S)
F, p = parse_amount(m.group(1)), float(m.group(2))
prem = parse_amount(re.search(r"charges \\\$([\d,]+)", q2["Text"]).group(1))
check("q2 correct recomputed",
      abs(parse_amount(q2["a"]) - (prem - F * p)) < 0.5,
      "%s vs prem=%s F=%s p=%s" % (q2["a"], prem, F, p))
import math
check("q3 correct recomputed",
      abs(parse_amount(q3["a"]) - F * math.sqrt(p * (1 - p))) < 0.51,
      q3["a"])

# q8-q12 (block 3): recompute all five premiums from the printed scenario.
q8 = by_qid[8]
probs = re.findall(r"(\d+)\\% chance of a \\\$([\d,]+) loss", q8["b_info"])
dist = [(int(pc) / 100.0, parse_amount(amt)) for pc, amt in probs]
check("q8 scenario parsed", len(dist) == 3, repr(q8["b_info"]))
EV = sum(pi * li for pi, li in dist)
check("q8 correct recomputed",
      abs(parse_amount(q8["a"]) - round(EV / 100) * 100) < 1e-6, q8["a"])
q9 = by_qid[9]
s = int(re.search(r"insurer pays (\d+)\\%", q9["Text"]).group(1)) / 100.0
check("q9 correct recomputed",
      abs(parse_amount(q9["a"]) - round(s * EV)) < 0.51, q9["a"])
q10 = by_qid[10]
ded = parse_amount(re.search(r"\\\$([\d,]+) deductible", q10["Text"]).group(1))
want10 = sum(pi * max(0.0, li - ded) for pi, li in dist)
check("q10 correct recomputed",
      abs(parse_amount(q10["a"]) - round(want10)) < 0.51, q10["a"])
q11 = by_qid[11]
lim = parse_amount(re.search(r"\\\$([\d,]+) coverage limit",
                             q11["Text"]).group(1))
want11 = sum(pi * min(li, lim) for pi, li in dist)
check("q11 correct recomputed",
      abs(parse_amount(q11["a"]) - round(want11)) < 0.51, q11["a"])
q12 = by_qid[12]
want12 = sum(pi * min(s * max(0.0, li - ded), lim) for pi, li in dist)
check("q12 correct recomputed",
      abs(parse_amount(q12["a"]) - round(want12)) < 0.51, q12["a"])

# q13: term life; exact survival-probability computation.
q13 = by_qid[13]
F13 = parse_amount(re.search(r"pays out \\\$([\d,]+)", q13["Text"]).group(1))
p1v, p2v = [float(x) for x in re.findall(r"insured is ([\d.]+) for the "
                                         r"first|and ([\d.]+) for the last",
                                         q13["Text"]) for x in x if x]
want13 = F13 * (1 - (1 - p1v) ** 5 * (1 - p2v) ** 5)
check("q13 correct recomputed",
      abs(parse_amount(q13["a"]) - round(want13 / 100) * 100) < 1e-6,
      "%s vs %s" % (q13["a"], want13))

# --------------------------------- the Topic 3 risk-pooling block (q18-q21)
t3 = generator.load_full_bank(
    [{"path": "Test Bank Topic 3.xlsx", "topic": "Topic 3"}],
    base_dir=ELLIS_DATA)
check("topic 3 has 50 questions", len(t3) == 50, str(len(t3)))
t3_static = {r["q_id"]: r for r in param_engine.instantiate_bank(
    t3, random.Random(0))}
untouched = [r["q_id"] for r, o in zip(
    param_engine.instantiate_bank(t3, random.Random(0)), t3) if r is o]
check("topic 3: only the block is instantiated",
      sorted(int(q) for q in set(r["q_id"] for r in t3) - set(untouched))
      == [18, 19, 20, 21], repr(sorted(untouched)))

for seed in range(300):
    rr = random.Random(seed)
    inst = {r["q_id"]: r for r in param_engine.instantiate_bank(t3, rr)}
    q18, q19, q20, q21 = inst["18"], inst["19"], inst["20"], inst["21"]
    # Recover p, L, LC from the printed scenario.
    mm = re.findall(r"a (\d+)\\% chance of having a loss of \\\$(\d+)\.",
                    q18["b_info"])
    if len(mm) != 3:
        check("t3 seed %d scenario parsed" % seed, False, repr(q18["b_info"]))
        break
    p = int(mm[0][0]) / 100.0
    L, LB, LC = (float(x[1]) for x in mm)
    ok = (
        L == LB and LC > L
        and q18["a"].endswith("\\$%s." % param_engine.num(p * L))
        and q18["b"].endswith("\\$%s." % param_engine.num(L))
        and q18["c"].endswith("is %s." % param_engine.num(
            math.sqrt((1 - p) / p), 2))
        and q18["d"].endswith("is %s." % param_engine.num(
            L * math.sqrt(p * (1 - p)), 2))
        and q19["c"].endswith("about %s." % param_engine.num(
            math.sqrt((1 - p) / p) / math.sqrt(2), 2))
        and ("\\$%s." % param_engine.num((p * L + p * LC) / 2)) in q20["Text"]
        and abs((p * L + p * LC) / 2 - round((p * L + p * LC) / 2)) < 1e-9
        and abs(p * L - round(p * L)) < 1e-9
        and q21["Text"] == t3_static["21"]["Text"]  # q21 stays static
    )
    if not ok:
        check("t3 seed %d recomputed" % seed, False,
              "p=%s L=%s LC=%s %r" % (p, L, LC, [q18, q19, q20]))
        break
else:
    print("ok    topic 3 block: 300 seeds recomputed (premium, CV, pool)")

# ----------------------- full back-pass: every math question, ground truth
# recomputed from the PRINTED text (not the formulas), plus a numeric check
# that no distractor value ever equals the correct value (the engine's
# string check cannot catch a same-value collision printed in a different
# format).
from param_engine import dollar as D, num as N, pct as P


def _dist(binfo):
    """The 'x% chance of a $L loss' triples from a block scenario."""
    return [(int(pc) / 100.0, parse_amount(amt)) for pc, amt in
            re.findall(r"(\d+)\\% chance of a \\\$([\d,]+) loss", binfo)]


def gt_q1(q, _):
    p = float(re.search(r"winning is p = (\d+(?:\.\d+)?)", q["Text"]).group(1))
    qq = re.search(r"losing is q = (\d+(?:\.\d+)?)", q["Text"]).group(1)
    assert qq == N(1 - p, 4), "q1 printed q inconsistent: " + qq
    return N(math.sqrt((1 - p) / p), 2)


def gt_q2(q, by):
    m = re.search(r"pays \\\$([\d,]+).*?year is (\d+(?:\.\d+)?)\.",
                  by[2]["b_info"], re.S)
    F, p = parse_amount(m.group(1)), float(m.group(2))
    prem = parse_amount(re.search(r"charges \\\$([\d,]+)", q["Text"]).group(1))
    return D(prem - F * p)


def gt_q3(q, by):
    m = re.search(r"pays \\\$([\d,]+).*?year is (\d+(?:\.\d+)?)\.",
                  by[2]["b_info"], re.S)
    F, p = parse_amount(m.group(1)), float(m.group(2))
    return D(F * math.sqrt(p * (1 - p)))


def gt_q4(q, _):
    h = float(re.search(r"high-risk drivers is (\d+(?:\.\d+)?)\.",
                        q["Text"]).group(1))
    ph = float(re.search(r"high-risk driver having an accident in a year "
                         r"is (\d+(?:\.\d+)?)\.", q["Text"]).group(1))
    return N((h * ph) ** 3, 4)


def gt_q5(q, by):
    return D(sum(p * L for p, L in _dist(by[5]["b_info"])), 100)


def gt_q6(q, by):
    d = _dist(by[5]["b_info"])
    ev = sum(p * L for p, L in d)
    return N(sum(p * L * L for p, L in d) - ev * ev, 0, 1000)


def gt_q7(q, by):
    d = _dist(by[5]["b_info"])
    ev = sum(p * L for p, L in d)
    v = sum(p * L * L for p, L in d) - ev * ev
    return N(math.sqrt(v) / ev, 1)


def gt_q8(q, by):
    return D(sum(p * L for p, L in _dist(by[8]["b_info"])), 100)


def gt_q9(q, by):
    d = _dist(by[8]["b_info"])
    s = int(re.search(r"insurer pays (\d+)\\%", q["Text"]).group(1)) / 100.0
    return D(s * sum(p * L for p, L in d))


def gt_q10(q, by):
    d = _dist(by[8]["b_info"])
    ded = parse_amount(re.search(r"\\\$([\d,]+) deductible",
                                 q["Text"]).group(1))
    return D(sum(p * max(0.0, L - ded) for p, L in d))


def gt_q11(q, by):
    d = _dist(by[8]["b_info"])
    lim = parse_amount(re.search(r"\\\$([\d,]+) coverage limit",
                                 q["Text"]).group(1))
    return D(sum(p * min(L, lim) for p, L in d))


def gt_q12(q, by):
    d = _dist(by[8]["b_info"])
    s = int(re.search(r"insurer pays (\d+)\\%", q["Text"]).group(1)) / 100.0
    ded = parse_amount(re.search(r"\\\$([\d,]+) deductible",
                                 q["Text"]).group(1))
    lim = parse_amount(re.search(r"maximum insurer payment of "
                                 r"\\\$([\d,]+)", q["Text"]).group(1))
    return D(sum(p * min(s * max(0.0, L - ded), lim) for p, L in d))


def gt_q13(q, _):
    F = parse_amount(re.search(r"pays out \\\$([\d,]+)", q["Text"]).group(1))
    p1 = float(re.search(r"insured is (\d+(?:\.\d+)?) for the first",
                         q["Text"]).group(1))
    p2 = float(re.search(r"and (\d+(?:\.\d+)?) for the last", q["Text"]).group(1))
    return D(F * (1 - (1 - p1) ** 5 * (1 - p2) ** 5), 100)


def gt_q14(q, _):
    w = [float(x) for x in re.search(
        r"category are (\d+(?:\.\d+)?), (\d+(?:\.\d+)?), and (\d+(?:\.\d+)?), respectively",
        q["Text"]).groups()]
    c = [parse_amount(x) for x in re.search(
        r"are \\\$([\d,]+), \\\$([\d,]+), and \\\$([\d,]+), respectively",
        q["Text"]).groups()]
    return D(sum(wi * ci for wi, ci in zip(w, c)))


def _table(text):
    """(loss, prob) rows of a printed distribution table, $0 row included."""
    return [(parse_amount(L), float(p)) for L, p in
            re.findall(r"\\\$([\d,]+)\s*&\s*(\d+(?:\.\d+)?)", text)]


def gt_q15(q, _):
    rows = [r for r in _table(q["Text"]) if r[0] > 0]
    assert len(rows) == 1, "q15 table: " + repr(rows)
    return D(rows[0][1] * rows[0][0])


def gt_q16(q, _):
    rows = [r for r in _table(q["Text"]) if r[0] > 0]
    assert len(rows) == 2, "table: " + repr(rows)
    return D(sum(p * L for L, p in rows))


def gt_q19(q, _):
    p = int(re.search(r"there's a (\d+)\\% chance", q["Text"]).group(1)) / 100.0
    n = int(re.search(r"has (\d+)\s+policyholders", q["Text"]).group(1))
    return N(1 - (1 - p) ** n, 2)


def gt_q20(q, _):
    pf, pe, pw = (float(x) / 100.0 for x in re.search(
        r"are (\d+(?:\.\d+)?)\\%, (\d+(?:\.\d+)?)\\%, and (\d+(?:\.\d+)?)\\%",
        q["Text"]).groups())
    return P(pf + pw, 1)


def gt_q21(q, _):
    pt, pfire, pfl = (float(x) / 100.0 for x in re.search(
        r"are (\d+(?:\.\d+)?)\\%, (\d+(?:\.\d+)?)\\%, and (\d+(?:\.\d+)?)\\%",
        q["Text"]).groups())
    return P(pt * pfl, 4)


GROUND_TRUTH = {1: gt_q1, 2: gt_q2, 3: gt_q3, 4: gt_q4, 5: gt_q5, 6: gt_q6,
                7: gt_q7, 8: gt_q8, 9: gt_q9, 10: gt_q10, 11: gt_q11,
                12: gt_q12, 13: gt_q13, 14: gt_q14, 15: gt_q15, 16: gt_q16,
                17: gt_q16, 18: gt_q16, 19: gt_q19, 20: gt_q20, 21: gt_q21}

backpass_fail = 0
for seed in range(100):
    by = {int(r["q_id"]): r for r in
          param_engine.instantiate_bank(bank, random.Random(1000 + seed))}
    for qid, gt in GROUND_TRUTH.items():
        qr = by[qid]
        want = gt(qr, by)
        got = qr[qr["correct"]].strip()
        if got != want.strip():
            check("backpass q%d seed %d" % (qid, seed), False,
                  "printed %r, ground truth %r" % (got, want))
            backpass_fail += 1
        # no distractor value may equal the correct value
        cv = parse_amount(got)
        for k in ("a", "b", "c", "d"):
            if k == qr["correct"] or qr[k] is None:
                continue
            if abs(parse_amount(qr[k]) - cv) < 1e-9:
                check("backpass q%d seed %d distractor %s" % (qid, seed, k),
                      False, "equals correct: " + repr(qr[k]))
                backpass_fail += 1
    if backpass_fail:
        break
else:
    print("ok    back-pass: all 21 questions x 100 seeds recomputed from "
          "printed text; no distractor ever equals the correct value")

# ------------------------------------------------- end-to-end generate_exam
def gen(seed):
    res = generator.generate_exam(
        bank, ["Math"], 21, seed, False, "intro", "Spring 2026",
        "FIN 3400", exam_dir=os.path.join(HERE, "out_param"),
        num_versions_input=1, title_input="Practice Exam:")
    return res


res1, res2, res3 = gen("123"), gen("123"), gen("456")
check("generate ok", res1["status"] == "ok", repr(res1)[:200])
check("same seed reproduces numbers", res1["tex"] == res2["tex"])
check("different seed changes numbers", res1["tex"] != res3["tex"])
check("no [[ ]] in generated tex", "[[" not in res1["tex"]
      and "]]" not in res1["tex"])
check("no raw params leak into tex", "pick(" not in res1["tex"])

print()
if failures:
    print("FAILURES:", len(failures))
    sys.exit(1)
print("All param-engine tests passed.")
