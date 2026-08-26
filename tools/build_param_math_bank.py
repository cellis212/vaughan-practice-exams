"""Regenerate the parameterized "Test Bank Module 1 Math.xlsx" (central bank store).

Each question is a template: the `params` column draws the numbers, the
Text / choice / b_info cells embed [[expr]] placeholders, and column `a`
always holds the correct-answer formula (`correct` = "a"; rc() shuffles
choices at generation time, so the printed position still varies).
Distractor formulas encode classic wrong methods (variance instead of SD,
forgot the deductible, added instead of multiplied, ...), so every draw
yields a plausible, internally consistent question with a correct key.

Run from the repo root:  python3 tools/build_param_math_bank.py
"""

import os

import openpyxl

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "banks", "intro-to-rmi", "Test Bank Module 1 Math.xlsx",
)

COLUMNS = ["Topic", "Text", "a", "b", "c", "d", "extras", "correct",
           "idea_id", "block_id", "q_id", "b_info", "params"]

BLOCK_HEADER = ("\t\\textbf{Questions \\thefirst --\\thelast \\ are based "
                "on the following information:}\n\t")


def q(q_id, text, a, b, c, d, params=None, block_id=None, b_info=None):
    return {
        "Topic": "1m", "Text": text, "a": a, "b": b, "c": c, "d": d,
        "extras": "y", "correct": "a", "idea_id": None,
        "block_id": block_id, "q_id": q_id, "b_info": b_info,
        "params": params,
    }


