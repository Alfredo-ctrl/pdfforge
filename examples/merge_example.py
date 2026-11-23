"""Join two PDFs and stamp the result. Run from the project root."""

from pdfforge import apply_ops, describe, merge

print(merge(["a.pdf", "b.pdf"], "joined.pdf"))
print(apply_ops("joined.pdf", "joined-draft.pdf", [{"op": "watermark", "text": "DRAFT"}]))
print(describe("joined-draft.pdf"))
