# book-library

Особиста база книг. Markdown файли + YAML frontmatter.
GitHub Pages: автогенерована статична сторінка при кожному push.

## Структура
```
books/          ← одна книга = один .md файл (slug як назва)
scripts/        ← build.py: генерує site/index.html
skills/         ← get-content.md: отримання тексту з YouTube / статей
site/           ← НЕ редагувати вручну, генерується build.py
.github/workflows/deploy.yml ← CI/CD → GitHub Pages
```

## Флоу: додати книги з YouTube відео

1. Юзер дає URL відео
2. Запустити скіл `youtube-transcribe` з URL → отримати транскрипцію
3. Проаналізувати текст → виділити всі згадані книги/серії
4. Для кожної книги — створити `books/[slug].md` з YAML + нотатками
5. `git add books/ && git commit -m "add: ..." && git push`
6. GitHub Actions автоматично оновлює сайт (~1 хв)

## Флоу: додати книгу вручну (назва/автор)

1. Юзер називає книгу
2. Створити `books/[slug].md` з відомими полями, `source_type: "personal"`
3. `git add . && git commit -m "add: Назва" && git push`

## Флоу: додати книгу зі статті

1. Юзер дає URL статті
2. `WebFetch` → витягти текст (fallback: Playwright)
3. Виділити книги → створити `.md` файли → push

## Поля YAML
- **Обов'язкові:** title, author, genre, status, source_type, source_url, date_added
- **Опціональні:** rating (1-5), tags, source_author_notes, my_notes

## Статуси
- `want-to-read` — хочу прочитати
- `reading` — читаю зараз
- `done` — прочитано

## Правила
- Slug = kebab-case назви латиницею (напр. `atomic-habits.md`)
- Мова записів — українська
- `source_author_notes` — думки автора джерела (відео/статті)
- `my_notes` — власні думки юзера, не змішувати
- Після оновлення скілу — записати нові edge cases в `skills/get-content.md`
