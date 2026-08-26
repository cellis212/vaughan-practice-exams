# nolint start: line_length_linter, trailing_whitespace_linter.



library(tidyverse)


# Function to randomize choices for a single question
rc <- function(dat)
{
  tdat <- dat
  
  # Collect options into a vector
  options <- as.character(dat[, c('a', 'b', 'c', 'd')])
  options <- options[!is.na(options)]  # Remove NA options
  num_options <- length(options)
  
  # Randomize options (excluding 'None of the above', which we'll add later)
  idx <- sample(num_options)
  options_shuffled <- options[idx]
  
  # Update options in tdat
  option_names <- c('a', 'b', 'c', 'd')[1:num_options]
  tdat[option_names] <- as.list(options_shuffled)
  
  # Update the correct answer(s)
  if (dat$correct == 'none') {
    # If 'None of the above' is correct
    tdat$correct <- 'none'
  } else {
    # Map the correct answers based on the shuffled indices
    poss <- option_names
    correct_letters <- unlist(strsplit(dat$correct, ""))
    correct_indices <- match(correct_letters, c('a', 'b', 'c', 'd')[1:num_options])
    
    # Find new positions of the correct answers after shuffling
    new_indices <- match(correct_indices, idx)
    new_correct_letters <- poss[new_indices]
    
    tdat$correct <- paste(sort(new_correct_letters), collapse = "")
  }
  
  return(tdat)
}


# Function to format a single question
fq <- function(dat)
{
  qtab <- c()
  dat <- rc(dat)
  
  # Determine if 'None of the above' should be added
  if (dat$extras == 'n') {
    num_options <- ifelse(is.na(dat$d), 4, 4)  # Do not add 'None of the above'
    # Add "(Exactly One Correct Answer)" in bold at the beginning of the question text
    dat$Text <- paste0("\\textbf{(Exactly One Correct Answer)} ", dat$Text)
  } else {
    num_options <- ifelse(is.na(dat$d), 4, 5)  # Include 'None of the above' as the last option
  }
  
  # Begin question
  qtab[1] <- paste0("\\begin{question}\n[", dat$Topic, "-", dat$q_id, "]")
  
  # Choices without 'combo' options
  choices <- list()
  choices[[1]] <- paste0("\n\\choice{", dat$a, "}\n")
  choices[[2]] <- paste0("\\choice{", dat$b, "}\n")
  choices[[3]] <- paste0("\\choice{", dat$c, "}\n")
  if (!is.na(dat$d)) {
    choices[[4]] <- paste0("\\choice{", dat$d, "}\n")
  }
  
  if (dat$extras != 'n') {
    # 'None of the above' as the last option
    choices[[num_options]] <- "\\choice{None of the above.}\n"
  }
  
  # Marking Correct Answer(s)
  correct_letters <- unlist(strsplit(dat$correct, ""))
  poss <- c("a", "b", "c", "d")
  
 if (dat$correct == "none" && dat$extras != 'n') {
    # If 'None of the above' is correct and 'extras' is not 'n'
    choices[[num_options]] <- sub("\\\\choice\\{", "\\\\choice[!]\\{", choices[[num_options]])
  } else {
    # For other correct answers
    for (i in seq_along(poss)) {
      if (poss[i] %in% correct_letters) {
        choices[[i]] <- sub("\\\\choice\\{", "\\\\choice[!]\\{", choices[[i]])
      }
    }
  }
  
  # End question
  qtab[length(qtab) + 1] <- "\\end{question}\n"
  
  # Combine question elements
  qtab <- c(qtab[1], dat$Text, choices, qtab[length(qtab)])
  
  return(qtab)
}


