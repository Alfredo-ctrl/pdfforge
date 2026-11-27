"""Join two PDFs and stamp the result. Run from the project root: python examples/merge_example.py"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdfforge import apply_ops, create_pdf, describe, merge  # noqa: E402

OUT = tempfile.mkdtemp(prefix="pdfforge-example-")
a = os.path.join(OUT, "a.pdf")
b = os.path.join(OUT, "b.pdf")
create_pdf({"title": "First", "sections": [{"heading": "One", "paragraphs": ["First file."]}]}, a)
create_pdf({"title": "Second", "sections": [{"heading": "Two", "paragraphs": ["Second file."]}]}, b)

joined = os.path.join(OUT, "joined.pdf")
print(merge([a, b], joined))
print(apply_ops(joined, os.path.join(OUT, "joined-draft.pdf"), [{"op": "watermark", "text": "DRAFT"}]))
print(describe(os.path.join(OUT, "joined-draft.pdf")))
print("pdfs in", OUT)
