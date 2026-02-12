from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model: str
    channel_language: str = "uk"


class GeminiEnhancer:
    """
    Gemini-based strict editor for Smart News formatting.

    Contract:
    - Returns "SKIP" (exact, uppercase) if content is advertising/marketing.
    - Otherwise returns Telegram HTML WITHOUT the "Джерело:" line.
    """

    def __init__(self, cfg: GeminiConfig) -> None:
        self._client = genai.Client(api_key=cfg.api_key)
        self._model = cfg.model
        self._lang = cfg.channel_language

    def _prompt(self, text: str) -> str:
        # We force an explicit template and forbid unclosed tags / truncated HTML.
        return f"""
Ти — строгий редактор новинного Telegram-каналу.

Крок 1: Оціни текст.
Якщо це реклама/маркетинг/просування — поверни РІВНО одне слово:
SKIP

Крок 2: Якщо це новина — переформатуй для публікації.

Жорсткі правила:
- Мова: {self._lang}
- ЖОДНИХ нових фактів. Не домислюй. Не змінюй причини/наслідки.
- Імена, цифри, дати, географія, цитати — зберігай точно.
- Не додавай посилання в текст (посилання додамо окремо).
- Не додавай рядок "Джерело:" (додамо окремо).
- HTML має бути валідний: якщо відкрив <b>/<i>/<u>/<blockquote>, обовʼязково закрий.
- Не обрізай слова на середині.

Формат ВИХОДУ (поверни тільки готовий текст поста, без пояснень):
1) Рядок 1: <b>Заголовок</b> + 0–1 емодзі. Довжина заголовка до 110 символів.
2) Порожній рядок.
3) 1–2 речення суті (читабельно, коротко).
4) Порожній рядок.
5) 3 буллети, кожен з нового рядка і починається з "• ".
   - Кожен буллет — окремий факт (не повторюй суть).
   - Якщо фактів мало — все одно зроби 3 буллети, але без води (коротко).

Текст для обробки:
{text}
""".strip()

    def enhance(self, raw_text: str) -> str:
        prompt = self._prompt(raw_text)

        resp = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=800,
            ),
        )

        return (resp.text or "").strip()
