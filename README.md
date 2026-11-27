# pdfforge

PDF tools for AI agents. No GUI, no account, no vendor lock-in: a CLI, a Python API and an MCP server that any agent can drive — Muse, Antigravity, Codex, Claude Code, or a local model.

It works on .pdf files with pypdf and reportlab, so install the package and you are set.

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

Output is JSON, so it is easy to parse:

```json
{"output": "report-v2.pdf", "ops_applied": ["extract_pages", "watermark", "set_metadata"], "format": "pdf", "pages": 2, "encrypted": false, "size": 18341, "title": "Weekly report", "author": null}
```

## How an agent uses it

You translate the user's words into ops. `pdfforge ops` lists every operation with its parameters, so there is nothing to guess. Examples:

- "keep only the first three pages" -> extract_pages
- "stamp DRAFT on every page" -> watermark
- "join these three PDFs" -> merge
- "split it into one file per page" -> split
- "what is in this file?" -> describe, read

If the user asks for something that is not an op yet, add it — see CONTRIBUTING.md. That is the whole point: the tool grows with what people ask for.

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

MIT
