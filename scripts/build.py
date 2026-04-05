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


def escape_html(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# HTML_TEMPLATE uses __BOOKS_JSON__ and __GENRE_OPTIONS__ as placeholders
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Amber Shelf — Особиста Бібліотека</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:            #0f0d0b;
    --surface:       #1c1814;
    --surface2:      #26201a;
    --surface3:      #2a2420;
    --border:        #3a2e22;
    --border-hover:  #4a4035;
    --text:          #f0e6d3;
    --text-sec:      #b8a98a;
    --muted:         #8a7a6a;
    --accent:        #c8922a;
    --accent-soft:   #e8b96a;
    --accent-glow:   rgba(200,146,42,0.15);
    --done:          #4a7c59;
    --reading:       #c8922a;
    --want:          #4a6fa5;
    --star:          #e8b96a;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 13px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── scrollbar ── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #3a2e22; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #4a4035; }

  /* ── header ── */
  header {
    position: sticky; top: 0; z-index: 20;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    padding: 16px 32px 14px;
  }
  .header-inner {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px;
  }
  .header-left {
    display: flex; flex-direction: column; gap: 3px;
  }
  .header-brand {
    display: flex; align-items: center; gap: 10px;
  }
  header h1 {
    font-family: 'Lora', serif;
    font-size: 26px; font-weight: 700;
    color: var(--accent-soft);
    line-height: 1;
  }
  .header-icon {
    font-size: 22px; line-height: 1;
  }
  .header-subtitle {
    font-size: 12px; color: var(--muted);
    font-style: italic; font-family: 'Inter', sans-serif;
    padding-left: 2px;
  }
  .header-stats {
    font-size: 13px; color: var(--muted);
    font-family: 'Inter', sans-serif;
    white-space: nowrap; text-align: right;
  }
  .header-stats .stat-num {
    color: var(--accent-soft); font-weight: 500;
  }

  /* ── filter panel ── */
  .filter-panel {
    position: sticky; top: 77px; z-index: 19;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 32px;
    display: flex; flex-direction: column; gap: 10px;
  }

  /* search row */
  .search-wrap {
    position: relative;
  }
  .search-icon {
    position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
    pointer-events: none;
    color: var(--accent);
  }
  .search-icon svg { display: block; }
  #f-search {
    width: 100%;
    height: 42px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0 14px 0 38px;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  #f-search::placeholder { color: var(--muted); }
  #f-search:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(200,146,42,0.12);
  }

  /* selects row */
  .filters-row {
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  }
  select {
    background: var(--bg);
    color: var(--text-sec);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 28px 6px 10px;
    font-size: 12px;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%238a7a6a'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    background-size: 10px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
    flex: 1; min-width: 130px;
  }
  select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(200,146,42,0.12);
  }
  select option { background: #26201a; color: var(--text); }

  .sort-select {
    margin-left: auto;
    background: var(--surface2);
    border-color: var(--border);
    color: var(--accent-soft);
    font-weight: 500;
    min-width: 150px;
  }

  /* active filters chips */
  .active-filters {
    display: none; align-items: center; flex-wrap: wrap; gap: 6px;
    padding: 0 32px 10px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .active-filters.visible { display: flex; }
  .filter-chip {
    background: rgba(200,146,42,0.12);
    border: 1px solid rgba(200,146,42,0.25);
    color: var(--accent-soft);
    font-size: 11px; font-family: 'Inter', sans-serif;
    padding: 2px 8px; border-radius: 20px;
    cursor: pointer; transition: background 0.15s;
  }
  .filter-chip:hover { background: rgba(200,146,42,0.2); }
  .reset-btn {
    background: none; border: none;
    color: var(--muted); font-size: 11px;
    font-family: 'Inter', sans-serif;
    cursor: pointer; padding: 2px 6px;
    text-decoration: underline;
    margin-left: 4px;
  }
  .reset-btn:hover { color: var(--text); }

  /* ── main ── */
  main {
    padding: 24px 32px;
    flex: 1;
  }

  /* ── section headings ── */
  .section-heading {
    font-family: 'Lora', serif;
    font-size: 18px; font-weight: 600;
    color: var(--text);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--accent);
    display: inline-block;
  }
  .section-wrap {
    margin-bottom: 32px;
  }
  .section-count {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--muted);
    margin-left: 8px; font-weight: 400;
  }

  /* ── grid ── */
  .book-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }

  /* ── card ── */
  .book-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 3px 6px 6px 3px;
    border-left-width: 4px;
    overflow: hidden;
    cursor: pointer;
    display: flex; flex-direction: column;
    height: 260px;
    transition: transform 0.2s ease,
                box-shadow 0.2s ease,
                border-color 0.2s ease;
    animation: cardIn 0.25s ease both;
    position: relative;
  }
  .spine-done    { border-left-color: var(--done); }
  .spine-reading { border-left-color: var(--reading); box-shadow: 0 0 0 1px rgba(200,146,42,0.15); }
  .spine-want    { border-left-color: var(--want); }
  .spine-none    { border-left-color: var(--border); }

  .book-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 28px rgba(200,146,42,0.2);
  }
  .book-card.spine-done:hover    { border-left-color: var(--done); }
  .book-card.spine-reading:hover { border-left-color: var(--reading); }
  .book-card.spine-want:hover    { border-left-color: var(--want); }

  @keyframes cardIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* ── card cover ── */
  .card-cover {
    flex: 0 0 72%;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
    box-shadow: inset 0 -20px 30px rgba(0,0,0,0.4);
    transition: filter 0.18s ease;
  }
  .book-card:hover .card-cover { filter: brightness(1.08); }

  .cover-content {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 12px 10px 8px;
    text-align: center;
    flex: 1;
  }
  .cover-title {
    font-family: 'Lora', serif;
    font-size: 13px; font-weight: 600;
    color: #fff; line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .cover-author {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    color: rgba(255,255,255,0.6);
    margin-top: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .difficulty-badge {
    position: absolute; top: 6px; right: 6px;
    width: 18px; height: 18px;
    border-radius: 50%;
    font-size: 9px; font-weight: 700;
    font-family: 'Inter', sans-serif;
    display: flex; align-items: center; justify-content: center;
    z-index: 1;
  }

  .genre-dot {
    position: absolute; bottom: 8px; right: 8px;
    width: 7px; height: 7px; border-radius: 50%;
    opacity: 0.7; transition: opacity 0.15s, transform 0.15s;
  }
  .book-card:hover .genre-dot { opacity: 1; transform: scale(1.3); }

  /* ── card body (bottom 28%) ── */
  .card-body {
    flex: 0 0 28%;
    background: var(--surface);
    padding: 8px 10px;
    display: flex; flex-direction: column; gap: 4px;
    border-top: 1px solid var(--surface3);
  }
  .card-footer {
    display: flex; align-items: center;
    justify-content: space-between; flex-wrap: wrap; gap: 4px;
    margin-top: auto;
  }
  .badge {
    font-size: 10px; padding: 2px 7px;
    border-radius: 4px; font-weight: 500;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.02em; white-space: nowrap;
  }
  .badge-done    { background: rgba(74,124,89,0.15);  color: var(--done);    border: 1px solid rgba(74,124,89,0.25); }
  .badge-reading { background: rgba(200,146,42,0.15); color: var(--reading); border: 1px solid rgba(200,146,42,0.25); }
  .badge-want    { background: rgba(74,111,165,0.15); color: var(--want);    border: 1px solid rgba(74,111,165,0.25); }
  .badge-genre   { background: rgba(200,146,42,0.08); color: var(--accent);  border: 1px solid rgba(200,146,42,0.15); }
  .badge-source  { background: var(--surface3); color: var(--muted); border: 1px solid var(--border); }
  .stars { color: var(--star); font-size: 10px; letter-spacing: 1px; }

  /* reading section — featured amber glow */
  .section-reading .book-card.spine-reading {
    box-shadow: 0 4px 16px rgba(200,146,42,0.15);
  }
  .section-reading .book-card.spine-reading:hover {
    box-shadow: 0 8px 28px rgba(200,146,42,0.3);
  }

  /* ── modal ── */
  .overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(10,8,6,0.82);
    backdrop-filter: blur(4px);
    z-index: 100; align-items: center; justify-content: center;
    padding: 1rem;
  }
  .overlay.open { display: flex; animation: overlayIn 0.2s ease; }
  @keyframes overlayIn { from { opacity: 0; } to { opacity: 1; } }

  .modal {
    background: #1e1a14;
    border: 1px solid #3a3025;
    border-radius: 14px;
    max-width: 660px; width: 100%;
    max-height: 88vh; overflow-y: auto;
    padding: 0; position: relative;
    box-shadow: 0 24px 64px rgba(0,0,0,0.7),
                0 0 0 1px rgba(200,146,42,0.06);
    animation: modalIn 0.22s cubic-bezier(0.25,0.46,0.45,0.94);
  }
  @keyframes modalIn {
    from { opacity: 0; transform: translateY(12px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }
  .modal::-webkit-scrollbar { width: 4px; }
  .modal::-webkit-scrollbar-track { background: transparent; }
  .modal::-webkit-scrollbar-thumb { background: #3a3025; border-radius: 2px; }
  .modal::-webkit-scrollbar-thumb:hover { background: #4a4035; }

  .modal-close {
    position: absolute; top: 12px; right: 14px;
    width: 28px; height: 28px;
    background: rgba(0,0,0,0.4);
    border: 1px solid #3a3025; border-radius: 50%;
    color: var(--muted); font-size: 13px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; z-index: 2;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }
  .modal-close:hover {
    background: rgba(200,146,42,0.15);
    color: var(--text); border-color: rgba(200,146,42,0.4);
  }

  .modal-cover-strip {
    height: 80px; border-radius: 14px 14px 0 0;
    display: flex; align-items: center; justify-content: center;
    position: relative; overflow: hidden;
    box-shadow: inset 0 -30px 40px rgba(0,0,0,0.5);
    flex-shrink: 0;
  }
  .modal-cover-title {
    font-family: 'Lora', serif;
    font-size: 22px; font-weight: 700;
    color: var(--text); text-align: center;
    padding: 0 60px 0 16px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.6);
  }
  .modal-cover-author {
    font-family: 'Inter', sans-serif;
    font-size: 13px; color: var(--accent-soft);
    margin-top: 4px; text-align: center;
    text-shadow: 0 1px 4px rgba(0,0,0,0.5);
  }
  .modal-cover-inner {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    width: 100%; height: 100%;
    padding: 12px;
  }

  .modal-header { padding: 16px 20px 14px; border-bottom: 1px solid #302a22; }
  .modal-title {
    font-family: 'Lora', serif;
    font-size: 18px; font-weight: 600; color: var(--text);
    margin-bottom: 4px; padding-right: 32px;
  }
  .modal-author {
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    color: var(--accent-soft); margin-bottom: 10px;
  }
  .modal-badges {
    display: flex; flex-wrap: wrap; gap: 6px;
  }

  .meta-row {
    padding: 12px 20px;
    display: flex; flex-wrap: wrap; gap: 12px;
    font-size: 11px; color: var(--muted);
    border-bottom: 1px solid #302a22;
  }
  .meta-row a { color: var(--accent); text-decoration: none; }
  .meta-row a:hover { text-decoration: underline; }

  .notes-section { padding: 16px 20px; }
  .notes-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; position: relative;
  }
  @media (max-width: 480px) {
    .notes-grid { grid-template-columns: 1fr; }
    .notes-grid::before { display: none; }
  }
  .notes-grid.two-cols::before {
    content: ''; position: absolute;
    left: 50%; top: 0; bottom: 0;
    width: 1px; background: #302a22;
    transform: translateX(-50%);
  }
  .notes-block h4 {
    font-family: 'Inter', sans-serif;
    font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted);
    margin-bottom: 8px;
    padding-bottom: 6px; border-bottom: 1px solid #302a22;
  }
  .notes-block p {
    font-size: 12.5px; color: #c8b898;
    white-space: pre-wrap; line-height: 1.65;
  }

  .tags-section { padding: 0 20px 16px; display: flex; flex-wrap: wrap; gap: 6px; }
  .tag {
    background: #252018; color: var(--muted);
    border: 1px solid #302a22;
    font-size: 10.5px; padding: 2px 8px; border-radius: 4px;
    font-family: 'Inter', sans-serif;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    cursor: default;
  }
  .tag:hover {
    background: #2f2818; color: var(--text-sec);
    border-color: rgba(200,146,42,0.3);
  }

  .empty {
    color: var(--muted); padding: 3rem 2rem;
    font-size: 14px; text-align: center;
  }

  /* ── footer ── */
  footer {
    background: #0a0806;
    border-top: 1px solid #2a2018;
    padding: 20px 32px;
    display: flex; align-items: center;
    justify-content: space-between; gap: 16px;
    flex-wrap: wrap;
  }
  .footer-left .footer-brand {
    font-family: 'Lora', serif;
    font-size: 14px; color: var(--accent-soft);
    font-weight: 600;
  }
  .footer-left .footer-tagline {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--muted);
    margin-top: 2px;
  }
  .footer-center {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--muted);
    text-align: center;
    display: flex; gap: 16px; flex-wrap: wrap; justify-content: center;
  }
  .footer-center .fn { color: var(--accent-soft); font-weight: 500; }
  .footer-right {
    font-family: 'Inter', sans-serif;
    font-size: 12px; color: var(--muted);
    text-align: right;
  }

  /* ── responsive ── */
  @media (max-width: 768px) {
    header { padding: 14px 16px 12px; }
    .filter-panel { padding: 10px 16px; top: 68px; }
    .active-filters { padding: 0 16px 10px; }
    main { padding: 16px; }
    footer { padding: 16px; flex-direction: column; text-align: center; }
    .footer-right { text-align: center; }
    .book-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }
    .book-card { height: 220px; }
    .cover-title { font-size: 11px; }
    .header-stats { display: none; }
    .filters-row { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 2px; }
    .filters-row select { min-width: 110px; flex: 0 0 auto; }
    .sort-select { min-width: 130px; }
    .modal {
      max-height: 90vh;
      border-radius: 14px 14px 0 0;
      margin-top: auto;
      align-self: flex-end;
    }
  }

  @media (min-width: 1400px) {
    .book-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
    .modal { max-width: 720px; }
  }
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="header-left">
      <div class="header-brand">
        <span class="header-icon">&#x1F4D6;</span>
        <h1>Amber Shelf</h1>
      </div>
      <span class="header-subtitle">особиста бібліотека</span>
    </div>
    <div class="header-stats" id="header-stats">
      завантаження...
    </div>
  </div>
