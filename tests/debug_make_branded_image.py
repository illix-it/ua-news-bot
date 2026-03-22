from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from ua_news_bot.media.image_editor import add_branding_to_image

out_path = Path("/tmp/smart_news_test_branded.jpg")

img = Image.new("RGB", (1200, 800), (40, 60, 90))
buf = BytesIO()
img.save(buf, format="JPEG", quality=95)

result = add_branding_to_image(
    image_bytes=buf.getvalue(),
    watermark_text="Smart News UA",
    logo_position="top-left",
    text_position="bottom-right",
)

out_path.write_bytes(result.getvalue())
print(out_path)
