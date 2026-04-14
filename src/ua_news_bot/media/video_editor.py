from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Literal

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_FONT_PATH = (
    BASE_DIR / "data" / "assets" / "fonts" / "sf-pro-display" / "SFPRODISPLAYREGULAR.OTF"
)


def _escape_drawtext_text(s: str) -> str:
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def _get_logo_position(
    position: Literal["top-left", "top-right", "bottom-left", "bottom-right"],
) -> str:
    mapping = {
        "top-left": "x=20:y=20",
        "top-right": "x=W-w-20:y=20",
        "bottom-left": "x=20:y=H-h-20",
        "bottom-right": "x=W-w-20:y=H-h-20",
    }
    return mapping.get(position, "x=20:y=20")


async def _has_audio(video_path: str, ffprobe_bin: str) -> bool:
    process = await asyncio.create_subprocess_exec(
        ffprobe_bin,
        "-i",
        video_path,
        "-show_streams",
        "-select_streams",
        "a",
        "-loglevel",
        "error",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return bool(stdout.decode().strip())


async def _run_ffmpeg(command: list[str], timeout: int = 300) -> None:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{stderr.decode()}")


async def add_branding_to_video_file(
    input_video_path: str,
    watermark_text: str,
    logo_path: str,
    font_path: str | None = None,
    logo_position: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = "top-left",
    logo_opacity: float = 0.9,
    logo_scale: float = 0.08,
    text_scale: float = 0.028,
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
) -> str:
    logo_file = Path(logo_path)
    if not logo_file.exists():
        raise FileNotFoundError(f"Logo not found: {logo_file}")

    font_file = Path(font_path) if font_path else DEFAULT_FONT_PATH
    temp_output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    text = _escape_drawtext_text(watermark_text)
    logo_xy = _get_logo_position(logo_position)

    filter_complex = (
        f"[1:v]format=rgba,"
        f"colorchannelmixer=aa={logo_opacity},"
        f"scale=iw*{logo_scale}:-1[logo];"
        f"[0:v][logo]overlay={logo_xy}[tmp]"
    )

    if text:
        filter_complex += (
            f";[tmp]drawtext="
            f"fontfile='{font_file}':"
            f"text='{text}':"
            f"fontcolor=white:"
            f"fontsize=(w*{text_scale}):"
            f"box=1:"
            f"boxcolor=black@0.30:"
            f"boxborderw=6:"
            f"x=w-tw-20:"
            f"y=h-th-20[v]"
        )
    else:
        filter_complex += "[v]"

    has_audio = await _has_audio(input_video_path, ffprobe_bin)

    command = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        input_video_path,
        "-i",
        str(logo_file),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
    ]

    if has_audio:
        command += ["-map", "0:a", "-c:a", "aac", "-b:a", "128k"]
    else:
        command += ["-an"]

    command += [
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        temp_output_path,
    ]

    await _run_ffmpeg(command)

    output_path = Path(temp_output_path)
    if not output_path.exists() or output_path.stat().st_size < 5000:
        raise RuntimeError("FFmpeg produced invalid output video")

    return temp_output_path