</header>

<div class="filter-panel">
  <div class="search-wrap">
    <span class="search-icon">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6.5" cy="6.5" r="4.5" stroke="#c8922a" stroke-width="1.5"/>
        <path d="M10 10L14 14" stroke="#c8922a" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </span>
    <input type="search" id="f-search" oninput="onSearch()" placeholder="Шукати за назвою або автором...">
  </div>
  <div class="filters-row">
    <select id="f-status" onchange="render()">
      <option value="">Всі статуси</option>
      <option value="reading">Читаю</option>
      <option value="want-to-read">Хочу прочитати</option>
      <option value="done">Прочитано</option>
    </select>
    <select id="f-genre" onchange="render()">
      <option value="">Всі жанри</option>
      __GENRE_OPTIONS__
    </select>
    <select id="f-difficulty" onchange="render()">
      <option value="">Будь-яка складність</option>
      <option value="beginner">Beginner</option>
      <option value="intermediate">Intermediate</option>
      <option value="advanced">Advanced</option>
    </select>
    <select id="f-rating" onchange="render()">
      <option value="">Будь-який рейтинг</option>
      <option value="5">&#9733;&#9733;&#9733;&#9733;&#9733;</option>
      <option value="4">&#9733;&#9733;&#9733;&#9733;+</option>
      <option value="3">&#9733;&#9733;&#9733;+</option>
    </select>
    <select id="f-sort" onchange="render()" class="sort-select">
      <option value="">За замовчуванням</option>
      <option value="title-asc">Назва A&#8211;Z</option>
      <option value="title-desc">Назва Z&#8211;A</option>
      <option value="rating-desc">Рейтинг &#8595;</option>
    </select>
  </div>
