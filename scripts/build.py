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
<title>Моя Бібліотека</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:           #0f0d0b;
    --surface:      #1a1713;
    --surface2:     #221e18;
    --surface3:     #2a2520;
    --border:       #302a22;
    --border-hover: #4a4035;
    --text:         #e8e0d0;
    --text-sec:     #b8a98a;
    --muted:        #6b5c45;
    --muted-light:  #8a7560;
    --accent:       #c8922a;
    --accent-glow:  rgba(200,146,42,0.15);
    --done:         #52c97a;
    --reading:      #e8b840;
    --want:         #6fa3e0;
    --star:         #d4882a;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 13px;
    min-height: 100vh;
  }}

  /* ── header ── */
  header {{
    position: sticky; top: 0; z-index: 10;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    box-shadow: 0 1px 0 rgba(200,146,42,0.04);
    padding: 14px 24px 12px;
  }}
  .header-brand {{
    display: flex; align-items: baseline; gap: 10px;
    margin-bottom: 10px;
  }}
  header h1 {{
    font-family: 'Lora', serif;
    font-size: 15px; font-weight: 600;
    color: var(--text);
  }}
  .header-subtitle {{
    font-size: 11px; color: var(--muted);
  }}
  .header-filters {{
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  }}
  .filter-sep {{
    color: var(--border); font-size: 12px;
  }}
  select {{
    background: var(--surface2);
    color: var(--text-sec);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 28px 5px 10px;
    font-size: 12px;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b5c45'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    background-size: 10px;
    min-width: 130px;
    outline: none;
    transition: border-color 0.15s;
  }}
  select:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(200,146,42,0.15);
  }}
  select option {{ background: #221e18; color: var(--text); }}

  /* ── grid ── */
  main {{ padding: 20px 24px; }}
  .section-label {{
    font-family: 'Lora', serif;
    font-size: 11px; font-style: italic;
    color: var(--muted); padding: 0 0 10px 2px;
    letter-spacing: 0.03em;
  }}
  .book-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
  }}

  /* ── card — spine effect ── */
  .book-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0 10px 10px 0;
    border-left-width: 4px;
    overflow: hidden;
    cursor: pointer;
    display: flex; flex-direction: column;
    transition: transform 0.18s cubic-bezier(0.25,0.46,0.45,0.94),
                box-shadow 0.18s ease, border-color 0.18s ease;
    animation: cardIn 0.25s ease both;
  }}
  .spine-done    {{ border-left-color: var(--done); }}
  .spine-reading {{ border-left-color: var(--reading); }}
  .spine-want    {{ border-left-color: var(--want); }}
  .spine-none    {{ border-left-color: var(--border); }}

  .book-card:hover {{
    transform: translateY(-4px) scale(1.01);
    border-color: var(--border-hover);
    box-shadow: 0 8px 24px rgba(0,0,0,0.5),
                0 0 0 1px rgba(200,146,42,0.08);
  }}
  .book-card.spine-done:hover    {{ border-left-color: var(--done); }}
  .book-card.spine-reading:hover {{ border-left-color: var(--reading); }}
  .book-card.spine-want:hover    {{ border-left-color: var(--want); }}
  .book-card.spine-none:hover    {{ border-left-color: var(--border); }}
  .book-card:hover .card-cover {{ filter: brightness(1.08); }}
  .book-card:hover .stars {{ color: #e8b840; }}

  @keyframes cardIn {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  /* ── cover block ── */
  .card-cover {{
    height: 130px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Lora', serif;
    font-size: 2.6rem; font-style: italic; font-weight: 400;
    user-select: none; flex-shrink: 0;
    position: relative;
    box-shadow: inset 0 -20px 30px rgba(0,0,0,0.4);
    transition: filter 0.18s ease;
  }}
  .genre-dot {{
    position: absolute; bottom: 8px; right: 8px;
    width: 8px; height: 8px; border-radius: 50%;
    opacity: 0.7; transition: opacity 0.15s, transform 0.15s;
  }}
  .book-card:hover .genre-dot {{ opacity: 1; transform: scale(1.3); }}
  .source-icon {{
    position: absolute; top: 8px; right: 8px;
    font-size: 11px; opacity: 0.35;
    transition: opacity 0.15s;
  }}
  .book-card:hover .source-icon {{ opacity: 0.6; }}

  /* ── card body ── */
  .card-body {{
    padding: 10px 12px 12px;
    display: flex; flex-direction: column;
    gap: 4px; flex: 1;
  }}
  .book-title {{
    font-size: 12.5px; font-weight: 600;
    color: var(--text); line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .book-author {{
    font-size: 11px; color: var(--muted-light);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .card-footer {{
    margin-top: auto; padding-top: 6px;
    border-top: 1px solid var(--surface3);
    display: flex; align-items: center;
    justify-content: space-between; flex-wrap: wrap; gap: 4px;
  }}
  .badge {{
    font-size: 10px; padding: 2px 7px;
    border-radius: 4px; font-weight: 500;
    letter-spacing: 0.02em; white-space: nowrap;
  }}
  .badge-done    {{ background: rgba(82,201,122,0.12);  color: var(--done);    border: 1px solid rgba(82,201,122,0.2); }}
  .badge-reading {{ background: rgba(232,184,64,0.12);  color: var(--reading); border: 1px solid rgba(232,184,64,0.2); }}
  .badge-want    {{ background: rgba(111,163,224,0.12); color: var(--want);    border: 1px solid rgba(111,163,224,0.2); }}
  .badge-genre   {{ background: rgba(200,146,42,0.08);  color: var(--accent);  border: 1px solid rgba(200,146,42,0.15); }}
  .badge-source  {{ background: var(--surface3); color: var(--muted-light); border: 1px solid var(--border); }}
  .stars {{ color: var(--star); font-size: 10px; letter-spacing: 1px; transition: color 0.15s; }}

  /* ── modal ── */
  .overlay {{
    display: none; position: fixed; inset: 0;
    background: rgba(10,8,6,0.82);
    backdrop-filter: blur(4px);
    z-index: 100; align-items: center; justify-content: center;
    padding: 1rem;
  }}
  .overlay.open {{ display: flex; animation: overlayIn 0.2s ease; }}
  @keyframes overlayIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}

  .modal {{
    background: #1e1a14;
    border: 1px solid #3a3025;
    border-radius: 14px;
    max-width: 660px; width: 100%;
    max-height: 88vh; overflow-y: auto;
    padding: 0; position: relative;
    box-shadow: 0 24px 64px rgba(0,0,0,0.7),
                0 0 0 1px rgba(200,146,42,0.06);
    animation: modalIn 0.22s cubic-bezier(0.25,0.46,0.45,0.94);
  }}
  @keyframes modalIn {{
    from {{ opacity: 0; transform: translateY(12px) scale(0.97); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  .modal::-webkit-scrollbar {{ width: 4px; }}
  .modal::-webkit-scrollbar-track {{ background: transparent; }}
  .modal::-webkit-scrollbar-thumb {{ background: #3a3025; border-radius: 2px; }}
  .modal::-webkit-scrollbar-thumb:hover {{ background: #4a4035; }}

  .modal-close {{
    position: absolute; top: 12px; right: 14px;
    width: 28px; height: 28px;
    background: rgba(0,0,0,0.4);
    border: 1px solid #3a3025; border-radius: 50%;
    color: var(--muted-light); font-size: 13px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; z-index: 2;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }}
  .modal-close:hover {{
    background: rgba(200,146,42,0.15);
    color: var(--text); border-color: rgba(200,146,42,0.4);
  }}

  .modal-cover-strip {{
    height: 80px; border-radius: 14px 14px 0 0;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Lora', serif; font-size: 3.5rem;
    font-style: italic; user-select: none;
    box-shadow: inset 0 -30px 40px rgba(0,0,0,0.5);
    flex-shrink: 0;
  }}

  .modal-header {{ padding: 16px 20px 14px; border-bottom: 1px solid #302a22; }}
  .modal-title {{
    font-family: 'Lora', serif;
    font-size: 18px; font-weight: 600; color: var(--text);
    margin-bottom: 4px; padding-right: 32px;
  }}
  .modal-author {{
    font-family: 'Lora', serif;
    font-size: 14px; font-style: italic;
    color: var(--text-sec); margin-bottom: 10px;
  }}
  .modal-badges {{
    display: flex; flex-wrap: wrap; gap: 6px;
  }}

  .meta-row {{
    padding: 12px 20px;
    display: flex; flex-wrap: wrap; gap: 12px;
    font-size: 11px; color: var(--muted);
    border-bottom: 1px solid #302a22;
  }}
  .meta-row a {{ color: var(--accent); text-decoration: none; }}
  .meta-row a:hover {{ text-decoration: underline; }}

  .notes-section {{ padding: 16px 20px; }}
  .notes-grid {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; position: relative;
  }}
  @media (max-width: 480px) {{
    .notes-grid {{ grid-template-columns: 1fr; }}
    .notes-grid::before {{ display: none; }}
  }}
  .notes-grid.two-cols::before {{
    content: ''; position: absolute;
    left: 50%; top: 0; bottom: 0;
    width: 1px; background: #302a22;
    transform: translateX(-50%);
  }}
  .notes-block h4 {{
    font-family: 'Inter', sans-serif;
    font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted);
    margin-bottom: 8px;
    padding-bottom: 6px; border-bottom: 1px solid #302a22;
  }}
  .notes-block p {{
    font-size: 12.5px; color: #c8b898;
    white-space: pre-wrap; line-height: 1.65;
  }}

  .tags-section {{ padding: 0 20px 16px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag {{
    background: #252018; color: var(--muted-light);
    border: 1px solid #302a22;
    font-size: 10.5px; padding: 2px 8px; border-radius: 4px;
    font-family: 'Inter', sans-serif;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    cursor: default;
  }}
  .tag:hover {{
    background: #2f2818; color: var(--text-sec);
    border-color: rgba(200,146,42,0.3);
  }}

  .empty {{ color: var(--muted); padding: 2rem; font-size: 13px; }}

  @media (max-width: 600px) {{
    header {{ padding: 12px 16px 10px; }}
    main {{ padding: 16px; }}
    .book-grid {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }}
    .header-filters {{ gap: 4px; }}
    select {{ min-width: 0; font-size: 11px; }}
  }}
  @media (min-width: 1400px) {{
    .book-grid {{ grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }}
    .modal {{ max-width: 720px; }}
  }}
</style>
</head>
<body>

<header>
  <div class="header-brand">
    <h1>Моя Бібліотека</h1>
    <span class="header-subtitle" id="count">0 книг</span>
  </div>
  <div class="header-filters">
    <select id="f-status" onchange="render()">
      <option value="">Всі статуси</option>
      <option value="reading">Читаю</option>
      <option value="want-to-read">Хочу прочитати</option>
      <option value="done">Прочитано</option>
    </select>
    <span class="filter-sep">·</span>
    <select id="f-genre" onchange="render()">
      <option value="">Всі жанри</option>
      {''.join(f'<option value="{escape_html(g)}">{escape_html(g)}</option>' for g in genres)}
    </select>
    <span class="filter-sep">·</span>
    <select id="f-rating" onchange="render()">
      <option value="">Будь-який рейтинг</option>
      <option value="5">★★★★★</option>
      <option value="4">★★★★☆+</option>
      <option value="3">★★★☆☆+</option>
    </select>
  </div>
</header>

<main>
  <div id="main-content"></div>
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
const SOURCE_ICON  = {{ youtube:'▶', article:'◉', personal:'◆' }};

const COVER_COLORS = [
  ['#1a2a4a','#4a7fcf'],['#2a1a3a','#9b6bcf'],['#1a3a2a','#4acf8a'],
  ['#3a2a1a','#cf8a4a'],['#2a1a1a','#cf4a4a'],['#1a2a3a','#4acfcf'],
  ['#2a3a1a','#9bcf4a'],['#3a1a2a','#cf4a9b'],
];

const GENRE_COLORS = {{
  'fantasy': '#9b6bcf',
  'sci-fi': '#4acfcf',
  'саморозвиток': '#4acf8a',
  'romance': '#cf4a9b',
  'thriller': '#cf4a4a',
  'horror': '#cf6a2a',
  'historical': '#8a6320',
  'literary': '#4a7fcf',
}};

function genreDotColor(genre) {{
  return GENRE_COLORS[(genre||'').toLowerCase()] || '#6b5c45';
}}

function coverColor(title) {{
  let h = 0;
  for (let c of (title||'')) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return COVER_COLORS[h % COVER_COLORS.length];
}}

function spineClass(status) {{
  return {{done:'spine-done', reading:'spine-reading','want-to-read':'spine-want'}}[status] || 'spine-none';
}}

function badgeClass(status) {{
  return {{done:'badge-done', reading:'badge-reading','want-to-read':'badge-want'}}[status] || '';
}}

function stars(r) {{ return r ? '★'.repeat(r)+'☆'.repeat(5-r) : ''; }}

function esc(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function cardHTML(b, idx) {{
  const [bg, fg] = coverColor(b.title);
  const letter = (b.title || '?')[0].toUpperCase();
  const sc = spineClass(b.status);
  const bc = badgeClass(b.status);
  const sl = STATUS_LABEL[b.status] || b.status;
  const dotColor = genreDotColor(b.genre);
  const srcIcon = SOURCE_ICON[b.source_type] || '';
  return `
  <div class="book-card ${{sc}}" onclick="openModal(${{idx}})">
    <div class="card-cover" style="background:${{bg}};color:${{fg}}">
      ${{letter}}
      <span class="genre-dot" style="background:${{dotColor}}"></span>
      ${{srcIcon ? `<span class="source-icon">${{srcIcon}}</span>` : ''}}
    </div>
    <div class="card-body">
      <div class="book-title">${{esc(b.title)}}</div>
      <div class="book-author">${{esc(b.author)}}</div>
      <div class="card-footer">
        ${{b.status ? `<span class="badge ${{bc}}">${{sl}}</span>` : ''}}
        ${{b.rating ? `<span class="stars">${{stars(b.rating)}}</span>` : ''}}
      </div>
    </div>
  </div>`;
}}

let _filtered = [];

function render() {{
  const status = document.getElementById('f-status').value;
  const genre  = document.getElementById('f-genre').value;
  const minR   = parseInt(document.getElementById('f-rating').value) || 0;

  _filtered = BOOKS.filter(b =>
    (!status || b.status === status) &&
    (!genre  || b.genre  === genre)  &&
    (!minR   || (b.rating && b.rating >= minR))
  );

  // Animated count update
  const countEl = document.getElementById('count');
  countEl.style.opacity = '0';
  countEl.style.transform = 'translateY(-4px)';
  setTimeout(() => {{
    countEl.textContent = _filtered.length + ' книг';
    countEl.style.transition = 'opacity 0.2s, transform 0.2s';
    countEl.style.opacity = '1';
    countEl.style.transform = 'translateY(0)';
  }}, 120);

  const mainContent = document.getElementById('main-content');
  if (!_filtered.length) {{
    mainContent.innerHTML = '<p class="empty">Нічого не знайдено.</p>';
    return;
  }}

  // Секція "Читаю зараз" тільки якщо немає фільтра по статусу
  const readingBooks = !status ? _filtered.filter(b => b.status === 'reading') : [];
  const otherBooks   = !status ? _filtered.filter(b => b.status !== 'reading') : _filtered;

  let html = '';

  if (readingBooks.length) {{
    const readingOffset = 0;
    html += `<p class="section-label">Читаю зараз</p>`;
    html += `<div class="book-grid">${{readingBooks.map((b, i) => cardHTML(b, _filtered.indexOf(b))).join('')}}</div>`;
  }}

  if (otherBooks.length) {{
    if (readingBooks.length) {{
      html += `<p class="section-label" style="margin-top:8px">Решта книг</p>`;
    }}
    html += `<div class="book-grid">${{otherBooks.map((b, i) => cardHTML(b, _filtered.indexOf(b))).join('')}}</div>`;
  }}

  mainContent.innerHTML = html;

  // Staggered animation для перших 8 карток
  mainContent.querySelectorAll('.book-card').forEach((card, i) => {{
    card.style.animationDelay = i < 8 ? `${{i * 20}}ms` : '0ms';
  }});
}}

function openModal(idx) {{
  const b = _filtered[idx];
  if (!b) return;

  const [mbg, mfg] = coverColor(b.title);
  const mletter = (b.title || '?')[0].toUpperCase();
  const bc = badgeClass(b.status);

  const srcNotes = b.source_author_notes
    ? `<div class="notes-block"><h4>Нотатки автора джерела</h4><p>${{esc(b.source_author_notes)}}</p></div>` : '';
  const myNotes = b.my_notes
    ? `<div class="notes-block"><h4>Мої нотатки</h4><p>${{esc(b.my_notes)}}</p></div>` : '';
  const bothNotes = srcNotes && myNotes;
  const tags = (b.tags||[]).map(t=>`<span class="tag">${{esc(t)}}</span>`).join('');

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-cover-strip" style="background:${{mbg}};color:${{mfg}}">${{mletter}}</div>
    <div class="modal-header">
      <div class="modal-title">${{esc(b.title)}}</div>
      <div class="modal-author">${{esc(b.author)}}</div>
      <div class="modal-badges">
        ${{b.genre  ? `<span class="badge badge-genre">${{esc(b.genre)}}</span>` : ''}}
        ${{b.status ? `<span class="badge ${{bc}}">${{STATUS_LABEL[b.status]||b.status}}</span>` : ''}}
        ${{b.source_type ? `<span class="badge badge-source">${{SOURCE_LABEL[b.source_type]||b.source_type}}</span>` : ''}}
        ${{b.rating ? `<span class="stars">${{stars(b.rating)}}</span>` : ''}}
      </div>
    </div>
    ${{(b.date_added || b.source_url) ? `
    <div class="meta-row">
      ${{b.date_added ? `<span>додано: ${{esc(b.date_added)}}</span>` : ''}}
      ${{b.source_url ? `<a href="${{esc(b.source_url)}}" target="_blank" rel="noopener">джерело →</a>` : ''}}
    </div>` : ''}}
    ${{(srcNotes||myNotes) ? `
    <div class="notes-section">
      <div class="notes-grid ${{bothNotes ? 'two-cols' : ''}}">
        ${{srcNotes}}${{myNotes}}
      </div>
    </div>` : ''}}
    ${{tags ? `<div class="tags-section">${{tags}}</div>` : ''}}
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
