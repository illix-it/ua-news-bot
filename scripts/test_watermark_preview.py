from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

from PIL import Image

from ua_news_bot.media.image_editor import add_branding_to_image
from ua_news_bot.media.video_editor import add_branding_to_video_file

LOGO_PATH = "data/images/smart_news_ua_logo.png"
TEXT = "Smart News UA"
FFMPEG_BIN = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_BIN = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"

IMAGE_CASES = [
    ("small", 0.06, 0.022),
    ("medium", 0.08, 0.028),
    ("large", 0.10, 0.034),
]

VIDEO_INPUT = "/tmp/smart_news_test_branded_video.mp4"


def make_image_preview() -> None:
    base = Image.new("RGB", (1280, 720), (55, 72, 98))
    buf = BytesIO()
    base.save(buf, format="JPEG", quality=95)
    source_bytes = buf.getvalue()

    out_dir = Path("/tmp/smart_news_watermark_preview")
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, logo_scale, text_scale in IMAGE_CASES:
        result = add_branding_to_image(
            image_bytes=source_bytes,
            watermark_text=TEXT,
            logo_path=LOGO_PATH,
            logo_scale=logo_scale,
            text_scale=text_scale,
        )
        out_path = out_dir / f"image_{name}.jpg"
        out_path.write_bytes(result.getvalue())

    print(f"Image previews: {out_dir}")


async def make_video_preview() -> None:
    input_path = Path(VIDEO_INPUT)
    if not input_path.exists():
        print(f"Video input not found, skipping video preview: {input_path}")
        return

    out_dir = Path("/tmp/smart_news_watermark_preview")
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, logo_scale, text_scale in IMAGE_CASES:
        branded_path = await add_branding_to_video_file(
            input_video_path=str(input_path),
            watermark_text=TEXT,
            logo_path=LOGO_PATH,
            logo_scale=logo_scale,
            text_scale=text_scale,
            ffmpeg_bin=FFMPEG_BIN,
            ffprobe_bin=FFPROBE_BIN,
        )
        out_path = out_dir / f"video_{name}.mp4"
        out_path.write_bytes(Path(branded_path).read_bytes())
        Path(branded_path).unlink(missing_ok=True)

    print(f"Video previews: {out_dir}")


async def main() -> None:
    make_image_preview()
    await make_video_preview()
    print("Open previews with:")
    print("open /tmp/smart_news_watermark_preview")


if __name__ == "__main__":
    asyncio.run(main())
