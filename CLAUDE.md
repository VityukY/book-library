# book-library

Особиста база книг. Markdown файли + YAML frontmatter.
GitHub Pages: автогенерована статична сторінка при кожному push.

## Структура
```
books/          ← одна книга = один .md файл (slug як назва)
scripts/        ← build.py: генерує site/index.html
skills/         ← get-content.md: отримання тексту з YouTube / статей
site/           ← НЕ редагувати вручну, генерується автоматично
.github/workflows/deploy.yml ← CI/CD
```

## Додати книгу
1. Створити `books/[slug].md` з YAML frontmatter (дивись README)
2. `git add . && git commit -m "add: Назва книги" && git push`
3. GitHub Actions автоматично оновлює сайт

## Поля YAML
- **Обов'язкові:** title, author, genre, status, source_type, source_url, date_added
- **Опціональні:** rating (1-5), tags, source_author_notes, my_notes

## Статуси
- `want-to-read` — хочу прочитати
- `reading` — читаю зараз
- `done` — прочитано

## Правила
- Slug = транслітерація назви, kebab-case (напр. `atomic-habits.md`)
- Мова записів — українська
- Після додавання нових edge cases у get-content.md — оновити skills/get-content.md
