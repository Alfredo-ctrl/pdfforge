"""Minimal MCP server over stdio. No dependencies, plain JSON-RPC.

Tools: edit_pdf, describe_pdf, read_pdf, merge_pdfs, split_pdf, create_pdf,
list_operations.
"""

import json
import sys

from . import __version__, apply_ops, create_pdf, describe, extract_text, list_ops, merge, split

TOOLS = [
    {
        "name": "edit_pdf",
        "description": "Apply a list of PDF operations to a .pdf and save the result. Ops are the same ones list_operations returns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input .pdf path"},
                "output": {"type": "string", "description": "Output .pdf path"},
                "ops": {"type": "array", "items": {"type": "object"}, "description": "Ops to apply, e.g. [{\"op\": \"rotate\", \"angle\": 90}]"},
            },
            "required": ["input", "output", "ops"],
        },
    },
    {
        "name": "describe_pdf",
        "description": "Get page count, title, author, encrypted flag and size of a .pdf.",
        "inputSchema": {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "PDF path"}},
            "required": ["input"],
        },
    },
    {
        "name": "read_pdf",
        "description": "Extract the plain text of a .pdf, all pages or the listed ones.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "PDF path"},
                "pages": {"type": "array", "items": {"type": "integer"}, "description": "1-based page numbers, e.g. [1, 3]"},
            },
            "required": ["input"],
        },
    },
    {
        "name": "merge_pdfs",
        "description": "Join two or more PDFs into one, in the given order.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "inputs": {"type": "array", "items": {"type": "string"}, "description": "Input .pdf paths, at least 2"},
                "output": {"type": "string", "description": "Output .pdf path"},
            },
            "required": ["inputs", "output"],
        },
    },
    {
        "name": "split_pdf",
        "description": "Split a PDF into parts of N pages each, saved in the output directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input .pdf path"},
                "output_dir": {"type": "string", "description": "Directory for the parts"},
                "every": {"type": "integer", "description": "Pages per part (default 1)"},
            },
            "required": ["input", "output_dir"],
        },
    },
    {
        "name": "create_pdf",
        "description": "Build a .pdf from a structure dict: title, author, sections with heading and paragraphs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "structure": {"type": "object", "description": "Document structure dict"},
                "output": {"type": "string", "description": "Output .pdf path"},
            },
            "required": ["structure", "output"],
        },
    },
    {
        "name": "list_operations",
        "description": "List every operation with its parameters.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _text(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _call(name, args):
    if name == "list_operations":
        return _text(list_ops())
    if name == "describe_pdf":
        return _text(describe(args["input"]))
    if name == "read_pdf":
        return _text(extract_text(args["input"], args.get("pages")))
    if name == "edit_pdf":
        return _text(apply_ops(args["input"], args["output"], args["ops"]))
    if name == "merge_pdfs":
        return _text(merge(args["inputs"], args["output"]))
    if name == "split_pdf":
        return _text(split(args["input"], args["output_dir"], args.get("every", 1)))
    if name == "create_pdf":
        return _text(create_pdf(args["structure"], args["output"]))
    raise ValueError(f"unknown tool '{name}'")


def run():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method", "")
        req_id = req.get("id")
        if method in ("notifications/initialized", "notifications/cancelled"):
            continue
        if method == "initialize":
            result = {
                "protocolVersion": req.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "pdfforge", "version": __version__},
            }
            resp = {"result": result}
        elif method == "ping":
            resp = {"result": {}}
        elif method == "tools/list":
            resp = {"result": {"tools": TOOLS}}
        elif method == "tools/call":
            try:
                resp = {"result": _call(req["params"]["name"], req["params"].get("arguments", {}))}
            except Exception as e:
                resp = {"result": {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}}
        else:
            resp = {"error": {"code": -32601, "message": f"method not found: {method}"}}
        if req_id is not None:
            print(json.dumps({"jsonrpc": "2.0", "id": req_id, **resp}), flush=True)
