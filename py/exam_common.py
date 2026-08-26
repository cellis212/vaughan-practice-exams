"""Python translation of the shared parts of "Functions and Options.R".

The functions rc(), fq(), fqb(), and make_fm() are byte-for-byte identical
between the RMI Intro and Life/Health versions of "Functions and Options.R",
so they live here once. The two create_exam() variants differ and live in
engine_intro.py / engine_lh.py.

Every function is a line-faithful port of its R counterpart, including R's
quirks (1-based indices, NA propagation into paste() as the string "NA",
sort() dropping NA values). Do not "clean up" the logic: the output .tex
must match what the R code produces.
"""

import random

# Global RNG, mirroring R's global random state used by sample().
# set_seed() mirrors set.seed(as.numeric(input$seed_input)) in app.R.
_rng = random.Random()


def set_seed(seed):
    """Mirror of R's set.seed(). seed is a float (R's as.numeric result)."""
    _rng.seed(seed)


def reseed_from_system():
    """Fresh nondeterministic state, mirroring R's default RNG behavior
    when no seed is supplied."""
    _rng.seed()


def r_sample_permutation(n):
    """Mirror of R's sample(n) / sample(1:n, n): a random permutation of
    1..n (1-based, like R)."""
    return _rng.sample(range(1, n + 1), n)


def r_char(v):
    """Convert a cell value to the string R's as.character()/paste0() would
    produce for it. None stays None (R's NA)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    return str(v)


def _p(v):
    """paste0-safe: R's paste0 renders NA as the string 'NA'."""
    return "NA" if v is None else str(v)


LETTERS = ["a", "b", "c", "d"]


def rc(dat):
    """Port of rc(): randomize choices for a single question.

    dat is a dict with keys Topic, Text, a, b, c, d, extras, correct,
    block_id, b_info, q_id (values are strings or None). Returns a new dict.
    """
    tdat = dict(dat)

    # Collect options into a vector, removing NA options
    options = [dat[k] for k in LETTERS]
    options = [o for o in options if o is not None]
    num_options = len(options)

    # Randomize options (excluding 'None of the above', which is added later)
    idx = r_sample_permutation(num_options)
    options_shuffled = [options[i - 1] for i in idx]

    # Update options in tdat (only the first num_options letters, like
    # tdat[option_names] <- as.list(options_shuffled) in R)
    option_names = LETTERS[:num_options]
    for name, val in zip(option_names, options_shuffled):
        tdat[name] = val

    # Update the correct answer(s)
    if dat["correct"] == "none":
        # If 'None of the above' is correct
        tdat["correct"] = "none"
    else:
        # Map the correct answers based on the shuffled indices
        poss = option_names
        correct_letters = list(dat["correct"])
        # correct_indices <- match(correct_letters, c('a','b','c','d')[1:num_options])
        correct_indices = [
            (option_names.index(cl) + 1) if cl in option_names else None
            for cl in correct_letters
        ]
        # new_indices <- match(correct_indices, idx)
        new_correct_letters = []
        for ci in correct_indices:
            if ci is None or ci not in idx:
                new_correct_letters.append(None)
            else:
                new_correct_letters.append(poss[idx.index(ci)])
        # paste(sort(...), collapse=""): R's sort() drops NA values
        tdat["correct"] = "".join(
            sorted(l for l in new_correct_letters if l is not None)
        )

    return tdat