ROWS = [
    # ------------------------------------------------------------------
    # Q1: coefficient of variation of a win/lose gamble. CV = sqrt(q/p)
    # regardless of the prize W (W is a deliberate red herring).
    q(1,
      "Consider a game where the probability of winning is p = [[num(p,4)]] "
      "and the probability of losing is q = [[num(1-p,4)]]. If you win, you "
      "receive \\$[[W]]; otherwise you receive nothing. What is the "
      "coefficient of variation for this probability distribution? "
      "(round to nearest .00s)",
      "[[num(sqrt((1-p)/p), 2)]]",     # correct: CV = sd/mean = sqrt(q/p)
      "[[num(sqrt(p*(1-p)), 2)]]",     # sd of the indicator, not the CV
      "[[num(p*(1-p), 2)]]",           # variance of the indicator
      "[[num(sqrt(p/(1-p)), 2)]]",     # inverted ratio
      params="p = pick(0.1, 0.125, 0.1667, 0.2, 0.25)\n"
             "W = pick(1, 5, 10, 20)"),

    # ------------------------------------------------------------------
    # Block 1 (q2-q3): one-year life policy, payout F w.p. p, premium prem.
    q(2,
      "What is the expected value of the underwriting profit for the "
      "insurance company if it charges \\$[[num(prem)]]? "
      "(round to nearest 0s)",
      "[[dollar(prem - EL)]]",         # correct: premium - expected loss
      "[[dollar(prem)]]",              # ignored expected losses
      "\\$0",                          # assumed actuarially fair
      "[[dollar(EL - prem)]]",         # sign error
      params="F = pick(10000, 20000, 25000, 50000)\n"
             "p = pick(0.002, 0.004, 0.005, 0.008, 0.01)\n"
             "m = pick(2, 5, 10)\n"
             "EL = F * p\n"
             "prem = EL * m",
      block_id=1,
      b_info=BLOCK_HEADER + "A life insurance company sells a policy that "
             "pays \\$[[num(F)]] if a person dies within a year.  The "
             "probability that a randomly selected person dies within the "
             "year is [[num(p,3)]].  "),
    q(3,
      "What is the standard deviation of the underwriting profit for the "
      "insurance company if it charges \\$[[num(prem)]]? "
      "(round to nearest 0s)",
      "[[dollar(F * sqrt(p*(1-p)))]]",  # correct: SD of profit = F*sd(indicator)
      "[[dollar(F*F * p*(1-p))]]",      # variance, not SD
      "[[dollar(prem - EL)]]",          # the expected profit instead
      "[[dollar(EL)]]",                 # the expected loss instead
      block_id=1),

    # ------------------------------------------------------------------
    # Q4: joint probability of selecting 3 high-risk drivers who all crash.
    q(4,
      "A car insurance company classifies drivers into two categories: "
      "low-risk and high-risk. The proportion of high-risk drivers is "
      "[[num(h,1)]].  The probability of a low-risk driver having an "
      "accident in a year is [[num(pl,2)]].  The probability of a "
      "high-risk driver having an accident in a year is [[num(ph,2)]].  "
      "If the company randomly selects 3 drivers, what is the probability "
      "that they are all high-risk and all have an accident? "
      "(round to nearest .0000s)",
      "[[num((h*ph)**3, 4)]]",         # correct
      "[[num(ph**3, 4)]]",             # forgot the high-risk selection
      "[[num(h**3, 4)]]",              # forgot the accidents
      "[[num(h*ph, 4)]]",              # forgot to cube
      params="h = pick(0.3, 0.4, 0.5)\n"
             "ph = pick(0.2, 0.25, 0.3, 0.4)\n"
             "pl = pick(0.05, 0.1)"),

    # ------------------------------------------------------------------
    # Block 2 (q5-q7): fire policy with a four-point loss distribution.
    q(5,
      "What is the expected loss? (round to nearest 00s)",
      "[[dollar(EV, 100)]]",                       # correct
      "[[dollar(p1*L3 + p2*L2 + p3*L1, 100)]]",    # reversed weights
      "[[dollar((L1+L2+L3)/4, 100)]]",             # unweighted average
      "[[dollar(p1*L1 + p2*L2, 100)]]",            # dropped the largest loss
      params="p1 = pick(0.01, 0.02, 0.03)\n"
             "p2 = pick(0.01, 0.02, 0.03)\n"
             "p3 = pick(0.01, 0.02)\n"
             "L1 = pick(5000, 10000, 20000)\n"
             "L2 = pick(40000, 50000, 60000)\n"
             "L3 = pick(80000, 100000, 120000)\n"
             "EV = p1*L1 + p2*L2 + p3*L3\n"
             "EX2 = p1*L1**2 + p2*L2**2 + p3*L3**2\n"
             "V = EX2 - EV**2",
      block_id=2,
      b_info=BLOCK_HEADER + "A fire insurance policy covers a building for "
             "losses up to \\$[[num(L3)]].  The probability distribution of "
             "the losses is: [[pct(1-p1-p2-p3,0)]] chance of no loss; "
             "[[pct(p1,0)]] chance of a \\$[[num(L1)]] loss; [[pct(p2,0)]] "
             "chance of a \\$[[num(L2)]] loss; and a [[pct(p3,0)]] chance "
             "of a \\$[[num(L3)]] loss."),
    q(6,
      "What is the variance of the loss? (round to nearest 000s)",
      "[[num(V, 0, 1000)]]",           # correct
      "[[num(EX2, 0, 1000)]]",         # E[X^2], forgot to subtract mean^2
      "[[num(sqrt(V), 0, 1000)]]",     # the SD, not the variance
      "[[num(EV**2, 0, 1000)]]",       # mean squared
      block_id=2),
    q(7,
      "What is the coefficient of variation? (round to nearest .0s)",
      "[[num(sqrt(V)/EV, 1)]]",        # correct: SD / mean
      "[[num(EV/sqrt(V), 1)]]",        # inverted
      "[[num(V/EV**2, 1)]]",           # CV squared
      "[[num(V/EV, 1)]]",              # used variance instead of SD
      block_id=2),

    # ------------------------------------------------------------------
    # Block 3 (q8-q12): health policy; premiums under coinsurance,
    # deductible, coverage limit, and their combination.
    q(8,
      "What is the actuarially fair premium for full insurance? "
      "(round to nearest 00s)",
      "[[dollar(EV, 100)]]",                            # correct
      "[[dollar((L1+L2+L3)*(p1+p2+p3), 100)]]",         # sums x sums
      "[[dollar((L1+L2+L3)/4, 100)]]",                  # unweighted average
      "[[dollar(p3*L3, 100)]]",                         # worst case only
      params="p1 = pick(0.04, 0.05, 0.06, 0.08)\n"
             "p2 = pick(0.02, 0.03, 0.04)\n"
             "p3 = pick(0.01, 0.02)\n"
             "L1 = 10000\n"
             "L2 = 50000\n"
             "L3 = pick(100000, 150000)\n"
             "ded = pick(15000, 20000, 25000)\n"
             "s = pick(0.7, 0.75, 0.8, 0.9)\n"
             "lim = pick(40000, 50000, 60000)\n"
             "EV = p1*L1 + p2*L2 + p3*L3",
      block_id=3,
      b_info=BLOCK_HEADER + "A health insurance company covers medical "
             "expenses for its customers.  The probability distribution of "
             "the total expenses is [[pct(1-p1-p2-p3,0)]] chance of no "
             "loss; [[pct(p1,0)]] chance of a \\$[[num(L1)]] loss; "
             "[[pct(p2,0)]] chance of a \\$[[num(L2)]] loss; and a "
             "[[pct(p3,0)]] chance of a \\$[[num(L3)]] loss.\n\n"),
    q(9,
      "What is the actuarially fair premium for insurance with an "
      "[[pct(s,0)]]/[[pct(1-s,0)]] co-insurance, where the insurer pays "
      "[[pct(s,0)]] of the expenses and the customer pays the other "
      "[[pct(1-s,0)]]? (round to nearest 0s)",
      "[[dollar(s*EV)]]",              # correct
      "[[dollar(EV)]]",                # ignored the coinsurance
      "[[dollar((1-s)*EV)]]",          # the customer's share
      "[[dollar(EV/2)]]",              # split it in half
      block_id=3),
    q(10,
      "What is the actuarially fair premium for insurance with a "
      "\\$[[num(ded)]] deductible, where the customer pays the first "
      "\\$[[num(ded)]] of all losses and the insurer pays everything above "
      "that? (round to nearest 0s)",
      "[[dollar(p1*max(0, L1-ded) + p2*max(0, L2-ded) + p3*max(0, L3-ded))]]",
      "[[dollar(EV)]]",                        # ignored the deductible
      "[[dollar(EV - ded*(p1+p2+p3))]]",       # subtracted ded below the ded too
      "[[dollar(p3*max(0, L3-ded))]]",         # only the largest loss
      block_id=3),
    q(11,
      "What is the actuarially fair premium for insurance with a "
      "\\$[[num(lim)]] coverage limit, where the insurer pays the first "
      "\\$[[num(lim)]] of losses and the customer pays everything above "
      "that? (round to nearest 0s)",
      "[[dollar(p1*min(L1,lim) + p2*min(L2,lim) + p3*min(L3,lim))]]",
      "[[dollar(EV)]]",                        # ignored the limit
      "[[dollar(p1*(L1 if L1<=lim else 0) + p2*(L2 if L2<=lim else 0) "
      "+ p3*(L3 if L3<=lim else 0))]]",        # losses above limit "not covered"
      "[[dollar(lim*(p1+p2+p3))]]",            # limit times claim probability
      block_id=3),
    q(12,
      "What is the actuarially fair premium for insurance with an "
      "[[pct(s,0)]]/[[pct(1-s,0)]] co-insurance, a \\$[[num(ded)]] "
      "deductible, and a \\$[[num(lim)]] coverage limit? (The customer "
      "pays the first \\$[[num(ded)]], the insurer pays [[pct(s,0)]] of "
      "losses after that up to a maximum insurer payment of "
      "\\$[[num(lim)]]) (round to nearest 0s)",
      "[[dollar(p1*min(s*max(0,L1-ded), lim) + p2*min(s*max(0,L2-ded), lim)"
      " + p3*min(s*max(0,L3-ded), lim))]]",    # correct
      "[[dollar(s*(EV - ded*(p1+p2+p3)))]]",   # no cap, ded below the ded too
      "[[dollar(s*EV)]]",                      # coinsurance only
      "[[dollar(p1*max(0,L1-ded) + p2*max(0,L2-ded) + p3*max(0,L3-ded))]]",
      block_id=3),                             # deductible only

    # ------------------------------------------------------------------
    # Q13: 10-year term life, two mortality regimes; exact survival math
    # vs. the naive expected-payout shortcut.
    q(13,
      "A single premium life insurance policy pays out \\$[[num(F)]] if "
      "the insured dies within 10 years, and nothing otherwise.  The "
      "annual probability of death for the insured is [[num(p1,3)]] for "
      "the first 5 years and [[num(p2,3)]] for the last 5 years.  Ignoring "
      "discounting and investment returns, what is the actuarially fair "
      "premium for this policy? (round to nearest 00s)",
      "[[dollar(F*(1 - (1-p1)**5 * (1-p2)**5), 100)]]",  # correct
      "[[dollar(F*(5*p1 + 5*p2), 100)]]",                # naive sum of rates
      "[[dollar(F*(1 - (1-p1)**10), 100)]]",             # early rate throughout
      "[[dollar(F*(1 - (1-p2)**10), 100)]]",             # late rate throughout
      params="F = pick(100000, 200000, 250000, 500000)\n"
             "p1 = pick(0.004, 0.005, 0.006)\n"
             "p2 = pick(0.008, 0.01, 0.012)"),

    # ------------------------------------------------------------------
    # Q14: mixture expected value across three risk classes.
    q(14,
      "An auto insurance company classifies drivers into three risk "
      "categories: low, medium, and high.  The proportions of drivers in "
      "each category are [[num(w1,1)]], [[num(w2,1)]], and [[num(w3,1)]], "
      "respectively. The expected claim amounts for each category are "
      "\\$[[num(c1)]], \\$[[num(c2)]], and \\$[[num(c3)]], respectively. "
      "What is the expected claim amount for a randomly selected driver? "
      "(round to nearest 0s)",
      "[[dollar(w1*c1 + w2*c2 + w3*c3)]]",     # correct
      "[[dollar((c1+c2+c3)/3)]]",              # unweighted average
      "[[dollar(w3*c1 + w2*c2 + w1*c3)]]",     # reversed weights
      "[[dollar(c2)]]",                        # just the middle category
      params="w1 = pick(0.5, 0.6, 0.7)\n"
             "w2 = pick(0.2, 0.3)\n"
             "w3 = round(1 - w1 - w2, 10)\n"
             "require(w3 >= 0.1)\n"
             "c1 = pick(400, 500, 600)\n"
             "c2 = pick(700, 800, 900)\n"
             "c3 = pick(1000, 1200, 1500)"),

    # ------------------------------------------------------------------
    # Q15: expected value of a two-point distribution (table).
    q(15,
      "\\begin{tabular}{|c|c|}\n\\hline\nLoss & Probability \\\\ \\hline\n"
      "\\$0    & [[num(1-p,1)]]         \\\\ \\hline\n"
      "\\$[[num(L)]]  & [[num(p,1)]]         \\\\ \\hline\n"
      "\\end{tabular}\n\nGiven the above probability distribution table "
      "for a random variable Y, what is the expected value of Y? "
      "(round to nearest 0s)",
      "[[dollar(p*L)]]",               # correct
      "\\$0",                          # the modal outcome
      "[[dollar(L)]]",                 # the loss itself
      "[[dollar((1-p)*L)]]",           # wrong probability
      params="p = pick(0.2, 0.3, 0.4, 0.6, 0.7)\n"
             "L = pick(200, 500, 1000)"),

    # ------------------------------------------------------------------
    # Q16-Q18: expected value of a three-point distribution (table); the
    # same template three times with different parameter pools, so each
    # instance draws its own flavor of the problem.
    q(16,
      "Find the expected value for this distribution: \n"
      "\\begin{tabular}{|c|c|}\n\\hline\nLoss & Probability \\\\ \\hline\n"
      "\\$0    & [[num(p0,1)]]         \\\\ \\hline\n"
      "\\$[[num(L1)]]  & [[num(p1,1)]]         \\\\ \\hline\n"
      "\\$[[num(L2)]] & [[num(p2,1)]]         \\\\ \\hline\n"
      "\\end{tabular} \n(round to nearest 0s)",
      "[[dollar(p1*L1 + p2*L2)]]",     # correct
      "\\$0",                          # the modal outcome
      "[[dollar((L1+L2)/2)]]",         # average of the nonzero losses
      "[[dollar(p2*L1 + p1*L2)]]",     # swapped probabilities
      params="p1 = pick(0.2, 0.3, 0.4)\n"
             "p2 = pick(0.1, 0.2, 0.3)\n"
             "p0 = round(1 - p1 - p2, 10)\n"
             "require(p0 >= 0.2)\n"
             "L1 = pick(50, 100)\n"
             "L2 = pick(150, 200, 250)"),
    q(17,
      "Find the expected value for this distribution: \n"
      "\\begin{tabular}{|c|c|}\n\\hline\nLoss & Probability \\\\ \\hline\n"
      "\\$0    & [[num(p0,1)]]         \\\\ \\hline\n"
      "\\$[[num(L1)]]  & [[num(p1,1)]]         \\\\ \\hline\n"
      "\\$[[num(L2)]] & [[num(p2,1)]]         \\\\ \\hline\n"
      "\\end{tabular} \n(round to nearest 0s)",
      "[[dollar(p1*L1 + p2*L2)]]",
      "\\$0",
      "[[dollar((L1+L2)/2)]]",
      "[[dollar(p2*L1 + p1*L2)]]",
      params="p1 = pick(0.3, 0.4, 0.5)\n"
             "p2 = pick(0.2, 0.3, 0.4)\n"
             "p0 = round(1 - p1 - p2, 10)\n"
             "require(p0 >= 0.1)\n"
             "L1 = pick(100, 150, 200)\n"
             "L2 = pick(250, 300, 400)"),
    q(18,
      "Find the expected value for this distribution: \n"
      "\\begin{tabular}{|c|c|}\n\\hline\nLoss & Probability \\\\ \\hline\n"
      "\\$0    & [[num(p0,1)]]         \\\\ \\hline\n"
      "\\$[[num(L1)]]  & [[num(p1,1)]]         \\\\ \\hline\n"
      "\\$[[num(L2)]] & [[num(p2,1)]]         \\\\ \\hline\n"
      "\\end{tabular} \n(round to nearest 0s)",
      "[[dollar(p1*L1 + p2*L2)]]",
      "\\$0",
      "[[dollar((L1+L2)/2)]]",
      "[[dollar(p2*L1 + p1*L2)]]",
      params="p1 = pick(0.2, 0.3, 0.4)\n"
             "p2 = pick(0.2, 0.3, 0.4)\n"
             "p0 = round(1 - p1 - p2, 10)\n"
             "require(p0 >= 0.2)\n"
             "L1 = pick(50, 100, 150)\n"
             "L2 = pick(200, 250, 300)"),

    # ------------------------------------------------------------------
    # Q19: probability of at least one claim among n policyholders.
    q(19,
      "Assume there's a [[pct(p,0)]] chance that a policyholder will file "
      "a claim within a year. If an insurance company has [[n]] "
      "policyholders, what is the probability that at least 1 policyholder "
      "will file a claim? (round to nearest .00s)",
      "[[num(1 - (1-p)**n, 2)]]",      # correct: complement of no claims
      "[[num((1-p)**n, 2)]]",          # probability of NO claims
      "[[num(n*p, 2)]]",               # added the probabilities
      "[[num(p, 2)]]",                 # ignored the portfolio
      params="p = pick(0.02, 0.03, 0.05, 0.08, 0.1)\n"
             "n = pick(5, 10, 15, 20)\n"
             "require(n * p < 1)"),

    # ------------------------------------------------------------------
    # Q20: mutually exclusive events -> add the probabilities.
    q(20,
      "An insurance company covers homes against natural disasters. The "
      "annual probabilities that a claim is made for flood, earthquake, "
      "and wind damage are [[pct(pf,1)]], [[pct(pe,1)]], and "
      "[[pct(pw,1)]], respectively. Assuming each type of claim is "
      "mutually exclusive of the others, what is the probability that a "
      "policyholder will make a claim for either flood or wind damage in "
      "a year?",
      "[[pct(pf+pw,1)]]",              # correct
      "[[pct(pf+pe+pw,1)]]",           # added all three
      "[[pct(pw,1)]]",                 # forgot flood
      "[[pct(pf+pe,1)]]",              # wrong pair
      params="pf = pick(0.001, 0.002, 0.003)\n"
             "pe = pick(0.001, 0.002)\n"
             "pw = pick(0.004, 0.005, 0.006)"),

    # ------------------------------------------------------------------
    # Q21: independent events -> multiply the probabilities.
    q(21,
      "An insurance company offers comprehensive home insurance that "
      "covers theft, fire, and flood. The probabilities of filing a claim "
      "for theft, fire, and flood in a year are [[pct(pt,1)]], "
      "[[pct(pfire,1)]], and [[pct(pfl,1)]], respectively. If the "
      "occurrences are independent, what is the probability that a "
      "homeowner will file a claim for both theft and flood in the same "
      "year?",
      "[[pct(pt*pfl,4)]]",             # correct
      "[[pct(pt+pfl,1)]]",             # added instead of multiplied
      "[[pct(pt*pfire,4)]]",           # wrong pair
      "[[pct(pt*pfire*pfl,6)]]",       # multiplied all three
      params="pt = pick(0.008, 0.01, 0.012)\n"
             "pfire = pick(0.004, 0.005, 0.006)\n"
             "pfl = pick(0.001, 0.002)"),
]


def main():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(COLUMNS)
    for row in ROWS:
        ws.append([row[c] for c in COLUMNS])
    wb.save(OUT)
    print("Wrote", len(ROWS), "questions to", OUT)


if __name__ == "__main__":
    main()
