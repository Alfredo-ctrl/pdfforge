"""PDF ops, one OPS entry each."""

import io
import os

from pypdf import PdfReader, PdfWriter

from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from .documents import describe


class _EditSession:
    """The working PDF: a page list plus writer-level settings."""

    def __init__(self, writer):
        self.pages = list(writer.pages)
        self.metadata = {}
        self.password = None
        self.owner_password = None
        self.compress = False


def _parse_page_indices(op, params, total, key="pages"):
    pages = params.get(key)
    if pages is None:
        return list(range(total))
    if not isinstance(pages, list) or not pages or not all(isinstance(p, int) for p in pages):
        raise ValueError(f"'{op}': '{key}' has to be a list of page numbers, e.g. [1, 3]")
    if any(p < 1 or p > total for p in pages):
        raise ValueError(f"'{op}': page numbers go from 1 to {total}")
    return [p - 1 for p in pages]


def _require_int(op, params, key, default=None, lo=None, hi=None):
    v = params.get(key, default)
    if v is None:
        raise ValueError(f"'{op}' needs '{key}'")
    if not isinstance(v, int) or isinstance(v, bool):
        raise ValueError(f"'{op}': '{key}' has to be a whole number")
    if lo is not None and v < lo:
        raise ValueError(f"'{op}': '{key}' can't be under {lo}")
    if hi is not None and v > hi:
        raise ValueError(f"'{op}': '{key}' can't be over {hi}")
    return v


def _require_str(op, params, key, default=None):
    v = params.get(key, default)
    if v is None:
        raise ValueError(f"'{op}' needs '{key}'")
    if not isinstance(v, str):
        raise ValueError(f"'{op}': '{key}' has to be text")
    return v


def _extract_pages(job, p):
    keep = _parse_page_indices("extract_pages", p, len(job.pages))
    job.pages = [job.pages[i] for i in keep]


def _remove_pages(job, p):
    drop = set(_parse_page_indices("remove_pages", p, len(job.pages)))
    job.pages = [page for i, page in enumerate(job.pages) if i not in drop]
    if not job.pages:
        raise ValueError("'remove_pages': can't drop every page")


def _rotate(job, p):
    angle = _require_int("rotate", p, "angle", 90)
    if angle not in (90, 180, 270):
        raise ValueError("'rotate': angle has to be 90, 180 or 270")
    for i in _parse_page_indices("rotate", p, len(job.pages)):
        job.pages[i].rotate(angle)


def _stamp_page(width, height, draw):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(float(width), float(height)))
    draw(c, float(width), float(height))
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def _watermark_draw(text, opacity, angle, fontsize):
    def draw(c, width, height):
        c.saveState()
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
        c.setFont("Helvetica-Bold", fontsize)
        c.translate(width / 2, height / 2)
        c.rotate(angle)
        c.drawCentredString(0, 0, text)
        c.restoreState()

    return draw


def _watermark(job, p):
    text = _require_str("watermark", p, "text")
    opacity = p.get("opacity", 0.15)
    if not isinstance(opacity, (int, float)) or isinstance(opacity, bool) or not 0 < opacity <= 1:
        raise ValueError("'watermark': 'opacity' has to be between 0 and 1")
    angle = _require_int("watermark", p, "angle", 45, lo=-90, hi=90)
    fontsize = _require_int("watermark", p, "fontsize", 48, lo=8, hi=200)
    cache = {}
    for i in _parse_page_indices("watermark", p, len(job.pages)):
        page = job.pages[i]
        key = (float(page.mediabox.width), float(page.mediabox.height))
        if key not in cache:
            cache[key] = _stamp_page(key[0], key[1], _watermark_draw(text, opacity, angle, fontsize))
        page.merge_page(cache[key])


def _set_metadata(job, p):
    title = p.get("title")
    author = p.get("author")
    if title is None and author is None:
        raise ValueError("'set_metadata' needs 'title' or 'author'")
    if title is not None:
        job.metadata["/Title"] = str(title)
    if author is not None:
        job.metadata["/Author"] = str(author)


def _encrypt(job, p):
    job.password = _require_str("encrypt", p, "password")
    owner = p.get("owner_password")
    if owner is not None:
        job.owner_password = str(owner)


def _compress(job, p):
    # drop embedded images and dedupe identical objects
    job.compress = True


def _page_number_draw(text, fontsize):
    def draw(c, width, height):
        c.saveState()
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", fontsize)
        c.drawCentredString(width / 2, 24, text)
        c.restoreState()

    return draw