# Function to format block questions
fqb <- function(tdat)
{
  btab <- c()
  nq <- nrow(tdat)
  
  btab[1] <- paste0("\\begin{block}[questions=", nq, "]\n")
  btab[2] <- tdat$b_info[1]
  
  for (i in 1:nq) {
    dat <- rc(tdat[i, ])
    qtab <- c()
    
    # Determine if 'None of the above' should be added
    if (dat$extras == 'n') {
      num_options <- ifelse(is.na(dat$d), 4, 4)  # Do not add 'None of the above'
      # Add "(Exactly One Correct Answer)" in bold at the beginning of the question text
      dat$Text <- paste0("\\textbf{(Exactly One Correct Answer)} ", dat$Text)
    } else {
      num_options <- ifelse(is.na(dat$d), 4, 5)  # Include 'None of the above' as the last option
    }
    
    # Begin question
    qtab[1] <- paste0("\\begin{question}\n[", dat$Topic, "-", dat$q_id, "]")
    
    # Choices without 'combo' options
    choices <- list()
    choices[[1]] <- paste0("\n\\choice{", dat$a, "}\n")
    choices[[2]] <- paste0("\\choice{", dat$b, "}\n")
    choices[[3]] <- paste0("\\choice{", dat$c, "}\n")
    if (!is.na(dat$d)) {
      choices[[4]] <- paste0("\\choice{", dat$d, "}\n")
    }
    
    if (dat$extras != 'n') {
      # 'None of the above' as the last option
      choices[[num_options]] <- "\\choice{None of the above.}\n"
    }
    
    # Marking Correct Answer(s)
    correct_letters <- unlist(strsplit(dat$correct, ""))
    poss <- c("a", "b", "c", "d")
    
    if(dat$correct == "none" && dat$extras != 'n') {
      # If 'None of the above' is correct and 'extras' is not 'n'
      choices[[num_options]] <- sub("\\\\choice\\{", "\\\\choice[!]\\{", choices[[num_options]])
    } else {
      # For other correct answers
      for (j in seq_along(poss)) {
        if (poss[j] %in% correct_letters) {
          choices[[j]] <- sub("\\\\choice\\{", "\\\\choice[!]\\{", choices[[j]])
        }
      }
    }
    
    # End question
    qtab[length(qtab) + 1] <- "\\end{question}\n"
    
    # Combine question elements
    qtab <- c(qtab[1], dat$Text, choices, qtab[length(qtab)])
    btab <- c(btab, qtab)
  }
  
  btab[length(btab) + 1] <- "\\end{block}\n"
  
  return(btab)
}