</div>

<div class="active-filters" id="active-filters"></div>

<main>
  <div id="main-content"></div>
</main>

<footer>
  <div class="footer-left">
    <div class="footer-brand">&#x1F4D6; Amber Shelf</div>
    <div class="footer-tagline">особиста бібліотека</div>
  </div>
  <div class="footer-center" id="footer-stats">
    завантаження...
  </div>
  <div class="footer-right" id="footer-date">
    Оновлено: квітень 2026
  </div>
</footer>

<!-- модалка -->
<div class="overlay" id="overlay" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <button class="modal-close" onclick="closeModal()">&#x2715;</button>
    <div id="modal-content"></div>
  </div>
</div>

<script>
const BOOKS = __BOOKS_JSON__;

const STATUS_LABEL = { done:'Прочитано', reading:'Читаю', 'want-to-read':'Хочу прочитати' };
const SOURCE_LABEL = { youtube:'YouTube', article:'Стаття', personal:'Особисте' };
const SOURCE_ICON  = { youtube:'▶', article:'◉', personal:'◆' };

// Genre-specific cover gradients
const GENRE_GRADIENTS = {
  'fantasy':      ['#1a1035', '#3a1a6e'],
  'sci-fi':       ['#0a1a2a', '#1a4060'],
  'саморозвиток': ['#0a1a10', '#1a4028'],
  'horror':       ['#1a0808', '#4a1010'],
  'romance':      ['#2a0a1a', '#5a1a3a'],
  'thriller':     ['#1a1010', '#3a2010'],
  'historical':   ['#1a1508', '#3a2e10'],
  'literary':     ['#0a0f1a', '#1a253a'],
};

