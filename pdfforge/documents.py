"""Read and describe PDFs, join and split them, and build new ones."""

import os

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _open_pdf(path, caller):
    """Validate *path* exists and is a .pdf, then return a PdfReader."""
    if not os.path.exists(path):
        raise ValueError(f"no such file: '{path}'")
    if os.path.splitext(path)[1].lower() != ".pdf":
        raise ValueError(f"{caller} only reads .pdf files")
    return PdfReader(path)


def describe(path):
    reader = _open_pdf(path, "describe")
    info = {"format": "pdf", "encrypted": reader.is_encrypted, "size": os.path.getsize(path)}
    if reader.is_encrypted:
        info["pages"] = None
        info["title"] = None
        info["author"] = None
        return info
    info["pages"] = len(reader.pages)
    meta = reader.metadata
    info["title"] = meta.title if meta else None
    info["author"] = meta.author if meta else None
    return info


def extract_text(path, pages=None):
    reader = _open_pdf(path, "extract_text")
    if reader.is_encrypted:
        raise ValueError("this pdf is encrypted, decrypt it first")
    if pages:
        if not all(isinstance(p, int) and 1 <= p <= len(reader.pages) for p in pages):
            raise ValueError(f"pages has to be page numbers from 1 to {len(reader.pages)}")
    wanted = set(pages) if pages else None
    texts = []
    for i, page in enumerate(reader.pages, start=1):
        if wanted is None or i in wanted:
            texts.append(page.extract_text() or "")
    return {"format": "pdf", "pages": texts, "text": "\n".join(texts)}


def merge(inputs, output):
    if not isinstance(inputs, list) or len(inputs) < 2:
        raise ValueError("merge needs at least 2 input pdfs, e.g. [\"a.pdf\", \"b.pdf\"]")
    writer = PdfWriter()
    for path in inputs:
        if os.path.splitext(path)[1].lower() != ".pdf":
            raise ValueError(f"merge only takes .pdf files, got '{path}'")
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError(f"'{path}' is encrypted")
        writer.append(reader)
    with open(output, "wb") as f:
        writer.write(f)
    out = {"output": output}
    out.update(describe(output))
    return out


def split(input_path, output_dir, every=1):
    if not isinstance(every, int) or every < 1:
        raise ValueError("'every' has to be a whole number from 1 up")
    if os.path.splitext(input_path)[1].lower() != ".pdf":
        raise ValueError("split only takes .pdf files")
    reader = PdfReader(input_path)
    if reader.is_encrypted:
        raise ValueError("this pdf is encrypted, decrypt it first")
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    outputs = []
    for start in range(0, len(reader.pages), every):
        writer = PdfWriter()
        for page in reader.pages[start:start + every]:
            writer.add_page(page)
        out = os.path.join(output_dir, f"{base}-{start // every + 1:03d}.pdf")
        with open(out, "wb") as f:
            writer.write(f)
        outputs.append(out)
    return {"output_dir": output_dir, "outputs": outputs, "parts": len(outputs)}


def create_pdf(structure, output):
    if not isinstance(structure, dict):
        raise ValueError("structure has to be a dict, e.g. {\"title\": \"Report\", \"sections\": [...]}")

    styles = getSampleStyleSheet()
    title = structure.get("title", "")
    author = structure.get("author")
    story = []
    if title:
        story.append(Paragraph(title, styles["Heading1"]))
    for section in structure.get("sections", []):
        if not isinstance(section, dict):
            raise ValueError("every section has to be a dict")
        if section.get("heading"):
            story.append(Paragraph(section["heading"], styles["Heading2"]))
        for para in section.get("paragraphs", []):
            story.append(Paragraph(para, styles["Normal"]))
        story.append(Spacer(1, 6))
    if not story:
        raise ValueError("structure needs a title or at least one section")
    doc = SimpleDocTemplate(output, pagesize=A4, title=title, author=author or "")
    doc.build(story)
    out = {"output": output}
    out.update(describe(output))
    return out
