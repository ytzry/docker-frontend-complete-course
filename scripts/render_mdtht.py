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

INDEX_STYLE = """
<style>
  :root {
    --page-bg: #fafafa;
    --panel-border: #d2d2d2;
    --text-main: #070909;
    --text-muted: #666c72;
    --accent: #3e69d7;
  }

  html.site-index-root,
  html.site-index-root body {
    min-height: 100%;
    overflow: auto;
  }

  body.site-index {
    margin: 0;
    background: var(--page-bg);
    color: var(--text-main);
  }

  .site-shell {
    width: min(96rem, calc(100% - 3.2rem));
    margin: 0 auto;
    padding: 5.6rem 0 7.2rem;
  }

  .hero {
    padding: 0 0 3.2rem;
    border-bottom: 1px solid var(--panel-border);
  }

  .hero-kicker {
    margin: 0;
    color: var(--accent);
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .hero h1 {
    margin: 1rem 0 0;
    font-size: clamp(3.2rem, 4vw, 4.6rem);
    line-height: 1.2;
    letter-spacing: 0.02em;
  }

  .hero-intro {
    max-width: 72rem;
    margin: 1.6rem 0 0;
    color: var(--text-muted);
    font-size: 1.6rem;
    line-height: 1.75;
    text-wrap: pretty;
  }

  .section-head {
    margin: 4rem 0 1.2rem;
  }

  .section-title {
    margin: 0;
    font-size: 2.4rem;
  }

  .section-head p {
    margin: 0.6rem 0 0;
    color: var(--text-muted);
    font-size: 1.4rem;
  }

  .stage-list {
    border-top: 1px solid var(--panel-border);
  }

  .stage-card {
    display: grid;
    grid-template-columns: 6.4rem minmax(0, 1fr);
    gap: 1.6rem;
    align-items: start;
    padding: 2rem 0;
    border-bottom: 1px solid var(--panel-border);
  }

  .stage-card-index {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    align-items: flex-start;
    padding-top: 0.2rem;
  }

  .stage-meta {
    color: var(--accent);
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .stage-step {
    color: var(--text-muted);
    font-size: 1.1rem;
    line-height: 1.5;
  }

  .stage-card-body {
    min-width: 0;
  }

  .stage-card-entry {
    display: block;
    min-width: 0;
    color: inherit;
    text-decoration: none;
  }

  .stage-card-entry:hover {
    text-decoration: none;
  }

  .stage-card-entry:focus-visible {
    outline: 0.2rem solid var(--accent);
    outline-offset: 0.3rem;
  }

  .stage-card h2 {
    margin: 0;
    font-size: 2rem;
    line-height: 1.4;
    word-break: break-word;
    transition: color 0.16s ease;
  }

  .stage-card p {
    margin: 0.8rem 0 0;
    color: var(--text-muted);
    line-height: 1.7;
    word-break: break-word;
  }

  .stage-card:hover h2,
  .stage-card-entry:hover h2 {
    color: var(--accent);
  }

  @media (prefers-reduced-motion: reduce) {
    .stage-card h2 {
      transition: none;
    }
  }

  @media (max-width: 720px) {
    .site-shell {
      width: min(100% - 2.4rem, 96rem);
      padding-top: 2.4rem;
      padding-bottom: 4.8rem;
    }

    .hero {
      padding-bottom: 2.4rem;
    }

    .hero h1 {
      font-size: 3rem;
      line-height: 1.28;
    }

    .hero-intro {
      margin-top: 1.2rem;
      font-size: 1.5rem;
      line-height: 1.7;
    }

    .stage-card {
      grid-template-columns: 1fr;
      gap: 0.8rem;
      padding: 1.6rem 0;
    }

    .stage-card-index {
      flex-direction: row;
      gap: 0.8rem;
      align-items: baseline;
    }

    .stage-card h2 {
      font-size: 1.85rem;
      line-height: 1.45;
    }

    .stage-card p {
      font-size: 1.5rem;
      line-height: 1.68;
    }
  }

  @media (max-width: 420px) {
    .site-shell {
      width: min(100% - 2rem, 96rem);
      padding-top: 2rem;
      padding-bottom: 4rem;
    }

    .hero-kicker {
      font-size: 1.1rem;
    }

    .hero h1 {
      font-size: 2.7rem;
    }

    .section-head {
      margin-top: 3.2rem;
    }

    .section-title {
      font-size: 2.1rem;
    }

    .section-head p,
    .stage-step,
    .stage-meta {
      font-size: 1rem;
    }
  }
</style>
"""

