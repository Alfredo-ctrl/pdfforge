"""pdfforge command line. JSON in, JSON out."""

import argparse
import json
import sys

from . import (
    __version__,
    apply_ops,
    create_pdf,
    describe,
    extract_text,
    list_ops,
    merge,
    split,
)


def _exit_error(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)
    raise SystemExit(1)


def _print_result(payload):
    print(json.dumps(payload))


def cmd_edit(args):
    try:
        ops = json.loads(args.ops)
        result = apply_ops(args.input, args.output, ops)
    except (ValueError, RuntimeError, json.JSONDecodeError) as e:
        _exit_error(str(e))
    _print_result(result)


def cmd_ops(args):
    _print_result(list_ops())


def cmd_describe(args):
    try:
        result = describe(args.input)
    except ValueError as e:
        _exit_error(str(e))
    _print_result(result)


def cmd_read(args):
    try:
        pages = None
        if args.pages:
            pages = [int(x) for x in args.pages.split(",")]
        result = extract_text(args.input, pages)
    except (ValueError, RuntimeError) as e:
        _exit_error(str(e))
    _print_result(result)


def cmd_merge(args):
    try:
        result = merge(args.inputs, args.output)
    except ValueError as e:
        _exit_error(str(e))
    _print_result(result)


def cmd_split(args):
    try:
        result = split(args.input, args.output, args.every)
    except ValueError as e:
        _exit_error(str(e))
    _print_result(result)


def cmd_create(args):
    try:
        structure = json.loads(args.structure)
        result = create_pdf(structure, args.output)
    except (ValueError, json.JSONDecodeError) as e:
        _exit_error(str(e))
    _print_result(result)


def cmd_mcp(args):
    from .mcp_server import run

    run()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pdfforge", description="Edit, join, split and build PDFs.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_edit = sub.add_parser("edit", help="Apply operations to a .pdf and save the result.")
    p_edit.add_argument("-i", "--input", required=True, help="Input .pdf path")
    p_edit.add_argument("-o", "--output", required=True, help="Output .pdf path")
    p_edit.add_argument("--ops", required=True, help='JSON list of ops, e.g. \'[{"op": "rotate", "angle": 90}]\'')
    p_edit.set_defaults(func=cmd_edit)

    p_ops = sub.add_parser("ops", help="List every operation with its parameters.")
    p_ops.set_defaults(func=cmd_ops)

    p_desc = sub.add_parser("describe", help="Print PDF info as JSON.")
    p_desc.add_argument("-i", "--input", required=True, help="Input .pdf path")
    p_desc.set_defaults(func=cmd_describe)

    p_read = sub.add_parser("read", help="Extract the text of a .pdf.")
    p_read.add_argument("-i", "--input", required=True, help="Input .pdf path")
    p_read.add_argument("--pages", help="Pages to read, e.g. '1,3'")
    p_read.set_defaults(func=cmd_read)

    p_merge = sub.add_parser("merge", help="Join two or more PDFs into one.")
    p_merge.add_argument("-i", "--inputs", nargs="+", required=True, help="Input .pdf paths, in order")
    p_merge.add_argument("-o", "--output", required=True, help="Output .pdf path")
    p_merge.set_defaults(func=cmd_merge)

    p_split = sub.add_parser("split", help="Split a PDF into parts of N pages each.")
    p_split.add_argument("-i", "--input", required=True, help="Input .pdf path")
    p_split.add_argument("-o", "--output", required=True, help="Output directory for the parts")
    p_split.add_argument("--every", type=int, default=1, help="Pages per part (default 1)")
    p_split.set_defaults(func=cmd_split)

    p_create = sub.add_parser("create", help="Build a .pdf from a JSON structure.")
    p_create.add_argument("-o", "--output", required=True, help="Output .pdf path")
    p_create.add_argument("--structure", required=True, help='JSON structure, e.g. \'{"title": "Report", "sections": [{"heading": "Intro", "paragraphs": ["..."]}]}\'')
    p_create.set_defaults(func=cmd_create)

    p_mcp = sub.add_parser("mcp", help="Start the MCP server on stdio.")
    p_mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
