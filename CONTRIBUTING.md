# Contributing

pdfforge grows by adding operations. An operation is one function in `pdfforge/ops.py` plus one entry in the `OPS` dict: name, a one-line description, and a params schema (type, default, min/max or enum).

Rules:

- One op does one thing. Keep it small: if the function needs more than ~15 lines, split it.
- Never break the JSON contract: `pdfforge ops` must keep working, and every op must run on any .pdf.
- A new feature touches code, test, README, MCP description and example in the same commit.
- Add a test in `tests/test_ops.py` for anything new.
- Run `python -m unittest discover -s tests` before opening a PR.
- One commit per change, with a message that says why, not just what.
