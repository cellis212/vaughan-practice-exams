"""Split a compiled examdesign PDF into per-version exam and answer-key
files, zipped for download.

The examdesign class lays the document out as, for each version V:
front-matter page(s) + exam pages, then front-matter page(s) again + the
"Answer Key for Exam V" pages. Front-matter pages are identified by their
text (the make_fm() content: INSTRUCTIONS, Class Time, and the version
letter); each one starts a new section. A section containing an
"Answer Key for Exam V" heading is that version's key; otherwise it is the
exam itself. Page 1 always starts the first section (version A's front
matter shares its page with the intellectual-property block on the intro
engine, so its text is mixed with other content).
"""

import io
import re
import zipfile

from pypdf import PdfReader, PdfWriter

# PDF text extraction can inject spurious spaces inside words at kerning
# boundaries (e.g. "V ersion A"), so the letter patterns tolerate them.
VERSION_RE = re.compile(r"V\s*e\s*r\s*s\s*i\s*o\s*n\s*([A-Z])\b")
KEY_RE = re.compile(r"A\s*n\s*s\s*w\s*e\s*r\s*K\s*e\s*y\s*f\s*o\s*r\s*E\s*x\s*a\s*m\s*([A-Z])")
INSTRUCTIONS_RE = re.compile(r"INSTRUCTIONS")
CLASS_TIME_RE = re.compile(r"Class\s*Time")


def _is_front_matter(text):
    return (INSTRUCTIONS_RE.search(text) and CLASS_TIME_RE.search(text)
            and VERSION_RE.search(text))


def split_exam_pdf(pdf_bytes):
    """Return zip-file bytes containing Exam_Version_X.pdf and
    Answer_Key_Version_X.pdf files covering every page of the input.
    Raises ValueError when no section boundaries can be detected."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    n = len(reader.pages)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")

    starts = [i for i, t in enumerate(texts) if _is_front_matter(t)]
    if 0 not in starts:
        starts.insert(0, 0)

    if len(starts) == 1:
        # No front-matter markers beyond page 1 (e.g. a document generated
        # without a front page): split at the answer-key headings instead.
        for i, t in enumerate(texts):
            if i != 0 and KEY_RE.search(t[:400]):
                starts.append(i)
        starts = sorted(set(starts))

    if len(starts) == 1 and n > 1:
        raise ValueError(
            "Could not detect version/answer-key boundaries in the compiled "
            "PDF; download it without the separate-files option instead."
        )

    sections = []
    for si, s in enumerate(starts):
        e = starts[si + 1] - 1 if si + 1 < len(starts) else n - 1
        # The key heading sits on the first page after the section's front
        # matter; look only at the top of the section so question text can
        # never masquerade as a heading.
        head = "\n".join(t[:400] for t in texts[s:min(s + 2, e + 1)])
        key_match = KEY_RE.search(head)
        if key_match:
            name = "Answer_Key_Version_" + key_match.group(1)
        else:
            version_match = VERSION_RE.search(texts[s])
            letter = version_match.group(1) if version_match else "A"
            name = "Exam_Version_" + letter
        sections.append((name, s, e))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, s, e in sections:
            writer = PdfWriter()
            for i in range(s, e + 1):
                writer.add_page(reader.pages[i])
            out = io.BytesIO()
            writer.write(out)
            z.writestr(name + ".pdf", out.getvalue())
    return buf.getvalue()