const GENRE_COLORS = {
  'fantasy':      '#9b6bcf',
  'sci-fi':       '#4acfcf',
  'саморозвиток': '#4acf8a',
  'romance':      '#cf4a9b',
  'thriller':     '#cf4a4a',
  'horror':       '#cf6a2a',
  'historical':   '#8a6320',
  'literary':     '#4a7fcf',
};

const DIFFICULTY_LABEL = { beginner: 'B', intermediate: 'I', advanced: 'A' };
const DIFFICULTY_COLOR = { beginner: '#4a7c59', intermediate: '#c8922a', advanced: '#8a3030' };

function getDifficulty(tags) {
  if (!tags || !tags.length) return null;
  if (tags.includes('beginner'))     return 'beginner';
  if (tags.includes('intermediate')) return 'intermediate';
  if (tags.includes('advanced'))     return 'advanced';
  return null;
}

function genreDotColor(genre) {
  return GENRE_COLORS[(genre||'').toLowerCase()] || '#6b5c45';
}

function genreGradient(genre) {
  const g = GENRE_GRADIENTS[(genre||'').toLowerCase()];
  return g || ['#1a1508', '#2a2018'];
}

function coverColor(title) {
  const COVER_COLORS = [
    ['#1a2a4a','#4a7fcf'],['#2a1a3a','#9b6bcf'],['#1a3a2a','#4acf8a'],
    ['#3a2a1a','#cf8a4a'],['#2a1a1a','#cf4a4a'],['#1a2a3a','#4acfcf'],
    ['#2a3a1a','#9bcf4a'],['#3a1a2a','#cf4a9b'],
  ];
  let h = 0;
  for (let c of (title||'')) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return COVER_COLORS[h % COVER_COLORS.length];
}

