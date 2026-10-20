"""Builds a static web page (site/index.html) from the paper history."""

from datetime import date
from html import escape
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paper of the Day</title>
<style>
  :root {{
    --bg: #f7f6f2; --card: #ffffff; --text: #1d1d1f; --muted: #6b6b70;
    --accent: #2457c5; --border: #e3e1da;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #141416; --card: #1e1e22; --text: #ececf0; --muted: #9a9aa3;
      --accent: #7ea6ff; --border: #2e2e34;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  main {{ max-width: 760px; margin: 0 auto; padding: 40px 16px 64px; }}
  header h1 {{ font-size: 1.1rem; letter-spacing: .08em; text-transform: uppercase; margin: 0; }}
  header p {{ color: var(--muted); margin: 4px 0 0; }}
  nav {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 24px 0 8px; }}
  nav a {{
    color: var(--text); text-decoration: none; padding: 6px 14px; border-radius: 999px;
    border: 1px solid var(--border); font-size: .9rem;
  }}
  nav a:hover {{ border-color: var(--accent); }}
  section {{ margin-top: 32px; scroll-margin-top: 16px; }}
  .label {{ color: var(--muted); font-size: .85rem; text-transform: uppercase; letter-spacing: .06em; }}
  .card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: 24px; margin-top: 10px;
  }}
  .card h2 {{ font-family: Georgia, "Times New Roman", serif; font-size: 1.6rem; line-height: 1.25; margin: 0 0 12px; }}
  .meta {{ color: var(--muted); font-size: .9rem; margin: 0 0 16px; }}
  .abstract {{ margin: 0 0 20px; }}
  .links a {{
    display: inline-block; margin-right: 10px; padding: 8px 16px; border-radius: 8px;
    background: var(--accent); color: var(--bg); text-decoration: none; font-weight: 600; font-size: .9rem;
  }}
  .links a.secondary {{ background: transparent; color: var(--accent); border: 1px solid var(--accent); }}
  details {{ margin-top: 16px; }}
  summary {{ cursor: pointer; color: var(--muted); }}
  ul.archive {{ list-style: none; padding: 0; margin: 8px 0 0; }}
  ul.archive li {{ padding: 10px 0; border-bottom: 1px solid var(--border); display: flex; gap: 14px; }}
  ul.archive time {{ color: var(--muted); font-size: .85rem; flex: 0 0 auto; padding-top: 2px; }}
  ul.archive a {{ color: var(--text); text-decoration: none; }}
  ul.archive a:hover {{ color: var(--accent); }}
  footer {{ color: var(--muted); font-size: .8rem; margin-top: 48px; }}
  footer a {{ color: var(--muted); }}
</style>
</head>
<body>
<main>
  <header>
    <h1>Paper of the Day</h1>
    <p>One research paper a day, per topic. Updated {updated}.</p>
  </header>
  {nav}
  {sections}
  <footer>Papers from <a href="https://arxiv.org">arXiv</a>. Thank you to arXiv for use of its open access interoperability.</footer>
</main>
</body>
</html>
"""

SECTION = """<section id="{key}">
    <div class="label">{name} &middot; {day}</div>
    <article class="card">
      <h2>{title}</h2>
      <p class="meta">{authors}<br>Published {published} &middot; {categories}</p>
      <p class="abstract">{summary}</p>
      <div class="links">
        <a href="{url}">Read on arXiv</a>{pdf}
      </div>
    </article>
    {archive}
  </section>"""


def format_authors(authors):
    shown = ", ".join(authors[:6])
    return shown + (f" + {len(authors) - 6} more" if len(authors) > 6 else "")


def build_archive(entries):
    if not entries:
        return ""
    items = "\n".join(
        f'        <li><time>{escape(e["date"])}</time>'
        f'<a href="{escape(e["paper"]["url"])}">{escape(e["paper"]["title"])}</a></li>'
        for e in entries
    )
    return f"""<details>
      <summary>Earlier papers ({len(entries)})</summary>
      <ul class="archive">
{items}
      </ul>
    </details>"""


def build_site(history, topics, out_dir):
    sections = []
    for key, topic in topics.items():
        entries = sorted((h for h in history if h["topic"] == key), key=lambda h: h["date"], reverse=True)
        if not entries:
            continue
        latest, earlier = entries[0], entries[1:]
        paper = latest["paper"]
        pdf = f'<a class="secondary" href="{escape(paper["pdf"])}">PDF</a>' if paper.get("pdf") else ""
        sections.append(SECTION.format(
            key=escape(key),
            name=escape(topic["name"]),
            day=escape(latest["date"]),
            title=escape(paper["title"]),
            authors=escape(format_authors(paper["authors"])),
            published=escape(paper["published"]),
            categories=escape(", ".join(paper["categories"])),
            summary=escape(paper["summary"]),
            url=escape(paper["url"]),
            pdf=pdf,
            archive=build_archive(earlier),
        ))

    shown_topics = [(k, t) for k, t in topics.items() if any(h["topic"] == k for h in history)]
    nav = ""
    if len(shown_topics) > 1:
        links = "".join(f'<a href="#{escape(k)}">{escape(t["name"])}</a>' for k, t in shown_topics)
        nav = f"<nav>{links}</nav>"

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    page = PAGE.format(updated=date.today().isoformat(), nav=nav, sections="\n  ".join(sections))
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir / "index.html"
