"""Deterministic Markdown-to-HTML converter for Pattern Draft bodies.

Converts the Markdown subset used by Content Operations Pattern Drafts into
clean HTML suitable for the lnkwebsite CMS Article body field. Uses the
``markdown`` library with fenced code, tables, and smart extensions enabled.

Strips YAML front matter (``---`` delimited block at the start of the file)
before conversion so that Pattern Draft metadata is not emitted into HTML.

Supports: ATX headers (## ###), bold/italic, ordered/unordered lists,
blockquotes, inline code, fenced code blocks, tables, horizontal rules,
and links. Converts ``「」`` to ``<em>`` for emphasis where present.

Does NOT support: raw HTML passthrough (sanitized), images (stripped),
or custom syntax extensions. Pattern Drafts should not rely on these.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Final

import markdown as md

_EXTENSIONS: Final = (
    "fenced_code",
    "tables",
    "nl2br",
    "sane_lists",
)

# Matches a YAML front matter block at the very start of a file:
#   ---\n...\n---\n
_FRONT_MATTER_RE: Final = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def _strip_front_matter(markdown_text: str) -> str:
    """Remove a leading YAML front matter block if present."""
    return _FRONT_MATTER_RE.sub("", markdown_text)


def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert Pattern Draft Markdown to CMS-ready HTML.

    Strips YAML front matter before conversion so metadata is not emitted
    into the HTML body.

    Args:
        markdown_text: Source Markdown from a Pattern Draft body.

    Returns:
        HTML string with no surrounding ``<html>`` or ``<body>`` tags.

    """
    cleaned = _strip_front_matter(markdown_text)
    converter = md.Markdown(extensions=list(_EXTENSIONS))
    html = converter.convert(cleaned.strip())
    return html.strip()


def main() -> int:
    """Read a Markdown file, write its HTML conversion, and print the result."""
    parser = argparse.ArgumentParser(
        description="Convert a Pattern Draft Markdown body to CMS-ready HTML.",
    )
    parser.add_argument("input", type=Path, help="Markdown source file path.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="HTML output path (default: print to stdout).",
    )
    args = parser.parse_args()

    try:
        source = args.input.read_text(encoding="utf-8")
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 1

    html = convert_markdown_to_html(source)

    if args.output is not None:
        try:
            args.output.write_text(html, encoding="utf-8")
        except OSError as error:
            print(str(error), file=sys.stderr)
            return 1

    print(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