STAGE_NAV_STYLE = """
<style>
  .course-nav {
    margin-top: 4rem;
    padding-top: 1.6rem;
    border-top: 1px solid #d2d2d2;
  }

  .course-nav-links {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .course-nav-link {
    display: inline-flex;
    align-items: center;
    min-height: 4rem;
    padding: 0.6rem 0;
    color: #3e69d7;
    font-size: 1.5rem;
    text-decoration: none;
    transition: color 0.16s ease;
  }

  .course-nav-link:hover {
    color: #f59102;
    text-decoration: none;
  }

  .course-nav-link-home {
    color: #070909;
    font-weight: 700;
  }

  .course-nav-link-body {
    display: flex;
    align-items: center;
    gap: 0.8rem;
  }

  .course-nav-link-label {
    color: #666c72;
    font-size: 1.2rem;
  }

  .course-nav-link-title {
    color: #070909;
    font-size: 1.5rem;
    line-height: 1.4;
  }

  .course-nav-link-empty {
    visibility: hidden;
    min-width: 10rem;
  }

  .course-nav-link:focus-visible {
    outline: 0.2rem solid #3e69d7;
    outline-offset: 0.2rem;
  }

  @media (prefers-reduced-motion: reduce) {
    .course-nav-link {
      transition: none;
    }
  }

  @media (max-width: 720px) {
    .course-nav-links {
      flex-direction: column;
      align-items: stretch;
      gap: 0.4rem;
    }

    .course-nav-link {
      justify-content: center;
      min-height: 4.4rem;
      padding: 0.8rem 0;
    }

    .course-nav-link-body {
      justify-content: center;
      flex-wrap: wrap;
      text-align: center;
    }

    .course-nav-link-empty {
      display: none;
    }

    .course-nav-link-title {
      font-size: 1.4rem;
    }
  }

  @media (max-width: 420px) {
    .course-nav {
      margin-top: 3.2rem;
      padding-top: 1.2rem;
    }

    .course-nav-link {
      min-height: 4.2rem;
      font-size: 1.4rem;
    }
  }
</style>
"""

ALERT_PATTERN = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", re.IGNORECASE)
TITLE_PATTERN = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
STAGE_TITLE_PATTERN = re.compile(r"第\s*(\d+)\s*阶段[:：]\s*(.+)")
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