function spineClass(status) {
  return {done:'spine-done', reading:'spine-reading','want-to-read':'spine-want'}[status] || 'spine-none';
}

function badgeClass(status) {
  return {done:'badge-done', reading:'badge-reading','want-to-read':'badge-want'}[status] || '';
}

function stars(r) { return r ? '★'.repeat(r)+'☆'.repeat(5-r) : ''; }

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function cardHTML(b, idx) {
  const [bg1, bg2] = genreGradient(b.genre);
  const sc = spineClass(b.status);
  const bc = badgeClass(b.status);
  const sl = STATUS_LABEL[b.status] || b.status;
  const dotColor = genreDotColor(b.genre);
  const diff = getDifficulty(b.tags);

  const diffBadge = diff
    ? `<span class="difficulty-badge" style="background:${DIFFICULTY_COLOR[diff]};color:#fff" title="${diff}">${DIFFICULTY_LABEL[diff]}</span>`
    : '';

  return `
  <div class="book-card ${sc}" onclick="openModal(${idx})">
    <div class="card-cover" style="background:linear-gradient(160deg,${bg1},${bg2})">
      ${diffBadge}
      <div class="cover-content">
        <div class="cover-title">${esc(b.title)}</div>
        <div class="cover-author">${esc(b.author)}</div>
      </div>
      <span class="genre-dot" style="background:${dotColor}"></span>
    </div>
    <div class="card-body">
      <div class="card-footer">
        ${b.genre ? `<span class="badge badge-genre">${esc(b.genre)}</span>` : ''}
        ${b.rating ? `<span class="stars">${stars(b.rating)}</span>` : (b.status ? `<span class="badge ${bc}">${sl}</span>` : '')}
      </div>
    </div>
  </div>`;
}

