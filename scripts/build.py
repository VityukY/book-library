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
    --bg: #111;
    --surface: #1c1c1c;
    --surface2: #252525;
    --border: #2a2a2a;
    --text: #d4d4d4;
    --muted: #555;
    --accent: #6b8cff;
    --done: #4ade80;
    --reading: #facc15;
    --want: #60a5fa;
    --star: #f59e0b;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
    min-height: 100vh;
  }}

  /* ── header ── */
  header {{
    padding: 0.75rem 1.25rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 10;
  }}

  header h1 {{ font-size: 0.95rem; font-weight: 600; white-space: nowrap; }}

  .filters {{ display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; flex: 1; }}

  select {{
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    font-size: 12px;
    cursor: pointer;
    outline: none;
  }}
  select:focus {{ border-color: var(--accent); }}

  .count {{ color: var(--muted); font-size: 11px; margin-left: auto; }}

  /* ── grid ── */
  main {{ padding: 1.25rem; }}

  .book-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 0.75rem;
  }}

  /* ── card ── */
  .book-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.12s, border-color 0.12s, box-shadow 0.12s;
    display: flex;
    flex-direction: column;
  }}

  .book-card:hover {{
    transform: translateY(-2px);
    border-color: #3a3a3a;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
  }}

  /* кольорова смужка зверху = статус */
  .card-stripe {{
    height: 4px;
    width: 100%;
    flex-shrink: 0;
  }}
  .stripe-done    {{ background: var(--done); }}
  .stripe-reading {{ background: var(--reading); }}
  .stripe-want    {{ background: var(--want); }}
  .stripe-none    {{ background: var(--border); }}

  /* "обкладинка" — квадрат з першою літерою */
  .card-cover {{
    height: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -2px;
    user-select: none;
    flex-shrink: 0;
  }}

  /* ── тіло карточки ── */
  .card-body {{
    padding: 0.6rem 0.75rem 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    flex: 1;
  }}

  .book-title {{
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .book-author {{
    font-size: 11px;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .card-footer {{
    margin-top: auto;
    padding-top: 0.4rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.25rem;
  }}

  .badge {{
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 500;
    white-space: nowrap;
  }}
  .badge-genre   {{ background: #1e3250; color: #7db8f7; }}
  .badge-done    {{ background: #14532d55; color: var(--done); }}
  .badge-reading {{ background: #42200655; color: var(--reading); }}
  .badge-want    {{ background: #1e3a5f55; color: var(--want); }}

  .stars {{ color: var(--star); font-size: 10px; letter-spacing: 1px; }}

  /* ── модалка ── */
  .overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }}
  .overlay.open {{ display: flex; }}

  .modal {{
    background: var(--surface);
    border: 1px solid #333;
    border-radius: 10px;
    max-width: 640px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    padding: 1.5rem;
    position: relative;
  }}

  .modal-close {{
    position: absolute;
    top: 0.75rem;
    right: 1rem;
    background: none;
    border: none;
    color: var(--muted);
    font-size: 1.25rem;
    cursor: pointer;
    line-height: 1;
  }}
  .modal-close:hover {{ color: var(--text); }}

  .modal-title {{
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.2rem;
    padding-right: 1.5rem;
  }}
  .modal-author {{
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 0.75rem;
  }}

  .modal-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
  }}

  .meta-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    font-size: 11px;
    color: var(--muted);
  }}
  .meta-row a {{ color: var(--accent); text-decoration: none; }}
  .meta-row a:hover {{ text-decoration: underline; }}

  .divider {{ border: none; border-top: 1px solid var(--border); margin: 0.75rem 0; }}

  .notes-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }}
  @media (max-width: 480px) {{ .notes-grid {{ grid-template-columns: 1fr; }} }}

  .notes-block h4 {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 0.4rem;
  }}
  .notes-block p {{
    font-size: 12px;
    color: #bbb;
    white-space: pre-wrap;
    line-height: 1.6;
  }}

  .tags {{ display: flex; flex-wrap: wrap; gap: 0.25rem; }}
  .tag {{
    background: var(--surface2);
    color: var(--muted);
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 3px;
  }}

  .empty {{ color: var(--muted); padding: 2rem; font-size: 13px; }}
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
  <div class="book-grid" id="list"></div>
</main>

<!-- модалка -->
<div class="overlay" id="overlay" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modal-content"></div>
  </div>
</div>

<script>
const BOOKS = {books_json};

const STATUS_LABEL = {{ done:'Прочитано', reading:'Читаю', 'want-to-read':'Хочу прочитати' }};
const SOURCE_LABEL = {{ youtube:'YouTube', article:'Стаття', personal:'Особисте' }};

const COVER_COLORS = [
  ['#1a2a4a','#4a7fcf'],['#2a1a3a','#9b6bcf'],['#1a3a2a','#4acf8a'],
  ['#3a2a1a','#cf8a4a'],['#2a1a1a','#cf4a4a'],['#1a2a3a','#4acfcf'],
  ['#2a3a1a','#9bcf4a'],['#3a1a2a','#cf4a9b'],
];

function coverColor(title) {{
  let h = 0;
  for (let c of (title||'')) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return COVER_COLORS[h % COVER_COLORS.length];
}}

function stripeClass(status) {{
  return {{done:'stripe-done', reading:'stripe-reading','want-to-read':'stripe-want'}}[status] || 'stripe-none';
}}

function badgeClass(status) {{
  return {{done:'badge-done', reading:'badge-reading','want-to-read':'badge-want'}}[status] || '';
}}

function stars(r) {{ return r ? '★'.repeat(r)+'☆'.repeat(5-r) : ''; }}

function esc(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function render() {{
  const status = document.getElementById('f-status').value;
  const genre  = document.getElementById('f-genre').value;
  const minR   = parseInt(document.getElementById('f-rating').value) || 0;

  const filtered = BOOKS.filter(b =>
    (!status || b.status === status) &&
    (!genre  || b.genre  === genre)  &&
    (!minR   || (b.rating && b.rating >= minR))
  );

  document.getElementById('count').textContent = filtered.length + ' книг';

  const list = document.getElementById('list');
  if (!filtered.length) {{
    list.innerHTML = '<p class="empty">Нічого не знайдено.</p>';
    return;
  }}

  list.innerHTML = filtered.map((b, i) => {{
    const [bg, fg] = coverColor(b.title);
    const letter = (b.title || '?')[0].toUpperCase();
    const sc = stripeClass(b.status);
    const bc = badgeClass(b.status);
    const sl = STATUS_LABEL[b.status] || b.status;
    return `
    <div class="book-card" onclick="openModal(${{i}})">
      <div class="card-stripe ${{sc}}"></div>
      <div class="card-cover" style="background:${{bg}};color:${{fg}}">${{letter}}</div>
      <div class="card-body">
        <div class="book-title">${{esc(b.title)}}</div>
        <div class="book-author">${{esc(b.author)}}</div>
        <div class="card-footer">
          ${{b.status ? `<span class="badge ${{bc}}">${{sl}}</span>` : ''}}
          ${{b.rating ? `<span class="stars">${{stars(b.rating)}}</span>` : ''}}
        </div>
      </div>
    </div>`;
  }}).join('');
}}

let _filtered = [];

function openModal(idx) {{
  const status = document.getElementById('f-status').value;
  const genre  = document.getElementById('f-genre').value;
  const minR   = parseInt(document.getElementById('f-rating').value) || 0;
  _filtered = BOOKS.filter(b =>
    (!status || b.status === status) &&
    (!genre  || b.genre  === genre)  &&
    (!minR   || (b.rating && b.rating >= minR))
  );
  const b = _filtered[idx];
  if (!b) return;

  const srcNotes = b.source_author_notes
    ? `<div class="notes-block"><h4>Нотатки автора джерела</h4><p>${{esc(b.source_author_notes)}}</p></div>` : '';
  const myNotes = b.my_notes
    ? `<div class="notes-block"><h4>Мої нотатки</h4><p>${{esc(b.my_notes)}}</p></div>` : '';
  const tags = (b.tags||[]).map(t=>`<span class="tag">${{esc(t)}}</span>`).join('');
  const bc = badgeClass(b.status);

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-title">${{esc(b.title)}}</div>
    <div class="modal-author">${{esc(b.author)}}</div>
    <div class="modal-badges">
      ${{b.genre  ? `<span class="badge badge-genre">${{esc(b.genre)}}</span>` : ''}}
      ${{b.status ? `<span class="badge ${{bc}}">${{STATUS_LABEL[b.status]||b.status}}</span>` : ''}}
      ${{b.source_type ? `<span class="badge" style="background:#222;color:#888">${{SOURCE_LABEL[b.source_type]||b.source_type}}</span>` : ''}}
      ${{b.rating ? `<span class="stars">${{stars(b.rating)}}</span>` : ''}}
    </div>
    <div class="meta-row">
      ${{b.date_added ? `<span>📅 ${{esc(b.date_added)}}</span>` : ''}}
      ${{b.source_url ? `<a href="${{esc(b.source_url)}}" target="_blank" rel="noopener">🔗 Джерело</a>` : ''}}
    </div>
    ${{(srcNotes||myNotes) ? `<hr class="divider"><div class="notes-grid">${{srcNotes}}${{myNotes}}</div>` : ''}}
    ${{tags ? `<div class="tags">${{tags}}</div>` : ''}}
  `;
  document.getElementById('overlay').classList.add('open');
}}

function closeModal(e) {{
  if (!e || e.target === document.getElementById('overlay') || e.target.classList.contains('modal-close')) {{
    document.getElementById('overlay').classList.remove('open');
  }}
}}

document.addEventListener('keydown', e => {{ if (e.key==='Escape') closeModal({{target:document.getElementById('overlay')}}); }});

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
