"""Python translation of create_exam() from the RMI Intro (FIN 3400)
"Functions and Options.R" (RMI Intro Spring 2026 version).

Every string literal below is transcribed from the R source, preserving its
exact whitespace, indentation, and tabs, so the generated .tex is identical
to what the R code writes. Verified byte-for-byte by tests/parity_test.
"""

from exam_common import fq, fqb, make_fm


def create_exam(bank, qind, tit, sem, file, numVer=1, frontPage=False,
                max_q=9999, case=True, classnum="FIN 3400", real_exam=False,
                landscape=False):
    """bank: list of row dicts. qind: 1-based indices into bank (R-style).
    Returns the .tex content and writes it to `file`."""
    pdat = bank
    if landscape:
        layout_pkg = "\n    \\usepackage[landscape,margin=1in]{geometry}"
    else:
        layout_pkg = "\n    \\usepackage{fullpage}"
    if landscape:
        size_cmd = "\\small"
    else:
        size_cmd = "\\scriptsize"

    fulltab = []
    q_num = 0

    # Dropping later block questions
    # l <- which(is.na(pdat$b_info[qind]) & !(is.na(pdat$block_id[qind])))
    qind = [
        i for i in qind
        if not (pdat[i - 1]["b_info"] is None and pdat[i - 1]["block_id"] is not None)
    ]
    for i in qind:
        if q_num >= max_q:
            continue
        elif pdat[i - 1]["b_info"] is None:
            fulltab.extend(fq(pdat[i - 1]))
            q_num = q_num + 1
        else:
            # l <- which(pdat$block_id == pdat$block_id[i] & pdat$Topic == pdat$Topic[i])
            l = [
                j for j in range(1, len(pdat) + 1)
                if pdat[j - 1]["block_id"] is not None
                and pdat[j - 1]["block_id"] == pdat[i - 1]["block_id"]
                and pdat[j - 1]["Topic"] == pdat[i - 1]["Topic"]
            ]
            if q_num + len(l) <= max_q:
                fulltab.extend(fqb([pdat[j - 1] for j in l]))
                q_num = q_num + len(l)
            else:
                continue

    front = ""
    if frontPage:
        front = make_fm(tit, sem, classnum)

    if not real_exam:
        output = [
            "\\documentclass{examdesign} \n    \\usepackage[utf8]{inputenc}\n    \\usepackage{amsmath}\n    \\usepackage{amsfonts}\n    \\usepackage{amssymb}\n    \\usepackage{booktabs}\n    \\usepackage{graphicx}\n    \\usepackage{verbatim}\n    \\usepackage{lscape}\n    \\usepackage{multirow}\n    \\usepackage{ctable}\n    \\usepackage{rotating}\n    \\usepackage{natbib}\n    \\usepackage[nottoc]{tocbibind}\n    \\usepackage{setspace}\\singlespacing\n    ",
            layout_pkg,
            "\n    \\usepackage{longtable}\n    \\usepackage[center]{caption}\n    \\usepackage[pdftex,pdfstartview=FitH,pdfpagelabels]{hyperref}\n    \\usepackage{xcolor}\n    \\usepackage{enumitem}   \n\n    \\newcommand{\\del}{\\partial}\n    \\newcommand{\\noimplies}{\\centernot \\implies}\n    \\newcommand{\\bi}{\\begin{itemize}}\n    \\newcommand{\\ei}{\\end{itemize}}\n\n    \\makeatletter\n    \\renewcommand{\\exam@DefaultChoice}[2][]{%\n    \t\\ifchoice \\relax\n    \t\\else \\@mcstartlist \\choicetrue\n    \t\\fi\n    \t\\ifanswer\n    \t\\if#1!%\n    \t\\ifbox \\vspace{-\\fboxsep}\\item[\\hfill\\fbox{\\Alph{choice})}\\hfill] #2\n    \t\\vspace{-\\fboxsep}%\n    \t\\else\n    \t\\item[\\hfill\\MCfont{\\Alph{choice})}\\hfill] \\MCfont{#2}%\n    \t\\fi\n    \t\\else \\item[\\hfill\\Alph{choice})\\hfill] #2\n    \t\\fi\n    \t\\stepcounter{choice}%\n    \t\\else\n    \t\\item[\\hfill\\Alph{choice})\\hfill] #2\n    \t\\stepcounter{choice}%\n    \t\\fi}\n    \\makeatother\n\n    \\makeatletter\n    \\renewcommand\\@endquestionhook{\\vspace{1cm}}\n    \\makeatother\n\n    \\begin{document} \n    \\NumberOfVersions{",
            str(numVer),
            "}\n    \\ContinuousNumbering\n    \\setrandomseed{42}",
            front,
            "\\begin{center}\\textbf{This practice exam is the intellectual property of Dr. Cameron Ellis and Dr. Meghan Esson, and is intended only for use by students of FIN 3400 at the University of Iowa.}\\par\n\n    \\textcopyright 2025, Cameron Ellis and Meghan Esson. All rights reserved. \n    This practice exam is intended solely for use by students enrolled in FIN 3400 at the University of Iowa. \n    Any reproduction, redistribution, or other use -- online or otherwise -- without explicit written permission is strictly prohibited.\n\n    \\end{center}",
            "\\begin{examtop}",
            "\\noindent Name: $\\rule{6cm}{.15mm}$\\\\ \\\\" if not frontPage else "",
            "\\end{examtop}\n    \t\n    \t\\begin{multiplechoice}[title = {\\begin{center}",
            tit,
            "\\\\",
            sem,
            "\\end{center}\n    \t\tMark the best answer(s) on your scantron. Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; \n    mark all that apply. You receive partial credit for each correct answer that you mark AS LONG AS YOU DON'T MARK ANY INCORRECT ANSWERS. IF YOU MARK ANY INCORRECT ANSWERS, YOU WILL NOT RECEIVE ANY CREDIT FOR THE QUESTION. \\textbf{I don't bold things for no reason.}}, rearrange = {yes}, suppressprefix={yes}] ",
            size_cmd,
        ] + fulltab + [
            "\\end{multiplechoice}\n    \\end{document}",
            # The R source passes `file = file` INSIDE the c(...) call, so the
            # output path string becomes the final element of the document
            # (after \end{document}, where TeX ignores it). Replicated as-is.
            file,
        ]

        tex = " ".join(output)
        with open(file, "w", encoding="utf-8") as f:
            f.write(tex)
        return tex

    if real_exam:
        output = [
            "\\documentclass{examdesign} \n  \\usepackage[utf8]{inputenc}\n  \\usepackage{amsmath}\n  \\usepackage{amsfonts}\n  \\usepackage{amssymb}\n  \\usepackage{booktabs}\n  \\usepackage{graphicx}\n  \\usepackage{verbatim}\n  \\usepackage{lscape}\n  \\usepackage{multirow}\n  \\usepackage{ctable}\n  \\usepackage{rotating}\n  \\usepackage{natbib}\n  \\usepackage[nottoc]{tocbibind}\n  \\usepackage{setspace}\\singlespacing\n  ",
            layout_pkg,
            "\n  \\usepackage{longtable}\n  \\usepackage[center]{caption}\n  \\usepackage[pdftex,pdfstartview=FitH,pdfpagelabels]{hyperref}\n  \\usepackage{xcolor}\n  \\usepackage{enumitem}   \n\n  \\newcommand{\\del}{\\partial}\n  \\newcommand{\\noimplies}{\\centernot \\implies}\n  \\newcommand{\\bi}{\\begin{itemize}}\n  \\newcommand{\\ei}{\\end{itemize}}\n\n  \\makeatletter\n  \\renewcommand{\\exam@DefaultChoice}[2][]{%\n  \t\\ifchoice \\relax\n  \t\\else \\@mcstartlist \\choicetrue\n  \t\\fi\n  \t\\ifanswer\n  \t\\if#1!%\n  \t\\ifbox \\vspace{-\\fboxsep}\\item[\\hfill\\fbox{\\Alph{choice})}\\hfill] #2\n  \t\\vspace{-\\fboxsep}%\n  \t\\else\n  \t\\item[\\hfill\\MCfont{\\Alph{choice})}\\hfill] \\MCfont{#2}%\n  \t\\fi\n  \t\\else \\item[\\hfill\\Alph{choice})\\hfill] #2\n  \t\\fi\n  \t\\stepcounter{choice}%\n  \t\\else\n  \t\\item[\\hfill\\Alph{choice})\\hfill] #2\n  \t\\stepcounter{choice}%\n  \t\\fi}\n  \\makeatother\n\n  \\makeatletter\n  \\renewcommand\\@endquestionhook{\\vspace{1cm}}\n  \\makeatother\n\n  \\begin{document} \n  \\NumberOfVersions{",
            str(numVer),
            "}\n  \\ContinuousNumbering\n  \\setrandomseed{42}",
            front,
            "\\begin{center}\\textbf{This exam is the intellectual property of Dr. Cameron Ellis and Dr. Meghan Esson, and is intended only for use by students of FIN 3400 at the University of Iowa.}\\par\n\n  \\textcopyright 2025, Cameron Ellis and Meghan Esson. All rights reserved. \n  This exam is intended solely for use by students enrolled in FIN 3400 at the University of Iowa. Any reproduction, redistribution, or other use -- online or otherwise -- without explicit written permission is strictly prohibited.\n\n  \\end{center}",
            "\\begin{examtop}",
            "\\noindent Name: $\\rule{6cm}{.15mm}$\\\\ \\\\" if not frontPage else "",
            "\\end{examtop}\n  \t\n  \t\\begin{multiplechoice}[title = {\\begin{center}",
            tit,
            "\\\\",
            sem,
            "\\end{center}\n  \t\tMark the best answer(s) on your scantron. Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; \n  mark all that apply. You receive partial credit for each correct answer that you mark AS LONG AS YOU DON'T MARK ANY INCORRECT ANSWERS. IF YOU MARK ANY INCORRECT ANSWERS, YOU WILL NOT RECEIVE ANY CREDIT FOR THE QUESTION. \\textbf{I don't bold things for no reason.}}, rearrange = {yes}, suppressprefix={yes}] ",
            size_cmd,
        ] + fulltab + [
            "\\end{multiplechoice}\n  \\end{document}",
            # Same `file = file` inside c(...) as the practice branch.
            file,
        ]

        tex = " ".join(output)
        with open(file, "w", encoding="utf-8") as f:
            f.write(tex)
        return tex