let _filtered = [];
let _searchTimeout;

function onSearch() {
  clearTimeout(_searchTimeout);
  _searchTimeout = setTimeout(render, 200);
}

function resetFilters() {
  document.getElementById('f-search').value = '';
  document.getElementById('f-status').value = '';
  document.getElementById('f-genre').value = '';
  document.getElementById('f-difficulty').value = '';
  document.getElementById('f-rating').value = '';
  document.getElementById('f-sort').value = '';
  render();
}

function updateHeaderStats() {
  const total   = BOOKS.length;
  const done    = BOOKS.filter(b => b.status === 'done').length;
  const reading = BOOKS.filter(b => b.status === 'reading').length;
  const want    = BOOKS.filter(b => b.status === 'want-to-read').length;

  document.getElementById('header-stats').innerHTML =
    `<span class="stat-num">${total}</span> книг · <span class="stat-num">${done}</span> прочитано · <span class="stat-num">${reading}</span> у процесі`;

  document.getElementById('footer-stats').innerHTML =
    `<span>📚 <span class="fn">${total}</span> книг</span>` +
    `<span>✓ <span class="fn">${done}</span> прочитано</span>` +
    `<span>◉ <span class="fn">${reading}</span> у процесі</span>` +
    `<span>○ <span class="fn">${want}</span> у списку</span>`;
}

