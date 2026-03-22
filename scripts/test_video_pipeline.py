from __future__ import annotations

import asyncio
from pathlib import Path

from ua_news_bot.media.video_editor import add_branding_to_video_file
from ua_news_bot.media.ytdlp_downloader import download_video_with_ytdlp

VIDEO_URL = "https://www.youtube.com/embed/6dbyRUedO8g"
YTDLP_BIN = "yt-dlp"
FFMPEG_BIN = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_BIN = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
WATERMARK_TEXT = "Smart News UA"
LOGO_PATH = "data/images/smart_news_ua_logo.png"


def _normalize_video_url(url: str) -> str:
    url = url.strip()

    if "youtube.com/embed/" in url:
        video_id = url.split("youtube.com/embed/", 1)[1].split("?", 1)[0].strip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    if "youtu.be/" in url:
        video_id = url.split("youtu.be/", 1)[1].split("?", 1)[0].strip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    return url


async def main() -> None:
    if VIDEO_URL == "PASTE_VIDEO_URL_HERE":
        raise RuntimeError("Set VIDEO_URL first")

    normalized_url = _normalize_video_url(VIDEO_URL)
    print(f"Input URL:      {VIDEO_URL}")
    print(f"Normalized URL: {normalized_url}")

    print("Downloading video via yt-dlp...")
    downloaded_path = await download_video_with_ytdlp(
        normalized_url,
        ytdlp_bin=YTDLP_BIN,
    )

    branded_path: str | None = None
    try:
        print("Branding video...")
        branded_path = await add_branding_to_video_file(
            input_video_path=downloaded_path,
            watermark_text=WATERMARK_TEXT,
            logo_path=LOGO_PATH,
            ffmpeg_bin=FFMPEG_BIN,
            ffprobe_bin=FFPROBE_BIN,
        )

        out_path = Path("/tmp/smart_news_test_branded_video.mp4")
        out_path.write_bytes(Path(branded_path).read_bytes())

        print("\nDONE")
        print(f"Downloaded temp file: {downloaded_path}")
        print(f"Branded temp file:   {branded_path}")
        print(f"Copied output:       {out_path}")
        print("\nOpen it with:")
        print(f"open {out_path}")

    finally:
        Path(downloaded_path).unlink(missing_ok=True)
        if branded_path:
            Path(branded_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
