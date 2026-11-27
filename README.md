# pdfforge

Edit, join, split and build PDFs from the terminal, from Python, or over MCP.

It works on .pdf files with pypdf and reportlab.

## Install

```sh
pip install git+https://github.com/Alfredo-ctrl/pdfforge.git
```

## Use it from the terminal

```sh
# what can it do?
pdfforge ops

# describe a file
pdfforge describe -i report.pdf

# read it as text
pdfforge read -i report.pdf

# edit it: keep pages 1 and 3, stamp a watermark, set the title
pdfforge edit -i report.pdf -o report-v2.pdf --ops '[
  {"op": "extract_pages", "pages": [1, 3]},
  {"op": "watermark", "text": "DRAFT"},
  {"op": "set_metadata", "title": "Weekly report"}
]'

# join PDFs and split them back
pdfforge merge -i a.pdf b.pdf -o joined.pdf
pdfforge split -i joined.pdf -o parts --every 2

# build a PDF from a structure
pdfforge create -o report.pdf --structure '{
  "title": "Weekly report", "author": "Alfredo Ramos",
  "sections": [{"heading": "Summary", "paragraphs": ["All good this week."]}]
}'
```

Running the edit above on a 3-page report prints:

```json
{"output": "report-v2.pdf", "ops_applied": ["extract_pages", "watermark", "set_metadata"], "format": "pdf", "encrypted": false, "size": 2886, "pages": 2, "title": "Weekly report", "author": null}
```

## Operations

`pdfforge ops` lists them all with their parameters:

- `extract_pages` — keep only the listed pages (1-based), in that order
- `remove_pages` — drop the listed pages
- `rotate` — rotate pages 90, 180 or 270 degrees
- `watermark` — stamp text diagonally on pages
- `set_metadata` — set the PDF title and/or author
- `encrypt` — lock the PDF with a password
- `compress` — drop embedded images, dedupe identical objects
- `page_numbers` — stamp "Page N of M" at the bottom of pages

## Use it from Python

```python
from pdfforge import apply_ops, create_pdf, describe, extract_text, merge, split

print(describe("report.pdf"))
print(extract_text("report.pdf", pages=[1])["text"])

out = merge(["a.pdf", "b.pdf"], "joined.pdf")

out = apply_ops("report.pdf", "report-v2.pdf", [
    {"op": "remove_pages", "pages": [2]},
    {"op": "rotate", "angle": 90},
])

out = create_pdf({
    "title": "Weekly report",
    "sections": [{"heading": "Summary", "paragraphs": ["All good this week."]}],
}, "report.pdf")
```

## MCP server

Any MCP client can use pdfforge as tools:

```sh
pdfforge mcp
```

It speaks MCP over stdio and exposes `edit_pdf`, `describe_pdf`, `read_pdf`, `merge_pdfs`, `split_pdf`, `create_pdf` and `list_operations`. Example client config:

```json
{
  "mcpServers": {
    "pdfforge": {"command": "pdfforge", "args": ["mcp"]}
  }
}
```

## License

See [LICENSE](LICENSE).