def render_body(markdown_text: str) -> str:
    prepared_markdown = convert_github_alerts(markdown_text)
    return markdown.markdown(
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


def render_document(title: str, body: str, asset_prefix: str, lang: str) -> str:
    html_tag_class = "site-index-root" if asset_prefix == "./" and "site-index" in body else ""
    document = HTML_TEMPLATE.format(
        lang=lang,
        title=html.escape(title),
        asset_prefix=asset_prefix,
        body=body,
    )
    if html_tag_class:
        document = document.replace(f'<html lang="{lang}">', f'<html lang="{lang}" class="{html_tag_class}">', 1)
    return document


def extract_title(markdown_text: str, fallback: str) -> str:
    match = TITLE_PATTERN.search(markdown_text)
    if not match:
        return fallback
    return match.group(1).strip() or fallback


def extract_summary(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    paragraph: list[str] = []
    after_title = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            after_title = True
            continue
        if not after_title:
            continue
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("!["):
            continue
        paragraph.append(stripped)

    summary = " ".join(paragraph)
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 140:
        summary = summary[:137].rstrip() + "..."
    return summary


def stage_slug(stage_path: Path) -> str:
    return stage_path.stem


def stage_label(index: int) -> str:
    return f"Stage {index + 1:02d}"


def build_stage_nav(current_index: int, items: list[dict[str, str]]) -> str:
    prev_link = '<div class="course-nav-link course-nav-link-empty" aria-hidden="true"></div>'
    next_link = '<div class="course-nav-link course-nav-link-empty" aria-hidden="true"></div>'

    if current_index > 0:
        prev_item = items[current_index - 1]
        prev_link = (
            f'<a class="course-nav-link" href="./{prev_item["slug"]}.html">'
            '<span class="course-nav-link-body">'
            '<span class="course-nav-link-label">上一节</span>'
            f'<span class="course-nav-link-title">{html.escape(prev_item["short_title"])}</span>'
            "</span></a>"
        )

    if current_index < len(items) - 1:
        next_item = items[current_index + 1]
        next_link = (
            f'<a class="course-nav-link" href="./{next_item["slug"]}.html">'
            '<span class="course-nav-link-body">'
            '<span class="course-nav-link-label">下一节</span>'
            f'<span class="course-nav-link-title">{html.escape(next_item["short_title"])}</span>'
            "</span></a>"
        )

    return (
        STAGE_NAV_STYLE
        + '<nav class="course-nav">'
        + '<div class="course-nav-links">'
        + prev_link
        + '<a class="course-nav-link course-nav-link-home" href="../index.html">课程目录</a>'
        + next_link
        + "</div>"
        + "</nav>"
    )


def build_index_html(course_title: str, stage_items: list[dict[str, str]], lang: str) -> str:
    cards = []

    for item in stage_items:
        cards.append(
            '<article class="stage-card">'
            '<div class="stage-card-index">'
            f'<div class="stage-meta">{html.escape(item["label"])}</div>'
            f'<div class="stage-step">第 {int(item["order"])} 节</div>'
            "</div>"
            f'<a class="stage-card-entry" href="./stages/{item["slug"]}.html">'
            '<div class="stage-card-body">'
            f'<h2>{html.escape(item["title"])}</h2>'
            f'<p>{html.escape(item["summary"])}</p>'
            "</div></a>"
            "</article>"
        )

    body = (
        INDEX_STYLE
        + '<main class="site-index"><div class="site-shell">'
        + '<section class="hero">'
        + '<p class="hero-kicker">课程目录</p>'
        + f"<h1>{html.escape(course_title)}</h1>"
        + '<p class="hero-intro">围绕前端开发者的实际使用场景组织为 7 个阶段，从容器基础、镜像构建、网络协作到生产实践与 Kubernetes 衔接，按顺序完成整套学习路径。</p>'
        + "</section>"
        + '<div class="section-head">'
        + '<h2 class="section-title">阶段目录</h2>'
        + f'<p>共 {len(stage_items)} 个阶段</p>'
        + "</div>"
        + '<section class="stage-list">'
        + "".join(cards)
        + "</section>"
        + "</div></main>"
    )
    return render_document(course_title, body, "./", lang)


def build_site(stages_dir: Path, output_dir: Path, lang: str, course_title: str) -> None:
    stage_paths = sorted(stages_dir.glob("*.md"))
    if not stage_paths:
        raise SystemExit(f"No stage markdown files found in {stages_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stages_output_dir = output_dir / "stages"
    stages_output_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, str]] = []
    for index, stage_path in enumerate(stage_paths):
        raw_markdown = stage_path.read_text(encoding="utf-8")
        title = extract_title(raw_markdown, stage_path.stem)
        match = STAGE_TITLE_PATTERN.match(title)
        short_title = match.group(2).strip() if match else title
        items.append(
            {
                "slug": stage_slug(stage_path),
                "title": title,
                "short_title": short_title,
                "summary": extract_summary(raw_markdown),
                "label": stage_label(index),
                "order": f"{index + 1:02d}",
            }
        )

    for index, item in enumerate(items):
        stage_path = stages_dir / f"{item['slug']}.md"
        raw_markdown = stage_path.read_text(encoding="utf-8")
        body = render_body(raw_markdown) + build_stage_nav(index, items)
        html_text = render_document(item["title"], body, "../", lang)
        (stages_output_dir / f"{item['slug']}.html").write_text(html_text, encoding="utf-8")

    index_html = build_index_html(course_title, items, lang)
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a staged Markdown course to a multi-page Mdtht site.")
    parser.add_argument("--stages-dir", type=Path, default=Path("stages"), help="Directory containing stage markdown files")
    parser.add_argument("--output-dir", type=Path, default=Path("site"), help="Directory for generated site files")
    parser.add_argument("--lang", default="zh-CN", help="HTML lang attribute")
    parser.add_argument("--course-title", default="面向前端开发者的 Docker 教程", help="Course title for generated pages")
    args = parser.parse_args()

    build_site(
        stages_dir=args.stages_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        lang=args.lang,
        course_title=args.course_title,
    )


if __name__ == "__main__":
    main()
