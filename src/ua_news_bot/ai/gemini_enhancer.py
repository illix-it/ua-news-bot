from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class GeminiConfig:
    api_keys: list[str]
    model: str
    channel_language: str = "uk"


class GeminiEnhancer:
    """
    Gemini editor via direct REST API.

    Main path:
    raw RSS text -> Gemini -> ready HTML post body/title for Telegram

    We do not add source line here.
    """

    def __init__(self, cfg: GeminiConfig) -> None:
        self._api_keys = [k.strip() for k in cfg.api_keys if k.strip()]
        self._model = cfg.model
        self._lang = cfg.channel_language

        if not self._api_keys:
            raise ValueError("GeminiEnhancer requires at least one API key")

    def _build_prompt(self, text: str) -> str:
        return f"""
Ти працюєш як строгий редактор новинного Telegram-каналу Smart News.

Спочатку проаналізуй текст.
Якщо це <b>реклама, просування товарів/послуг, маркетинг або акція</b>, поверни лише одне слово:
SKIP

Якщо текст не є рекламою — твоє завдання:
<u>перетворити його на короткий, точний і читабельний пост для публікації</u> у стилі Smart News.

🔄 Основне завдання:
- Перефразуй текст акуратно, зберігаючи зміст.
- Зроби текст простішим, зрозумілішим і легшим для читання.
- Дозволено змінювати структуру речень і абзаців, якщо це покращує читабельність.
- Не скорочуй зміст настільки, щоб губилися важливі факти.
- Переклади весь текст на {self._lang}.

⚖️ Правила точності:
- Факти, дати, цифри, імена та географічні назви <b>не змінюються</b>.
- Якщо в оригіналі є помилка, <b>не виправляй її</b>.
- Не вигадуй нових фактів і не прибирай важливі факти.

🚫 Жорсткі заборони:
- Не додавай власних висновків, оцінок чи коментарів.
- Не додавай рекламних формулювань, кліше чи емоційних прикрас.
- Не згадуй ЗМІ, Telegram-канали або бренди, якщо це не є частиною факту новини.
- Використовуй лише HTML-теги для форматування: <b>, <i>, <u>, <blockquote>, <tg-spoiler>.
- Ніколи не використовуй Markdown.
- Максимальна довжина тексту — 1024 символи.
- Не роби подвійних пробілів.

📌 Заголовок:
- Заголовок завжди став окремим першим рядком.
- Заголовок завжди оформлюй у <b>...</b>.
- Можна додати 0–1 доречне емодзі.
- Довжина заголовка: 5–9 слів.
- Заголовок має бути чітким, сильним і строго за фактами.
- Не повторюй дослівно перший абзац.

📌 Основний текст:
- Текст має бути <b>структурованим, коротким і зрозумілим</b>.
- Розбивай текст на акуратні абзаци по 1–3 речення.
- Якщо є цитата в лапках, дозволено винести її в окремий абзац через <blockquote>...</blockquote>.
- Зберігай простоту, логіку і легкість читання.

📌 Форматування:
- <b>...</b> — для ключових фактів, рішень, подій, цифр.
- <i>...</i> — для уточнень або деталей.
- <u>...</u> — для офіційних назв, термінів або формулювань.
- <blockquote>...</blockquote> — лише для прямих цитат, якщо вони є в оригінальному тексті.
- <tg-spoiler>...</tg-spoiler> — тільки за потреби цензурування.

⚠️ Правила для цитат:
- Якщо в оригіналі є пряма цитата в лапках, збережи її зміст точно.
- За потреби переклади її на мову каналу ({self._lang}).
- Не скорочуй і не розширюй цитату без причини.

📌 Стиль:
- Абзаци короткі.
- Текст має читатися легко і природно.
- Емодзі — максимум 1–2 на весь текст і тільки якщо вони доречні.

📌 Очищення:
- Повністю прибирай веб-посилання.
- Прибирай заклики підписатися, переслати, поділитися, підтримати.
- Прибирай рекламні або підписні згадки каналів, ЗМІ чи брендів.
- Усе інше зберігай.

ВАЖЛИВО:
- Не додавай рядок "Джерело:".
- Поверни лише готовий HTML-текст поста для Telegram.

---

Текст для обробки:
{text}
""".strip()

    def _call_once(self, prompt: str, api_key: str) -> str:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt,
                            }
                        ]
                    }
                ]
            },
            timeout=30,
        )

        data: dict[str, Any] = resp.json()

        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {data}")

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"No candidates in response: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError(f"No parts in first candidate: {data}")

        text = (parts[0].get("text") or "").strip()
        if not text:
            raise RuntimeError(f"Empty text in first part: {data}")

        return text

    def enhance(self, text: str) -> str:
        prompt = self._build_prompt(text)
        last_error: str | None = None

        for key in self._api_keys:
            try:
                result = self._call_once(prompt, key)
                if result.upper() == "SKIP":
                    return "SKIP"
                return result
            except Exception as e:
                last_error = repr(e)
                continue

        raise RuntimeError(f"All Gemini REST keys failed. Last error: {last_error}")
