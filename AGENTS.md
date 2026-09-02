# Practice Exam Websites

This repository publishes the practice exam generator at https://cellis212.github.io/vaughan-practice-exams/ through GitHub Pages.

## Standing approval from Cameron (2026-09-02)

When Cameron asks to fix a website issue or handle an issue report, complete these steps without separate confirmation:

- Make the required changes and run the relevant checks.
- Commit only the task changes and push them to `origin/main` to publish the fix.
- Verify the live website and PDF download. Use the existing `latex.ytotech.com` service for public practice-question content.
- Send a routine reply to the original reporter after the fix is live and verified.

Respect any narrower instruction Cameron gives for the current task. Never force-push or include unrelated changes.

## Verification

- Reproduce the reported failure before changing the source when possible.
- Preserve the questions, answer keys, and valid LaTeX notation unless the requested fix requires a change.
- Run the existing R/Python parity and parameter-engine tests for changes to the generator.
- For PDF failures, compile every question in the affected bank and inspect the affected PDF pages.
- Confirm the GitHub Pages deployment includes the new commit before reporting that the website is fixed.
