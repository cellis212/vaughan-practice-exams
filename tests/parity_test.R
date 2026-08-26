# Parity test (R side). Runs the ORIGINAL R engines from tests/reference/
# with sample() replaced by a deterministic rotation, over synthetic and
# real-bank scenarios, and writes the .tex outputs to tests/out_r/.
# tests/run_parity.sh diffs these against the Python port's outputs.
#
# Usage: Rscript parity_test.R <out_dir> <ref_dir> <intro_data_dir> <lh_data_dir>

args <- commandArgs(trailingOnly = TRUE)
out_dir <- args[1]
ref_dir <- args[2]
intro_data <- args[3]
lh_data <- args[4]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

suppressMessages({
  library(tidyverse)
  library(readxl)
})

# Deterministic replacement for sample(): a rotation instead of a shuffle.
# sample(n) -> c(2:n, 1); sample(x, size) -> x rotated. This exercises the
# correct-answer remapping in rc() while staying reproducible across languages.
rotate_sample <- function(x, size, replace = FALSE, prob = NULL) {
  n <- if (length(x) == 1 && is.numeric(x)) x else length(x)
  if (n <= 1) {
    if (length(x) == 1 && is.numeric(x)) return(1L) else return(x)
  }
  idx <- c(2:n, 1L)
  if (length(x) == 1 && is.numeric(x)) idx else x[idx]
}

load_engine <- function(src) {
  e <- new.env(parent = globalenv())
  source(src, local = e)
  e$sample <- rotate_sample
  e
}

synth_bank <- function() {
  tibble(
    Topic = rep("Synthetic Topic", 12),
    Text = paste0("Question stem number ", 1:12, " with some \\textbf{bold} text?"),
    a = paste0("Choice A for q", 1:12),
    b = paste0("Choice B for q", 1:12),
    c = paste0("Choice C for q", 1:12),
    d = c("Choice D for q1", "Choice D for q2", NA, "Choice D for q4",
          "Choice D for q5", "Choice D for q6", "Choice D for q7",
          "Choice D for q8", NA, "Choice D for q10", "Choice D for q11",
          "Choice D for q12"),
    extras = c("n", "y", "y", "y", "n", "y", "n", "y", "y", "y", "y", "n"),
    correct = c("c", "ab", "b", "none", "a", "acd", "d", "bd", "none",
                "a", "c", "b"),
    idea_id = NA_character_,
    block_id = c(NA, NA, NA, NA, NA, "B1", "B1", "B1", NA, "B2", "B2", NA),
    q_id = as.numeric(1:12),
    b_info = c(NA, NA, NA, NA, NA,
               "\\textbf{Questions in this block share the following scenario:} A firm faces a loss.",
               NA, NA, NA,
               "\\textbf{Block two context:} Consider an insurance contract.",
               NA, NA)
  )
}

qind_synth <- c(7, 3, 1, 6, 12, 2, 8, 10, 5, 11, 4, 9)

intro <- load_engine(file.path(ref_dir, "functions_and_options_intro.R"))
lh <- load_engine(file.path(ref_dir, "functions_and_options_lh.R"))

bank <- synth_bank()

intro$create_exam(bank = bank, qind = qind_synth, tit = "Practice Exam:",
                  sem = "Spring 2026", classnum = "FIN 3400", numVer = 1,
                  file = file.path(out_dir, "intro_practice_portrait.tex"),
                  frontPage = TRUE, max_q = 8, real_exam = FALSE,
                  landscape = FALSE)

intro$create_exam(bank = bank, qind = qind_synth, tit = "Practice Exam:",
                  sem = "Spring 2026", classnum = "FIN 3400", numVer = 1,
                  file = file.path(out_dir, "intro_practice_landscape.tex"),
                  frontPage = TRUE, max_q = 8, real_exam = FALSE,
                  landscape = TRUE)

intro$create_exam(bank = bank, qind = qind_synth, tit = "Cumulative Final Exam:",
                  sem = "Spring 2026", classnum = "FIN 3400", numVer = 3,
                  file = file.path(out_dir, "intro_real_portrait.tex"),
                  frontPage = TRUE, max_q = 8, real_exam = TRUE,
                  landscape = FALSE)

lh$create_exam(bank = bank, qind = qind_synth, tit = "Practice Exam:",
               sem = "Spring 2026", classnum = "FIN 4430", numVer = 1,
               file = file.path(out_dir, "lh_practice_portrait.tex"),
               frontPage = TRUE, max_q = 8, real_exam = FALSE,
               landscape = FALSE)

lh$create_exam(bank = bank, qind = qind_synth, tit = "Practice Exam:",
               sem = "Spring 2026", classnum = "FIN 4430", numVer = 1,
               file = file.path(out_dir, "lh_practice_landscape.tex"),
               frontPage = TRUE, max_q = 8, real_exam = FALSE,
               landscape = TRUE)

lh$create_exam(bank = bank, qind = qind_synth, tit = "Exam 3:",
               sem = "Spring 2026", classnum = "FIN 4430", numVer = 3,
               file = file.path(out_dir, "lh_real_portrait.tex"),
               frontPage = TRUE, max_q = 8, real_exam = TRUE,
               landscape = FALSE)

# LH-only edge: a row with b_info set but block_id NA is standalone under
# the LH condition (is.na(b_info) | is.na(block_id)).
bank_edge <- bank
bank_edge$b_info[4] <- "Stray context with no block id."
lh$create_exam(bank = bank_edge, qind = qind_synth, tit = "Practice Exam:",
               sem = "Spring 2026", classnum = "FIN 4430", numVer = 1,
               file = file.path(out_dir, "lh_practice_blocknaedge.tex"),
               frontPage = TRUE, max_q = 8, real_exam = FALSE,
               landscape = FALSE)

# Real-data scenarios: mirrors the purrr::map_df loading in app.R.
intro_banks <- list(
  list(path = file.path(intro_data, "Test Bank Topic 1.xlsx"), topic = "Topic 1"),
  list(path = file.path(intro_data, "Test Bank Module 1 Math.xlsx"), topic = "Math For Module 1")
)
full_intro <- purrr::map_df(intro_banks, function(bk) {
  readxl::read_xlsx(bk$path) %>% mutate(Topic = bk$topic)
})
intro$create_exam(bank = full_intro, qind = seq_len(nrow(full_intro)),
                  tit = "Practice Exam:", sem = "Spring 2026",
                  classnum = "FIN 3400", numVer = 1,
                  file = file.path(out_dir, "intro_realdata.tex"),
                  frontPage = TRUE, max_q = 30, real_exam = FALSE,
                  landscape = FALSE)

lh_banks <- list(
  list(path = file.path(lh_data, "Test Bank Module 3.xlsx"), topic = "Lecture"),
  list(path = file.path(lh_data, "Test Bank Reading - Annuity Puzzle.xlsx"), topic = "Annuity Puzzle")
)
full_lh <- purrr::map_df(lh_banks, function(bk) {
  readxl::read_xlsx(bk$path) %>% mutate(Topic = bk$topic)
})
lh$create_exam(bank = full_lh, qind = seq_len(nrow(full_lh)),
               tit = "Practice Exam:", sem = "Spring 2026",
               classnum = "FIN 4430", numVer = 1,
               file = file.path(out_dir, "lh_realdata.tex"),
               frontPage = TRUE, max_q = 25, real_exam = FALSE,
               landscape = FALSE)

cat("R parity outputs written to", out_dir, "\n")