# Function to create and output an exam
create_exam <- function(bank, qind, tit, sem, file, numVer = 1, frontPage = F, max_q = 9999, case = TRUE, classnum, real_exam = F, landscape = FALSE)
{
  pdat <- bank
  layout_pkg <- if (landscape) {
    "\n    \\usepackage[landscape,margin=1in]{geometry}"
  } else {
    "\n    \\usepackage{fullpage}"
  }
  size_cmd <- if (landscape) {
    "\\small"
  } else {
    "\\scriptsize"
  }
  
  fulltab <- c()
  q_num <- 0
  
  # Dropping later block questions
  l <- which(is.na(pdat$b_info[qind]) & !(is.na(pdat$block_id[qind])))
  if(length(l) > 0){
    qind <- qind[-l]
  }
  for(i in qind){
    if(q_num >= max_q){
      next()
    } else if(is.na(pdat$b_info[i])){
      fulltab <- c(fulltab, fq(pdat[i,]))
      q_num <- q_num + 1
    } else {
      l <- which(pdat$block_id == pdat$block_id[i] & pdat$Topic == pdat$Topic[i])
      if(q_num + length(l) <= max_q){
        fulltab <- c(fulltab, fqb(pdat[l,]))
        q_num <- q_num + length(l)
      } else {
        next()
      }
    }
  }
  
  front <- ""
  if(frontPage == T){
    front <- make_fm(tit, sem, classnum)
  }
  
  if(real_exam == F){
    # Combine all elements into a single character vector
    output <- c(
     "\\documentclass{examdesign} 
    \\usepackage[utf8]{inputenc}
    \\usepackage{amsmath}
    \\usepackage{amsfonts}
    \\usepackage{amssymb}
    \\usepackage{booktabs}
    \\usepackage{graphicx}
    \\usepackage{verbatim}
    \\usepackage{lscape}
    \\usepackage{multirow}
    \\usepackage{ctable}
    \\usepackage{rotating}
    \\usepackage{natbib}
    \\usepackage[nottoc]{tocbibind}
    \\usepackage{setspace}\\singlespacing
    ", layout_pkg, "
    \\usepackage{longtable}
    \\usepackage[center]{caption}
    \\usepackage[pdftex,pdfstartview=FitH,pdfpagelabels]{hyperref}
    \\usepackage{xcolor}
    \\usepackage{enumitem}   

    \\newcommand{\\del}{\\partial}
    \\newcommand{\\noimplies}{\\centernot \\implies}
    \\newcommand{\\bi}{\\begin{itemize}}
    \\newcommand{\\ei}{\\end{itemize}}

    \\makeatletter
    \\renewcommand{\\exam@DefaultChoice}[2][]{%
    \t\\ifchoice \\relax
    \t\\else \\@mcstartlist \\choicetrue
    \t\\fi
    \t\\ifanswer
    \t\\if#1!%
    \t\\ifbox \\vspace{-\\fboxsep}\\item[\\hfill\\fbox{\\Alph{choice})}\\hfill] #2
    \t\\vspace{-\\fboxsep}%
    \t\\else
    \t\\item[\\hfill\\MCfont{\\Alph{choice})}\\hfill] \\MCfont{#2}%
    \t\\fi
    \t\\else \\item[\\hfill\\Alph{choice})\\hfill] #2
    \t\\fi
    \t\\stepcounter{choice}%
    \t\\else
    \t\\item[\\hfill\\Alph{choice})\\hfill] #2
    \t\\stepcounter{choice}%
    \t\\fi}
    \\makeatother

    \\makeatletter
    \\renewcommand\\@endquestionhook{\\vspace{1cm}}
    \\makeatother

    \\begin{document} 
    \\NumberOfVersions{", numVer, "}
    \\ContinuousNumbering
    \\setrandomseed{42}",
        front,
        "\\begin{center}\\textbf{This practice exam is the intellectual property of Dr. Cameron Ellis and Dr. Meghan Esson, and is intended only for use by students of FIN 3400 at the University of Iowa.}\\par

    \\textcopyright 2025, Cameron Ellis and Meghan Esson. All rights reserved. 
    This practice exam is intended solely for use by students enrolled in FIN 3400 at the University of Iowa. 
    Any reproduction, redistribution, or other use -- online or otherwise -- without explicit written permission is strictly prohibited.

    \\end{center}",
        "\\begin{examtop}", if(frontPage == F){
          "\\noindent Name: $\\rule{6cm}{.15mm}$\\\\ \\\\"
        } else {
          ""
        }, 
        "\\end{examtop}
    \t
    \t\\begin{multiplechoice}[title = {\\begin{center}",
        tit,"\\\\",sem, "\\end{center}
    \t\tMark the best answer(s) on your scantron. Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; 
    mark all that apply. You receive partial credit for each correct answer that you mark AS LONG AS YOU DON'T MARK ANY INCORRECT ANSWERS. IF YOU MARK ANY INCORRECT ANSWERS, YOU WILL NOT RECEIVE ANY CREDIT FOR THE QUESTION. \\textbf{I don't bold things for no reason.}}, rearrange = {yes}, suppressprefix={yes}] ",
        size_cmd,
        fulltab, 
        "\\end{multiplechoice}
    \\end{document}", 
        file = file
      )
      
      cat(paste(output, collapse = " "), file = file)
  }


