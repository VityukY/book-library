# 📚 Book Library

Особиста база книг. Markdown + YAML frontmatter. GitHub Pages.

## Як додати книгу

1. Створити файл `books/[slug].md` (slug = назва транслітом, kebab-case)
2. Заповнити frontmatter:

```yaml
---
title: "Назва книги"
author: "Автор"
genre: "бізнес"
status: "want-to-read"
source_type: "youtube"
source_url: "https://..."
date_added: "2026-03-16"
rating:
tags: []
---

## Нотатки автора джерела

## Мої нотатки
```

3. Зробити push — сайт оновиться автоматично.

## Поля

| Поле | Обов'язкове | Значення |
|------|-------------|----------|
| title | ✅ | назва книги |
| author | ✅ | автор |
| genre | ✅ | бізнес / психологія / саморозвиток / фантастика / інше |
| status | ✅ | want-to-read / reading / done |
| source_type | ✅ | youtube / article / personal |
| source_url | ✅ | посилання на джерело |
| date_added | ✅ | YYYY-MM-DD |
| rating | — | 1–5 (залишити порожнім якщо не читав) |
| tags | — | список тегів |

## Сайт

GitHub Pages: `https://[username].github.io/book-library/`

Налаштування після першого push:
→ Settings → Pages → Source: `gh-pages` branch

## Отримати контент із джерела

Використовуй скіл `skills/get-content.md` — Claude отримає чистий текст із YouTube відео або статті.

## Локальний перегляд

```bash
python scripts/build.py
# Відкрити site/index.html у браузері
```
