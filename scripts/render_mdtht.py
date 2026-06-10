from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import markdown


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{asset_prefix}vendor/mdtht/mdtht.min.css">
</head>
<body>
{body}
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script>hljs.highlightAll();</script>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    window.mermaid = mermaid;
  </script>
  <script src="{asset_prefix}vendor/mdtht/mdtht.min.js"></script>
</body>
</html>
"""


ALERT_PATTERN = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", re.IGNORECASE)
ALERT_CLASS_MAP = {
    "note": "note",
    "tip": "tip",
    "important": "important",
    "warning": "warning",
    "caution": "caution",
}


def convert_github_alerts(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    result: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.startswith(">"):
            result.append(line)
            index += 1
            continue

        quote_lines: list[str] = []
        while index < len(lines) and lines[index].startswith(">"):
            current = lines[index][1:]
            if current.startswith(" "):
                current = current[1:]
            quote_lines.append(current)
            index += 1

        if not quote_lines:
            result.append(line)
            continue

        match = ALERT_PATTERN.match(quote_lines[0].strip())
        if not match:
            result.extend(f"> {item}" if item else ">" for item in quote_lines)
            continue

        alert_type = ALERT_CLASS_MAP[match.group(1).lower()]
        title_suffix = match.group(2).strip()
        title_text = match.group(1).capitalize()
        if title_suffix:
            title_text = f"{title_text}: {title_suffix}"

        body_lines = quote_lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()

        body_markdown = "\n".join(body_lines).strip()
        body_html = markdown.markdown(
            body_markdown,
            extensions=["extra", "fenced_code", "tables", "sane_lists"],
            output_format="html5",
        ) if body_markdown else ""

        result.append(
            f'<div class="md-alert md-alert-{alert_type}">'
            f'<p class="md-alert-text-{alert_type}"><strong>{html.escape(title_text)}</strong></p>'
            f"{body_html}"
            "</div>"
        )

    return "\n".join(result)


def render_markdown(source_path: Path, asset_prefix: str, lang: str) -> str:
    raw_markdown = source_path.read_text(encoding="utf-8")
    prepared_markdown = convert_github_alerts(raw_markdown)
    rendered_body = markdown.markdown(
        prepared_markdown,
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "sane_lists",
            "codehilite",
            "toc",
        ],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "use_pygments": False,
                "css_class": "hljs",
                "lang_prefix": "language-",
            }
        },
        output_format="html5",
    )

    title = source_path.stem
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", rendered_body, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() or title

    return HTML_TEMPLATE.format(
        lang=lang,
        title=html.escape(title),
        asset_prefix=asset_prefix,
        body=rendered_body,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Markdown to Mdtht themed HTML.")
    parser.add_argument("source", type=Path, help="Source markdown file")
    parser.add_argument("output", type=Path, help="Output html file")
    parser.add_argument("--lang", default="zh-CN", help="HTML lang attribute")
    parser.add_argument(
        "--asset-prefix",
        default="./",
        help="Asset prefix used in generated HTML, for example ./ or ../",
    )
    args = parser.parse_args()

    source_path = args.source.resolve()
    output_path = args.output.resolve()
    prefix = args.asset_prefix

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(source_path, prefix, args.lang),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