if(real_exam == T) {
    output <- c(
      "\\documentclass{examdesign} 
  \\usepackage[utf8]{inputenc}
  \\usepackage{amsmath}
  \\usepackage{amsfonts}
  \\usepackage{amssymb}
  \\usepackage{booktabs}
  \\usepackage{graphicx}
  \\usepackage{verbatim}
  \\usepackage{lscape}
  \\usepackage{multirow}
  \\usepackage{ctable}
  \\usepackage{rotating}
  \\usepackage{natbib}
  \\usepackage[nottoc]{tocbibind}
  \\usepackage{setspace}\\singlespacing
  ", layout_pkg, "
  \\usepackage{longtable}
  \\usepackage[center]{caption}
  \\usepackage[pdftex,pdfstartview=FitH,pdfpagelabels]{hyperref}
  \\usepackage{xcolor}
  \\usepackage{enumitem}   

  \\newcommand{\\del}{\\partial}
  \\newcommand{\\noimplies}{\\centernot \\implies}
  \\newcommand{\\bi}{\\begin{itemize}}
  \\newcommand{\\ei}{\\end{itemize}}

  \\makeatletter
  \\renewcommand{\\exam@DefaultChoice}[2][]{%
  \t\\ifchoice \\relax
  \t\\else \\@mcstartlist \\choicetrue
  \t\\fi
  \t\\ifanswer
  \t\\if#1!%
  \t\\ifbox \\vspace{-\\fboxsep}\\item[\\hfill\\fbox{\\Alph{choice})}\\hfill] #2
  \t\\vspace{-\\fboxsep}%
  \t\\else
  \t\\item[\\hfill\\MCfont{\\Alph{choice})}\\hfill] \\MCfont{#2}%
  \t\\fi
  \t\\else \\item[\\hfill\\Alph{choice})\\hfill] #2
  \t\\fi
  \t\\stepcounter{choice}%
  \t\\else
  \t\\item[\\hfill\\Alph{choice})\\hfill] #2
  \t\\stepcounter{choice}%
  \t\\fi}
  \\makeatother

  \\makeatletter
  \\renewcommand\\@endquestionhook{\\vspace{1cm}}
  \\makeatother

  \\begin{document} 
  \\NumberOfVersions{", numVer, "}
  \\ContinuousNumbering
  \\setrandomseed{42}",
      front,
      "\\begin{center}\\textbf{This exam is the intellectual property of Dr. Cameron Ellis and Dr. Meghan Esson, and is intended only for use by students of FIN 3400 at the University of Iowa.}\\par

  \\textcopyright 2025, Cameron Ellis and Meghan Esson. All rights reserved. 
  This exam is intended solely for use by students enrolled in FIN 3400 at the University of Iowa. Any reproduction, redistribution, or other use -- online or otherwise -- without explicit written permission is strictly prohibited.

  \\end{center}",
      "\\begin{examtop}", if(frontPage == F){
        "\\noindent Name: $\\rule{6cm}{.15mm}$\\\\ \\\\"
      } else {
        ""
      }, 
      "\\end{examtop}
  \t
  \t\\begin{multiplechoice}[title = {\\begin{center}",
      tit,"\\\\",sem, "\\end{center}
  \t\tMark the best answer(s) on your scantron. Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; 
  mark all that apply. You receive partial credit for each correct answer that you mark AS LONG AS YOU DON'T MARK ANY INCORRECT ANSWERS. IF YOU MARK ANY INCORRECT ANSWERS, YOU WILL NOT RECEIVE ANY CREDIT FOR THE QUESTION. \\textbf{I don't bold things for no reason.}}, rearrange = {yes}, suppressprefix={yes}] ",
      size_cmd,
      fulltab, 
      "\\end{multiplechoice}
  \\end{document}", 
      file = file
    )
    
    cat(paste(output, collapse = " "), file = file)
  }
} 
# 
# fqb(pdat[12:15,]) %>% cat
# 
make_fm <- function(tit, sem, classnum = "FIN 3400")
{
  # Create the front matter for the exam with customizable class number
  front <- paste0(
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
    "\\item Questions marked ``\\textbf{(Exactly One Correct Answer)}'' will have exactly one choice as the correct answer.  Other questions \\textbf{may have one or more} correct answers; 
mark all that apply. ",
    "\\bi ",
    "\\item For example, if the correct answers are $a$, $b$, and $c$, then you should bubble in $a$, $b$, and $c$ on the scantron.",
    "\\ei",
    " \\item If I perceive that you are cheating, you will receive an F for the course.  Keep your eyes on your own paper. Note that you are being filmed.",
    " \\item Your cell phone is not allowed on your desk.",
    " \\item All caps, hats, and hoods must be removed.",
    " \\item No headphones allowed.",
    "\\ei",
    "}}",
    " \\end{frontmatter} "
  )
  
  return(front)
}


# nolint end