def _format_question(dat):
    """The question-formatting body shared verbatim between fq() and the
    per-question loop inside fqb() in the R source."""
    dat = rc(dat)

    # Determine if 'None of the above' should be added
    if dat["extras"] == "n":
        # ifelse(is.na(dat$d), 4, 4) -- always 4; no 'None of the above'
        num_options = 4
        # Add "(Exactly One Correct Answer)" in bold at the start of the text
        dat["Text"] = "\\textbf{(Exactly One Correct Answer)} " + _p(dat["Text"])
    else:
        # Include 'None of the above' as the last option
        num_options = 4 if dat["d"] is None else 5

    # Begin question
    q_begin = "\\begin{question}\n[" + _p(dat["Topic"]) + "-" + _p(dat["q_id"]) + "]"

    # Choices (1-based dict mirroring R's list indexing)
    choices = {}
    choices[1] = "\n\\choice{" + _p(dat["a"]) + "}\n"
    choices[2] = "\\choice{" + _p(dat["b"]) + "}\n"
    choices[3] = "\\choice{" + _p(dat["c"]) + "}\n"
    if dat["d"] is not None:
        choices[4] = "\\choice{" + _p(dat["d"]) + "}\n"

    if dat["extras"] != "n":
        # 'None of the above' as the last option
        choices[num_options] = "\\choice{None of the above.}\n"

    # Marking Correct Answer(s)
    correct_letters = list(dat["correct"])
    poss = ["a", "b", "c", "d"]

    if dat["correct"] == "none" and dat["extras"] != "n":
        # If 'None of the above' is correct and 'extras' is not 'n'
        choices[num_options] = choices[num_options].replace(
            "\\choice{", "\\choice[!]{", 1
        )
    else:
        # For other correct answers
        for i, letter in enumerate(poss, start=1):
            if letter in correct_letters and i in choices:
                choices[i] = choices[i].replace("\\choice{", "\\choice[!]{", 1)

    q_end = "\\end{question}\n"

    # Combine question elements (c(qtab[1], dat$Text, choices, qtab[2]))
    ordered_choices = [choices[k] for k in sorted(choices.keys())]
    return [q_begin, _p(dat["Text"])] + ordered_choices + [q_end]


def fq(dat):
    """Port of fq(): format a single question into examdesign LaTeX pieces."""
    return _format_question(dat)


def fqb(tdat):
    """Port of fqb(): format a block of questions sharing b_info context.

    tdat is a list of row dicts (the block's rows, in bank order)."""
    nq = len(tdat)
    btab = []
    btab.append("\\begin{block}[questions=" + str(nq) + "]\n")
    btab.append(_p(tdat[0]["b_info"]))
    for row in tdat:
        btab.extend(_format_question(row))
    btab.append("\\end{block}\n")
    return btab


def make_fm(tit, sem, classnum):
    """Port of make_fm(): the exam front matter. Identical in both R files
    (they differ only in the default classnum, which is always passed)."""
    front = "".join([
        "\\begin{frontmatter}",
        "\\begin{center} \\textbf{", classnum, ":} \\textbf{", tit, "} \\textbf{", sem, "}\\ \\textbf{Version \\Alph{version}} \\vspace{2cm} \\end{center}",
        "{\\noindent Name: $\\rule{8cm}{.15mm}$ \\\\ \\\\",
        "{\\noindent Class Time: $\\rule{4cm}{.15mm}$ \\\\ \\\\",
        "\\examvspace{3cm} ",
        "\\textbf{INSTRUCTIONS:}   ",
        "\\bi",
        "\\item PUT YOUR FULL NAME AND EXAM VERSION NUMBER ON THE TOP OF YOUR SCANTRON.  YOU WILL NOT GET CREDIT IF YOU DO NOT DO THIS.",
        "\\item Mark the best answer(s) on your scantron.  You will not receive any credit for answers written on the exam itself.",
        "\\item Please use a pencil. Erase clearly if you want to change your answer.",
        "\\item Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; \nmark all that apply. ",
        "\\bi ",
        "\\item For example, if the correct answers are $a$, $b$, and $c$, then you should bubble in $a$, $b$, and $c$ on the scantron.",
        "\\ei",
        " \\item If I perceive that you are cheating, you will receive an F for the course.  Keep your eyes on your own paper. Note that you are being filmed.",
        " \\item Your cell phone is not allowed on your desk.",
        " \\item All caps, hats, and hoods must be removed.",
        " \\item No headphones allowed.",
        "\\ei",
        "}}",
        " \\end{frontmatter} ",
    ])
    return front
