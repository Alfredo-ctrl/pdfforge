"""Tests run against small generated PDFs, no fixtures needed."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdfforge import apply_ops, create_pdf, describe, extract_text, list_ops, merge, split  # noqa: E402


def _make_pdf(path, pages=4):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

    styles = getSampleStyleSheet()
    story = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"Report page {i}", styles["Heading1"]))
        story.append(Paragraph(f"This is the body text of page {i}.", styles["Normal"]))
        if i < pages:
            story.append(PageBreak())
    SimpleDocTemplate(path, pagesize=A4, title="Test report", author="Alfredo Ramos").build(story)


def _make_image_pdf(path):
    # a PDF with a big embedded photo: compress should shrink it a lot
    import numpy as np
    from PIL import Image
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    arr = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
    img_path = path + ".png"
    Image.fromarray(arr).save(img_path)
    c = canvas.Canvas(path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    c.save()
    os.remove(img_path)


class TestPdfforge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.pdf = os.path.join(cls.tmp, "report.pdf")
        _make_pdf(cls.pdf)
        cls.pdf2 = os.path.join(cls.tmp, "other.pdf")
        _make_pdf(cls.pdf2, pages=2)
        cls.img_pdf = os.path.join(cls.tmp, "photo.pdf")
        _make_image_pdf(cls.img_pdf)

    def out(self, name):
        return os.path.join(self.tmp, name)

    def test_ops_list(self):
        ops = list_ops()
        self.assertEqual(len(ops), 8)
        for name in ("extract_pages", "remove_pages", "rotate", "watermark", "set_metadata", "encrypt", "compress"):
            self.assertIn(name, ops)

    def test_describe(self):
        info = describe(self.pdf)
        self.assertEqual(info["pages"], 4)
        self.assertEqual(info["title"], "Test report")
        self.assertEqual(info["author"], "Alfredo Ramos")
        self.assertFalse(info["encrypted"])

    def test_describe_missing(self):
        with self.assertRaises(ValueError):
            describe(os.path.join(self.tmp, "nope.pdf"))

    def test_extract_text(self):
        out = extract_text(self.pdf)
        self.assertEqual(len(out["pages"]), 4)
        self.assertIn("Report page 2", out["text"])
        self.assertIn("body text of page 3", out["text"])

    def test_extract_text_pages(self):
        out = extract_text(self.pdf, pages=[2])
        self.assertEqual(len(out["pages"]), 1)
        self.assertIn("Report page 2", out["text"])
        self.assertNotIn("Report page 3", out["text"])

    def test_extract_pages(self):
        out = apply_ops(self.pdf, self.out("kept.pdf"), [{"op": "extract_pages", "pages": [1, 3]}])
        self.assertEqual(out["pages"], 2)
        text = extract_text(self.out("kept.pdf"))["text"]
        self.assertIn("Report page 1", text)
        self.assertIn("Report page 3", text)
        self.assertNotIn("Report page 2", text)

    def test_remove_pages(self):
        out = apply_ops(self.pdf, self.out("cut.pdf"), [{"op": "remove_pages", "pages": [2]}])
        self.assertEqual(out["pages"], 3)
        text = extract_text(self.out("cut.pdf"))["text"]
        self.assertNotIn("Report page 2", text)

    def test_remove_all_pages_fails(self):
        with self.assertRaises(ValueError):
            apply_ops(self.pdf, self.out("empty.pdf"), [{"op": "remove_pages", "pages": [1, 2, 3, 4]}])

    def test_rotate(self):
        out = apply_ops(self.pdf, self.out("rot.pdf"), [{"op": "rotate", "angle": 90}])
        self.assertEqual(out["pages"], 4)
        from pypdf import PdfReader

        self.assertEqual(PdfReader(self.out("rot.pdf")).pages[0].get("/Rotate"), 90)

    def test_rotate_one_page(self):
        out = apply_ops(self.pdf, self.out("rot1.pdf"), [{"op": "rotate", "angle": 180, "pages": [2]}])
        self.assertEqual(out["pages"], 4)
        from pypdf import PdfReader

        pages = PdfReader(self.out("rot1.pdf")).pages
        self.assertEqual(pages[1].get("/Rotate"), 180)
        self.assertIn(pages[0].get("/Rotate"), (None, 0))

    def test_watermark(self):
        out = apply_ops(self.pdf, self.out("wm.pdf"), [{"op": "watermark", "text": "DRAFT"}])
        self.assertEqual(out["pages"], 4)
        text = extract_text(self.out("wm.pdf"))["text"]
        self.assertIn("DRAFT", text)
        self.assertIn("Report page 1", text)

    def test_set_metadata(self):
        out = apply_ops(self.pdf, self.out("meta.pdf"), [{"op": "set_metadata", "title": "Final", "author": "Alfredo Ramos"}])
        self.assertEqual(out["title"], "Final")
        self.assertEqual(out["author"], "Alfredo Ramos")

    def test_encrypt(self):
        out = apply_ops(self.pdf, self.out("locked.pdf"), [
            {"op": "encrypt", "password": "secret", "owner_password": "owner-secret"}])
        self.assertTrue(out["encrypted"])
        with self.assertRaises(ValueError):
            extract_text(self.out("locked.pdf"))
        from pypdf import PdfReader

        reader = PdfReader(self.out("locked.pdf"))
        self.assertEqual(reader.decrypt("secret"), 1)
        self.assertEqual(len(reader.pages), 4)

    def test_compress(self):
        before = os.path.getsize(self.img_pdf)
        out = apply_ops(self.img_pdf, self.out("small.pdf"), [{"op": "compress"}])
        after = os.path.getsize(self.out("small.pdf"))
        self.assertEqual(out["pages"], 1)
        self.assertLess(after, before // 2)

    def test_page_numbers(self):
        out = apply_ops(self.pdf, self.out("numbered.pdf"), [{"op": "page_numbers"}])
        self.assertEqual(out["pages"], 4)
        text = extract_text(self.out("numbered.pdf"))["text"]
        self.assertIn("Page 1 of 4", text)
        self.assertIn("Page 4 of 4", text)
        self.assertIn("Report page 1", text)

    def test_page_numbers_custom_format(self):
        apply_ops(self.pdf, self.out("numbered2.pdf"),
                  [{"op": "page_numbers", "format": "{n}/{total}", "pages": [2]}])
        text = extract_text(self.out("numbered2.pdf"))["text"]
        self.assertIn("2/4", text)
        self.assertNotIn("1/4", text)

    def test_page_numbers_bad_format_fails(self):
        with self.assertRaises(ValueError):
            apply_ops(self.pdf, self.out("bad.pdf"), [{"op": "page_numbers", "format": "Page"}])

    def test_unknown_op_fails(self):
        with self.assertRaises(ValueError):
            apply_ops(self.pdf, self.out("bad.pdf"), [{"op": "nope"}])

    def test_bad_pages_fails(self):
        with self.assertRaises(ValueError):
            apply_ops(self.pdf, self.out("bad.pdf"), [{"op": "extract_pages", "pages": [99]}])

    def test_merge(self):
        out = merge([self.pdf, self.pdf2], self.out("joined.pdf"))
        self.assertEqual(out["pages"], 6)
        text = extract_text(self.out("joined.pdf"))["text"]
        self.assertIn("Report page 4", text)

    def test_merge_needs_two(self):
        with self.assertRaises(ValueError):
            merge([self.pdf], self.out("one.pdf"))

    def test_split(self):
        out = split(self.pdf, os.path.join(self.tmp, "parts"), every=2)
        self.assertEqual(out["parts"], 2)
        self.assertEqual(len(out["outputs"]), 2)
        self.assertEqual(describe(out["outputs"][0])["pages"], 2)
        self.assertEqual(describe(out["outputs"][1])["pages"], 2)

    def test_create_pdf(self):
        out = create_pdf({
            "title": "Weekly report",
            "author": "Alfredo Ramos",
            "sections": [{"heading": "Summary", "paragraphs": ["All good this week."]}],
        }, self.out("made.pdf"))
        self.assertEqual(out["pages"], 1)
        text = extract_text(self.out("made.pdf"))["text"]
        self.assertIn("Weekly report", text)
        self.assertIn("All good this week.", text)

    def test_cli_ops(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), ".."))
        r = subprocess.run([sys.executable, "-m", "pdfforge.cli", "ops"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("watermark", json.loads(r.stdout))

    def test_cli_edit(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), ".."))
        r = subprocess.run(
            [sys.executable, "-m", "pdfforge.cli", "edit", "-i", self.pdf, "-o", self.out("cli.pdf"),
             "--ops", '[{"op": "extract_pages", "pages": [1]}]'],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["pages"], 1)

    def test_cli_merge(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), ".."))
        r = subprocess.run(
            [sys.executable, "-m", "pdfforge.cli", "merge", "-i", self.pdf, self.pdf2, "-o", self.out("cli-joined.pdf")],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["pages"], 6)

    def test_mcp_smoke(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), ".."))
        proc = subprocess.Popen(
            [sys.executable, "-m", "pdfforge.cli", "mcp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env,
        )
        try:
            reqs = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                 "params": {"name": "list_operations", "arguments": {}}},
            ]
            for req in reqs:
                proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            lines = [proc.stdout.readline() for _ in range(3)]
            init = json.loads(lines[0])
            self.assertEqual(init["result"]["serverInfo"]["name"], "pdfforge")
            tools = json.loads(lines[1])["result"]["tools"]
            self.assertIn("merge_pdfs", [t["name"] for t in tools])
            payload = json.loads(json.loads(lines[2])["result"]["content"][0]["text"])
            self.assertIn("watermark", payload)
        finally:
            proc.stdin.close()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