function updateActiveFilters(status, genre, diff, minR, search) {
  const chips = [];
  if (search)  chips.push({ label: `Пошук: "${search}"`, key: 'search' });
  if (status)  chips.push({ label: STATUS_LABEL[status] || status, key: 'status' });
  if (genre)   chips.push({ label: genre, key: 'genre' });
  if (diff)    chips.push({ label: diff, key: 'difficulty' });
  if (minR)    chips.push({ label: '★'.repeat(minR) + '+', key: 'rating' });

  const el = document.getElementById('active-filters');
  if (!chips.length) {
    el.classList.remove('visible');
    el.innerHTML = '';
    return;
  }
  el.classList.add('visible');
  el.innerHTML = chips.map(c =>
    `<span class="filter-chip" onclick="clearFilter('${c.key}')">× ${esc(c.label)}</span>`
  ).join('') + `<button class="reset-btn" onclick="resetFilters()">Скинути все</button>`;
}

function clearFilter(key) {
  if (key === 'search')     document.getElementById('f-search').value = '';
  if (key === 'status')     document.getElementById('f-status').value = '';
  if (key === 'genre')      document.getElementById('f-genre').value = '';
  if (key === 'difficulty') document.getElementById('f-difficulty').value = '';
  if (key === 'rating')     document.getElementById('f-rating').value = '';
  render();
}

function render() {
  const status = document.getElementById('f-status').value;
  const genre  = document.getElementById('f-genre').value;
  const diff   = document.getElementById('f-difficulty').value;
  const minR   = parseInt(document.getElementById('f-rating').value) || 0;
  const search = (document.getElementById('f-search').value || '').toLowerCase().trim();
  const sortVal = document.getElementById('f-sort').value;

  _filtered = BOOKS.filter(b =>
    (!status || b.status === status) &&
    (!genre  || b.genre  === genre)  &&
    (!minR   || (b.rating && b.rating >= minR)) &&
    (!diff   || getDifficulty(b.tags) === diff) &&
    (!search || b.title.toLowerCase().includes(search) || b.author.toLowerCase().includes(search))
  );

  // Sorting
  if (sortVal === 'title-asc')        _filtered.sort((a,b) => a.title.localeCompare(b.title));
  else if (sortVal === 'title-desc')  _filtered.sort((a,b) => b.title.localeCompare(a.title));
  else if (sortVal === 'rating-desc') _filtered.sort((a,b) => (b.rating||0) - (a.rating||0));

  updateActiveFilters(status, genre, diff, minR, search);

  const mainContent = document.getElementById('main-content');
  if (!_filtered.length) {
    mainContent.innerHTML = '<p class="empty">Нічого не знайдено. Спробуйте змінити фільтри.</p>';
    return;
  }

  // Sections by status (only when no status filter applied)
  const readingBooks = !status ? _filtered.filter(b => b.status === 'reading') : [];
  const wantBooks    = !status ? _filtered.filter(b => b.status === 'want-to-read') : [];
  const doneBooks    = !status ? _filtered.filter(b => b.status === 'done') : [];
  const showSections = !status;

  let html = '';

  if (showSections) {
    if (readingBooks.length) {
      html += `<div class="section-wrap section-reading">
        <div><span class="section-heading">Читаю зараз</span><span class="section-count">${readingBooks.length}</span></div>
        <div class="book-grid">${readingBooks.map(b => cardHTML(b, _filtered.indexOf(b))).join('')}</div>
      </div>`;
    }
    if (wantBooks.length) {
      html += `<div class="section-wrap">
        <div><span class="section-heading">Хочу прочитати</span><span class="section-count">${wantBooks.length}</span></div>
        <div class="book-grid">${wantBooks.map(b => cardHTML(b, _filtered.indexOf(b))).join('')}</div>
      </div>`;
    }
    if (doneBooks.length) {
      html += `<div class="section-wrap">
        <div><span class="section-heading">Прочитано</span><span class="section-count">${doneBooks.length}</span></div>
        <div class="book-grid">${doneBooks.map(b => cardHTML(b, _filtered.indexOf(b))).join('')}</div>
      </div>`;
    }
  } else {
    html += `<div class="book-grid">${_filtered.map((b, i) => cardHTML(b, i)).join('')}</div>`;
  }

  mainContent.innerHTML = html;

  // Staggered animation for first 12 cards
  mainContent.querySelectorAll('.book-card').forEach((card, i) => {
    card.style.animationDelay = i < 12 ? `${i * 18}ms` : '0ms';
  });
}

