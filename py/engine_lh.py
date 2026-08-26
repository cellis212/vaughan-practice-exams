"""Python translation of create_exam() from the Life/Health (FIN 4430)
"Functions and Options.R" (Life Health Spring 2026 version).

Differences from the RMI Intro engine, mirroring the R sources exactly:
- A question is treated as standalone if b_info OR block_id is NA
  (intro checks only b_info).
- The preamble puts inputenc last (with a comment) and the layout package
  after it; the font-size command carries a trailing newline.
- There is no intellectual-property block in the document body.
- The output vector does not contain the stray `file = file` element.

String literals preserve the R source's exact whitespace and tabs.
Verified byte-for-byte by tests/parity_test.
"""

from exam_common import fq, fqb, make_fm


def create_exam(bank, qind, tit, sem, file, numVer=1, frontPage=False,
                max_q=9999, case=True, classnum="FIN 4430", real_exam=False,
                landscape=False):
    """bank: list of row dicts. qind: 1-based indices into bank (R-style).
    Returns the .tex content and writes it to `file`."""
    pdat = bank

    fulltab = []
    q_num = 0

    # Dropping later block questions
    qind = [
        i for i in qind
        if not (pdat[i - 1]["b_info"] is None and pdat[i - 1]["block_id"] is not None)
    ]
    for i in qind:
        if q_num >= max_q:
            continue
        elif pdat[i - 1]["b_info"] is None or pdat[i - 1]["block_id"] is None:
            fulltab.extend(fq(pdat[i - 1]))
            q_num = q_num + 1
        else:
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

    if landscape:
        layout_package = "\\usepackage[landscape,margin=1in]{geometry}"
    else:
        layout_package = "\\usepackage{fullpage}"

    if landscape:
        mc_font_size = "\\small\n"
    else:
        mc_font_size = "\\scriptsize\n"

    if not real_exam:
        output = [
            "\\documentclass{examdesign} \n    \\usepackage{amsmath}\n    \\usepackage{amsfonts}\n    \\usepackage{amssymb}\n    \\usepackage{booktabs}\n    \\usepackage{graphicx}\n    \\usepackage{verbatim}\n    \\usepackage{lscape}\n    \\usepackage{multirow}\n    \\usepackage{ctable}\n    \\usepackage{rotating}\n    \\usepackage{natbib}\n    \\usepackage[nottoc]{tocbibind}\n    \\usepackage{setspace}\\singlespacing\n    \\usepackage{longtable}\n    \\usepackage[center]{caption}\n    \\usepackage[pdftex,pdfstartview=FitH,pdfpagelabels]{hyperref}\n    \\usepackage{xcolor}\n    \\usepackage{enumitem}   \n    \\usepackage[utf8]{inputenc}   % allows you to type Unicode directly\n",
            layout_package,
            "\n\n\n\n    \\newcommand{\\del}{\\partial}\n    \\newcommand{\\noimplies}{\\centernot \\implies}\n    \\newcommand{\\bi}{\\begin{itemize}}\n    \\newcommand{\\ei}{\\end{itemize}}\n\n    \\makeatletter\n    \\renewcommand{\\exam@DefaultChoice}[2][]{%\n    \t\\ifchoice \\relax\n    \t\\else \\@mcstartlist \\choicetrue\n    \t\\fi\n    \t\\ifanswer\n    \t\\if#1!%\n    \t\\ifbox \\vspace{-\\fboxsep}\\item[\\hfill\\fbox{\\Alph{choice})}\\hfill] #2\n    \t\\vspace{-\\fboxsep}%\n    \t\\else\n    \t\\item[\\hfill\\MCfont{\\Alph{choice})}\\hfill] \\MCfont{#2}%\n    \t\\fi\n    \t\\else \\item[\\hfill\\Alph{choice})\\hfill] #2\n    \t\\fi\n    \t\\stepcounter{choice}%\n    \t\\else\n    \t\\item[\\hfill\\Alph{choice})\\hfill] #2\n    \t\\stepcounter{choice}%\n    \t\\fi}\n    \\makeatother\n\n    \\makeatletter\n    \\renewcommand\\@endquestionhook{\\vspace{1cm}}\n    \\makeatother\n\n    \\begin{document} \n    \\NumberOfVersions{",
            str(numVer),
            "}\n    \\ContinuousNumbering\n    \\setrandomseed{42}",
            front,
            "\\begin{examtop}",
            "\\noindent Name: $\\rule{6cm}{.15mm}$\\\\ \\\\" if not frontPage else "",
            "\\end{examtop}\n    \t\n    \t\\begin{multiplechoice}[title = {\\begin{center}",
            tit,
            "\\\\",
            sem,
            "\\end{center}\n    \t\tMark the best answer(s) on your scantron. Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; \n    mark all that apply. You receive partial credit for each correct answer that you mark AS LONG AS YOU DON'T MARK ANY INCORRECT ANSWERS. IF YOU MARK ANY INCORRECT ANSWERS, YOU WILL NOT RECEIVE ANY CREDIT FOR THE QUESTION. \\textbf{I don't bold things for no reason.}}, rearrange = {yes}, suppressprefix={yes}] ",
            mc_font_size,
        ] + fulltab + [
            "\\end{multiplechoice}\n    \\end{document}",
        ]

        tex = " ".join(output)
        with open(file, "w", encoding="utf-8") as f:
            f.write(tex)
        return tex

    if real_exam:
        output = [
            "\\documentclass{examdesign}\n  \\usepackage{amsmath}\n  \\usepackage{amsfonts}\n  \\usepackage{amssymb}\n  \\usepackage{booktabs}\n  \\usepackage{graphicx}\n  \\usepackage{verbatim}\n  \\usepackage{lscape}\n  \\usepackage{multirow}\n  \\usepackage{ctable}\n  \\usepackage{rotating}\n  \\usepackage{natbib}\n  \\usepackage[nottoc]{tocbibind}\n  \\usepackage{setspace}\\singlespacing\n  \\usepackage{longtable}\n  \\usepackage[center]{caption}\n  \\usepackage[pdftex,pdfstartview=FitH,pdfpagelabels]{hyperref}\n  \\usepackage{xcolor}\n  \\usepackage{enumitem}\n  \\usepackage[utf8]{inputenc}   % allows you to type Unicode directly\n",
            layout_package,
            "\n\n\n  \\newcommand{\\del}{\\partial}\n  \\newcommand{\\noimplies}{\\centernot \\implies}\n  \\newcommand{\\bi}{\\begin{itemize}}\n  \\newcommand{\\ei}{\\end{itemize}}\n\n  \\makeatletter\n  \\renewcommand{\\exam@DefaultChoice}[2][]{%\n  \t\\ifchoice \\relax\n  \t\\else \\@mcstartlist \\choicetrue\n  \t\\fi\n  \t\\ifanswer\n  \t\\if#1!%\n  \t\\ifbox \\vspace{-\\fboxsep}\\item[\\hfill\\fbox{\\Alph{choice})}\\hfill] #2\n  \t\\vspace{-\\fboxsep}%\n  \t\\else\n  \t\\item[\\hfill\\MCfont{\\Alph{choice})}\\hfill] \\MCfont{#2}%\n  \t\\fi\n  \t\\else \\item[\\hfill\\Alph{choice})\\hfill] #2\n  \t\\fi\n  \t\\stepcounter{choice}%\n  \t\\else\n  \t\\item[\\hfill\\Alph{choice})\\hfill] #2\n  \t\\stepcounter{choice}%\n  \t\\fi}\n  \\makeatother\n\n  \\makeatletter\n  \\renewcommand\\@endquestionhook{\\vspace{1cm}}\n  \\makeatother\n\n  \\begin{document} \n  \\NumberOfVersions{",
            str(numVer),
            "}\n  \\ContinuousNumbering\n  \\setrandomseed{42}",
            front,
            "\\begin{examtop}",
            "\\noindent Name: $\\rule{6cm}{.15mm}$\\\\ \\\\" if not frontPage else "",
            "\\end{examtop}\n  \t\n  \t\\begin{multiplechoice}[title = {\\begin{center}",
            tit,
            "\\\\",
            sem,
            "\\end{center}\n  \t\tMark the best answer(s) on your scantron. Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; \n  mark all that apply. You receive partial credit for each correct answer that you mark AS LONG AS YOU DON'T MARK ANY INCORRECT ANSWERS. IF YOU MARK ANY INCORRECT ANSWERS, YOU WILL NOT RECEIVE ANY CREDIT FOR THE QUESTION. \\textbf{I don't bold things for no reason.}}, rearrange = {yes}, suppressprefix={yes}] ",
            mc_font_size,
        ] + fulltab + [
            "\\end{multiplechoice}\n  \\end{document}",
        ]

        tex = " ".join(output)
        with open(file, "w", encoding="utf-8") as f:
            f.write(tex)
        return tex
