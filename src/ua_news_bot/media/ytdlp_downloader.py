from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path


async def extract_video_url_with_ytdlp(url: str, ytdlp_bin: str = "yt-dlp") -> str | None:
    process = await asyncio.create_subprocess_exec(
        ytdlp_bin,
        "--dump-single-json",
        "--no-warnings",
        "--skip-download",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"yt-dlp extract failed:\n{stderr.decode()}")

    data = json.loads(stdout.decode())

    direct_url = (data.get("url") or "").strip()
    if direct_url:
        return direct_url

    formats = data.get("formats") or []
    for fmt in reversed(formats):
        fmt_url = (fmt.get("url") or "").strip()
        ext = (fmt.get("ext") or "").lower()
        vcodec = (fmt.get("vcodec") or "").lower()
        if fmt_url and ext == "mp4" and vcodec and vcodec != "none":
            return fmt_url

    for fmt in reversed(formats):
        fmt_url = (fmt.get("url") or "").strip()
        vcodec = (fmt.get("vcodec") or "").lower()
        if fmt_url and vcodec and vcodec != "none":
            return fmt_url

    return None


async def download_video_with_ytdlp(url: str, ytdlp_bin: str = "yt-dlp") -> str:
    """
    Downloads video to a temp directory and returns the final mp4 path.
    Caller must delete the returned file.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="smart_news_ytdlp_"))

    process = await asyncio.create_subprocess_exec(
        ytdlp_bin,
        "-f",
        "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "--merge-output-format",
        "mp4",
        "-o",
        "%(id)s.%(ext)s",
        url,
        cwd=str(temp_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"yt-dlp download failed:\n{stderr.decode()}")

    candidates = sorted(
        [p for p in temp_dir.iterdir() if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("yt-dlp produced no files")

    mp4_candidates = [p for p in candidates if p.suffix.lower() == ".mp4"]
    chosen = mp4_candidates[0] if mp4_candidates else candidates[0]

    if not chosen.exists() or chosen.stat().st_size < 5000:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("yt-dlp produced invalid output video")

    final_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    final_temp.close()
    final_path = Path(final_temp.name)

    shutil.move(str(chosen), str(final_path))
    shutil.rmtree(temp_dir, ignore_errors=True)

    return str(final_path)