function openModal(idx) {
  const b = _filtered[idx];
  if (!b) return;

  const [bg1, bg2] = genreGradient(b.genre);
  const bc = badgeClass(b.status);
  const diff = getDifficulty(b.tags);

  const srcNotes = b.source_author_notes
    ? `<div class="notes-block"><h4>Нотатки автора джерела</h4><p>${esc(b.source_author_notes)}</p></div>` : '';
  const myNotes = b.my_notes
    ? `<div class="notes-block"><h4>Мої нотатки</h4><p>${esc(b.my_notes)}</p></div>` : '';
  const bothNotes = srcNotes && myNotes;
  const tags = (b.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('');

  const diffBadge = diff
    ? `<span class="badge" style="background:${DIFFICULTY_COLOR[diff]}22;color:${DIFFICULTY_COLOR[diff]};border:1px solid ${DIFFICULTY_COLOR[diff]}44">${diff}</span>`
    : '';

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-cover-strip" style="background:linear-gradient(160deg,${bg1},${bg2})">
      <div class="modal-cover-inner">
        <div class="modal-cover-title">${esc(b.title)}</div>
        <div class="modal-cover-author">${esc(b.author)}</div>
      </div>
    </div>
    <div class="modal-header">
      <div class="modal-title">${esc(b.title)}</div>
      <div class="modal-author">${esc(b.author)}</div>
      <div class="modal-badges">
        ${b.genre  ? `<span class="badge badge-genre">${esc(b.genre)}</span>` : ''}
        ${b.status ? `<span class="badge ${bc}">${STATUS_LABEL[b.status]||b.status}</span>` : ''}
        ${diffBadge}
        ${b.source_type ? `<span class="badge badge-source">${SOURCE_LABEL[b.source_type]||b.source_type}</span>` : ''}
        ${b.rating ? `<span class="stars">${stars(b.rating)}</span>` : ''}
      </div>
    </div>
    ${(b.date_added || b.source_url) ? `
    <div class="meta-row">
      ${b.date_added ? `<span>додано: ${esc(b.date_added)}</span>` : ''}
      ${b.source_url ? `<a href="${esc(b.source_url)}" target="_blank" rel="noopener">джерело →</a>` : ''}
    </div>` : ''}
    ${(srcNotes||myNotes) ? `
    <div class="notes-section">
      <div class="notes-grid ${bothNotes ? 'two-cols' : ''}">
        ${srcNotes}${myNotes}
      </div>
    </div>` : ''}
    ${tags ? `<div class="tags-section">${tags}</div>` : ''}
  `;
  document.getElementById('overlay').classList.add('open');
}

function closeModal(e) {
  if (!e || e.target === document.getElementById('overlay') || e.target.classList.contains('modal-close')) {
    document.getElementById('overlay').classList.remove('open');
  }
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal({target: document.getElementById('overlay')});
});

updateHeaderStats();
render();
</script>
</body>
</html>"""


def render_html(books: list[dict]) -> str:
    books_json = json.dumps(books, ensure_ascii=False)
    genres = sorted(set(b.get("genre", "") for b in books if b.get("genre")))
    genre_opts = ''.join(
        f'<option value="{escape_html(g)}">{escape_html(g)}</option>'
        for g in genres
    )
    return (
        HTML_TEMPLATE
        .replace('__BOOKS_JSON__', books_json)
        .replace('__GENRE_OPTIONS__', genre_opts)
    )


def main():
    books = load_books()
    SITE_DIR.mkdir(exist_ok=True)
    html = render_html(books)
    out = SITE_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Побудовано: {out} ({len(books)} книг)")


if __name__ == "__main__":
    main()
