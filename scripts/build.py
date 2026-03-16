#!/usr/bin/env python3
"""Генератор статичного сайту для book-library."""

import os
import json
import re
from pathlib import Path

BOOKS_DIR = Path(__file__).parent.parent / "books"
SITE_DIR = Path(__file__).parent.parent / "site"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Парсить YAML frontmatter з markdown файлу."""
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    yaml_text = content[3:end].strip()
    body = content[end + 3:].strip()

    data = {}
    for line in yaml_text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()

        # Список (tags: ["a", "b"] або tags: [a, b])
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if inner:
                items = [x.strip().strip('"').strip("'") for x in inner.split(",")]
                data[key] = [i for i in items if i]
            else:
                data[key] = []
        # Рядок у лапках
        elif val.startswith('"') and val.endswith('"'):
            data[key] = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            data[key] = val[1:-1]
        # Число
        elif val.isdigit():
            data[key] = int(val)
        # Порожнє
        elif val == "" or val is None:
            data[key] = None
        else:
            data[key] = val

    return data, body


def parse_body_sections(body: str) -> tuple[str, str]:
    """Витягує секції 'Нотатки автора джерела' і 'Мої нотатки'."""
    source_notes = ""
    my_notes = ""

    # Шукаємо секції
    src_match = re.search(
        r"##\s*Нотатки автора джерела\s*\n(.*?)(?=##|\Z)",
        body,
        re.DOTALL
    )
    my_match = re.search(
        r"##\s*Мої нотатки\s*\n(.*?)(?=##|\Z)",
        body,
        re.DOTALL
    )

    if src_match:
        source_notes = src_match.group(1).strip()
    if my_match:
        my_notes = my_match.group(1).strip()

    return source_notes, my_notes


def load_books() -> list[dict]:
    books = []
    for md_file in sorted(BOOKS_DIR.glob("*.md")):
        if md_file.name == ".gitkeep":
            continue
        content = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        if not meta.get("title"):
            continue

        source_notes, my_notes = parse_body_sections(body)
        meta["source_author_notes"] = source_notes
        meta["my_notes"] = my_notes
        meta["slug"] = md_file.stem
        books.append(meta)

    # Сортування: спочатку reading, потім want-to-read, потім done
    order = {"reading": 0, "want-to-read": 1, "done": 2}
    books.sort(key=lambda b: (order.get(b.get("status", ""), 9), b.get("date_added", "")))
    return books


def stars(rating) -> str:
    if not rating:
        return ""
    r = int(rating)
    return "★" * r + "☆" * (5 - r)


def escape_html(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_html(books: list[dict]) -> str:
    books_json = json.dumps(books, ensure_ascii=False)

    # Зібрати унікальні жанри і теги
    genres = sorted(set(b.get("genre", "") for b in books if b.get("genre")))

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📚 Book Library</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #1a1a1a;
    --surface: #242424;
    --surface2: #2e2e2e;
    --border: #383838;
    --text: #e0e0e0;
    --muted: #888;
    --accent: #7c9cff;
    --accent2: #a78bfa;
    --done: #4ade80;
    --reading: #facc15;
    --want: #60a5fa;
    --star: #f59e0b;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
  }}

  header {{
    padding: 2rem 1.5rem 1rem;
    border-bottom: 1px solid var(--border);
  }}

  header h1 {{
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 1rem;
  }}

  .filters {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
  }}

  select {{
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.35rem 0.75rem;
    font-size: 14px;
    cursor: pointer;
    outline: none;
  }}

  select:focus {{ border-color: var(--accent); }}

  .count {{
    color: var(--muted);
    font-size: 13px;
    margin-left: auto;
  }}

  main {{
    padding: 1.5rem;
    max-width: 900px;
  }}

  .book-list {{
    display: flex;
    flex-direction: column;
    gap: 1px;
  }}

  .book-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    cursor: pointer;
    transition: border-color 0.15s;
    margin-bottom: 0.5rem;
  }}

  .book-card:hover {{ border-color: var(--accent); }}
  .book-card.open {{ border-color: var(--accent2); }}

  .card-header {{
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    flex-wrap: wrap;
  }}

  .card-main {{ flex: 1; min-width: 0; }}

  .book-title {{
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
  }}

  .book-author {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 1px;
  }}

  .badges {{
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    align-items: center;
    margin-top: 0.5rem;
  }}

  .badge {{
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 500;
    white-space: nowrap;
  }}

  .badge-genre {{ background: #2d3a4a; color: #93c5fd; }}
  .badge-done {{ background: #14532d; color: var(--done); }}
  .badge-reading {{ background: #422006; color: var(--reading); }}
  .badge-want {{ background: #1e3a5f; color: var(--want); }}
  .badge-source {{ background: var(--surface2); color: var(--muted); }}

  .stars {{
    color: var(--star);
    font-size: 13px;
    margin-left: auto;
    white-space: nowrap;
  }}

  .card-body {{
    display: none;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
  }}

  .open .card-body {{ display: block; }}

  .notes-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }}

  @media (max-width: 600px) {{
    .notes-grid {{ grid-template-columns: 1fr; }}
  }}

  .notes-block h4 {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }}

  .notes-block p {{
    font-size: 13px;
    color: #c0c0c0;
    white-space: pre-wrap;
    line-height: 1.7;
  }}

  .meta-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 0.75rem;
    font-size: 12px;
    color: var(--muted);
  }}

  .meta-row a {{
    color: var(--accent);
    text-decoration: none;
  }}

  .meta-row a:hover {{ text-decoration: underline; }}

  .tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.75rem;
  }}

  .tag {{
    background: var(--surface2);
    color: var(--muted);
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 4px;
  }}

  .empty {{
    color: var(--muted);
    padding: 2rem 0;
    font-size: 14px;
  }}
</style>
</head>
<body>

<header>
  <h1>📚 Book Library</h1>
  <div class="filters">
    <select id="f-status" onchange="render()">
      <option value="">Всі статуси</option>
      <option value="reading">Читаю</option>
      <option value="want-to-read">Хочу прочитати</option>
      <option value="done">Прочитано</option>
    </select>
    <select id="f-genre" onchange="render()">
      <option value="">Всі жанри</option>
      {''.join(f'<option value="{escape_html(g)}">{escape_html(g)}</option>' for g in genres)}
    </select>
    <select id="f-rating" onchange="render()">
      <option value="">Будь-який рейтинг</option>
      <option value="5">★★★★★</option>
      <option value="4">★★★★☆+</option>
      <option value="3">★★★☆☆+</option>
    </select>
    <span class="count" id="count"></span>
  </div>
</header>

<main>
  <div class="book-list" id="list"></div>
</main>

<script>
const BOOKS = {books_json};

const STATUS_LABEL = {{
  'done': 'Прочитано',
  'reading': 'Читаю',
  'want-to-read': 'Хочу прочитати'
}};

const SOURCE_LABEL = {{
  'youtube': 'YouTube',
  'article': 'Стаття',
  'personal': 'Особисте'
}};

function stars(r) {{
  if (!r) return '';
  return '★'.repeat(r) + '☆'.repeat(5 - r);
}}

function badgeClass(status) {{
  return {{ done: 'badge-done', reading: 'badge-reading', 'want-to-read': 'badge-want' }}[status] || 'badge-source';
}}

function esc(s) {{
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function render() {{
  const status = document.getElementById('f-status').value;
  const genre = document.getElementById('f-genre').value;
  const minRating = parseInt(document.getElementById('f-rating').value) || 0;

  const filtered = BOOKS.filter(b =>
    (!status || b.status === status) &&
    (!genre || b.genre === genre) &&
    (!minRating || (b.rating && b.rating >= minRating))
  );

  document.getElementById('count').textContent = filtered.length + ' книг';

  const list = document.getElementById('list');
  if (!filtered.length) {{
    list.innerHTML = '<p class="empty">Нічого не знайдено.</p>';
    return;
  }}

  list.innerHTML = filtered.map(b => {{
    const tags = (b.tags || []).map(t => `<span class="tag">${{esc(t)}}</span>`).join('');
    const ratingStars = b.rating ? `<span class="stars">${{stars(b.rating)}}</span>` : '';
    const srcNotes = b.source_author_notes
      ? `<div class="notes-block"><h4>Нотатки автора джерела</h4><p>${{esc(b.source_author_notes)}}</p></div>`
      : '';
    const myNotes = b.my_notes
      ? `<div class="notes-block"><h4>Мої нотатки</h4><p>${{esc(b.my_notes)}}</p></div>`
      : '';
    const hasNotes = srcNotes || myNotes;

    return `
    <div class="book-card" onclick="toggle(this)">
      <div class="card-header">
        <div class="card-main">
          <div class="book-title">${{esc(b.title)}}</div>
          <div class="book-author">${{esc(b.author)}}</div>
          <div class="badges">
            ${{b.genre ? `<span class="badge badge-genre">${{esc(b.genre)}}</span>` : ''}}
            ${{b.status ? `<span class="badge ${{badgeClass(b.status)}}">${{STATUS_LABEL[b.status] || b.status}}</span>` : ''}}
            ${{b.source_type ? `<span class="badge badge-source">${{SOURCE_LABEL[b.source_type] || b.source_type}}</span>` : ''}}
          </div>
        </div>
        ${{ratingStars}}
      </div>
      <div class="card-body">
        <div class="meta-row">
          ${{b.date_added ? `<span>📅 ${{esc(b.date_added)}}</span>` : ''}}
          ${{b.source_url ? `<a href="${{esc(b.source_url)}}" target="_blank" rel="noopener">🔗 Джерело</a>` : ''}}
        </div>
        ${{hasNotes ? `<div class="notes-grid">${{srcNotes}}${{myNotes}}</div>` : ''}}
        ${{tags ? `<div class="tags">${{tags}}</div>` : ''}}
      </div>
    </div>`;
  }}).join('');
}}

function toggle(el) {{
  el.classList.toggle('open');
}}

render();
</script>
</body>
</html>"""


def main():
    books = load_books()
    SITE_DIR.mkdir(exist_ok=True)
    html = render_html(books)
    out = SITE_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Побудовано: {out} ({len(books)} knyh)")


if __name__ == "__main__":
    main()
