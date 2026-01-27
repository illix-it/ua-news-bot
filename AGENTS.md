# Codex/Agent instructions for ua-news-bot

## Project goals
- Telegram bot posts Ukrainian political news summaries.
- Sources: Ukrinform + Suspilne (RSS/site). No Telethon/userbot.
- Always include source name + link.
- No new facts or speculation. Preserve names/numbers/dates/quotes exactly.

## Tech stack
- Python 3.12+, uv
- httpx, feedparser
- ruff (format + lint), optional mypy
- Pillow watermark (images), ffmpeg watermark (video)

## Code style
- Keep modules small and composable.
- Prefer pure functions where possible.
- Add type hints to public functions.
- Run: `uv run ruff check .` and `uv run ruff format .` before finalizing changes.

## Safety/Content rules
- Summaries must be factual, neutral, and limited to the source.
- Always output: title <= 110 chars, 1–2 sentences, 3 bullets, and "Джерело: ... <link>"
- Total length 500–900 chars.

## Git hygiene
- Small commits, conventional commits.
- Update README/.env.example when adding new env vars.

## Agent behavior constraints
- Do not claim files, configuration, or tooling exist unless they are explicitly present in this repository.
- Do not introduce new architecture or refactors unless explicitly requested.
- Prefer read-only analysis unless asked to modify code.