def _page_numbers(job, p):
    fmt = p.get("format", "Page {n} of {total}")
    if not isinstance(fmt, str) or "{n}" not in fmt or "{total}" not in fmt:
        raise ValueError("'page_numbers': 'format' needs {n} and {total}, e.g. 'Page {n} of {total}'")
    fontsize = _require_int("page_numbers", p, "fontsize", 10, lo=6, hi=48)
    total = len(job.pages)
    cache = {}
    for i in _parse_page_indices("page_numbers", p, total):
        page = job.pages[i]
        key = (float(page.mediabox.width), float(page.mediabox.height), i + 1)
        if key not in cache:
            cache[key] = _stamp_page(key[0], key[1], _page_number_draw(fmt.format(n=i + 1, total=total), fontsize))
        page.merge_page(cache[key])


OPS = {
    "extract_pages": {
        "description": "Keep only the listed pages (1-based), in that order.",
        "params": {
            "pages": {"type": "array", "items": {"type": "integer"}},
        },
        "run": _extract_pages,
    },
    "remove_pages": {
        "description": "Drop the listed pages (1-based).",
        "params": {
            "pages": {"type": "array", "items": {"type": "integer"}},
        },
        "run": _remove_pages,
    },
    "rotate": {
        "description": "Rotate pages 90, 180 or 270 degrees. All pages unless 'pages' is given.",
        "params": {
            "angle": {"type": "integer", "enum": [90, 180, 270], "default": 90},
            "pages": {"type": "array", "items": {"type": "integer"}},
        },
        "run": _rotate,
    },
    "watermark": {
        "description": "Stamp text diagonally on every page (or the listed ones).",
        "params": {
            "text": {"type": "string"},
            "opacity": {"type": "number", "default": 0.15, "min": 0, "max": 1},
            "angle": {"type": "integer", "default": 45, "min": -90, "max": 90},
            "fontsize": {"type": "integer", "default": 48, "min": 8, "max": 200},
            "pages": {"type": "array", "items": {"type": "integer"}},
        },
        "run": _watermark,
    },
    "set_metadata": {
        "description": "Set the PDF title and/or author.",
        "params": {
            "title": {"type": "string"},
            "author": {"type": "string"},
        },
        "run": _set_metadata,
    },
    "encrypt": {
        "description": "Lock the PDF with a password.",
        "params": {
            "password": {"type": "string"},
            "owner_password": {"type": "string"},
        },
        "run": _encrypt,
    },
    "compress": {
        "description": "Smaller file: drop embedded images and dedupe identical objects.",
        "params": {},
        "run": _compress,
    },
    "page_numbers": {
        "description": "Stamp 'Page N of M' at the bottom of every page (or the listed ones).",
        "params": {
            "format": {"type": "string", "default": "Page {n} of {total}"},
            "fontsize": {"type": "integer", "default": 10, "min": 6, "max": 48},
            "pages": {"type": "array", "items": {"type": "integer"}},
        },
        "run": _page_numbers,
    },
}


def list_ops():
    return {name: {"description": spec["description"], "params": spec["params"]} for name, spec in OPS.items()}


def apply_ops(input_path, output_path, ops):
    if not isinstance(ops, list) or not ops:
        raise ValueError("ops has to be a non-empty list, e.g. [{\"op\": \"rotate\", \"angle\": 90}]")
    if os.path.splitext(input_path)[1].lower() != ".pdf":
        raise ValueError("apply_ops only edits .pdf files")
    reader = PdfReader(input_path)
    if reader.is_encrypted:
        raise ValueError("this pdf is encrypted, decrypt it first")
    job = _EditSession(PdfWriter(clone_from=input_path))
    applied = []
    for item in ops:
        if not isinstance(item, dict) or "op" not in item:
            raise ValueError("every op needs an 'op' name, e.g. {\"op\": \"rotate\", \"angle\": 90}")
        name = item["op"]
        if name not in OPS:
            raise ValueError(f"unknown op '{name}'. Run 'pdfforge ops' to see them all.")
        OPS[name]["run"](job, item)
        applied.append(name)
    writer = PdfWriter()
    for page in job.pages:
        writer.add_page(page)
    if job.metadata:
        writer.add_metadata(job.metadata)
    if job.compress:
        writer.remove_images()
        writer.compress_identical_objects()
    if job.password:
        writer.encrypt(job.password, job.owner_password or job.password)
    with open(output_path, "wb") as f:
        writer.write(f)
    out = {"output": output_path, "ops_applied": applied}
    out.update(describe(output_path))
    return out
