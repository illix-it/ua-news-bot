from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_FONT_PATH = (
    BASE_DIR / "data" / "assets" / "fonts" / "sf-pro-display" / "SFPRODISPLAYREGULAR.OTF"
)


def _get_position(
    img_w: int,
    img_h: int,
    obj_w: int,
    obj_h: int,
    margin: int,
    position: Literal["top-left", "top-right", "bottom-left", "bottom-right"],
) -> tuple[int, int]:
    mapping = {
        "top-left": (margin, margin),
        "top-right": (img_w - obj_w - margin, margin),
        "bottom-left": (margin, img_h - obj_h - margin),
        "bottom-right": (img_w - obj_w - margin, img_h - obj_h - margin),
    }
    return mapping.get(position, (margin, margin))


def add_branding_to_image(
    image_bytes: bytes,
    watermark_text: str,
    logo_path: str,
    font_path: str | None = None,
    logo_position: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = "top-left",
    text_position: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = "bottom-right",
    logo_opacity: float = 0.9,
    logo_scale: float = 0.08,
    text_scale: float = 0.028,
    margin: int = 20,
) -> BytesIO:
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    font_file = Path(font_path) if font_path else DEFAULT_FONT_PATH

    font_size = max(18, int(image.width * text_scale))
    try:
        font = ImageFont.truetype(str(font_file), font_size)
    except OSError:
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    text_xy = _get_position(
        image.width,
        image.height,
        text_w,
        text_h,
        margin,
        text_position,
    )

    shadow_fill = (0, 0, 0, 160)
    text_fill = (255, 255, 255, 215)
    shadow_offset = 2

    draw.text(
        (text_xy[0] + shadow_offset, text_xy[1] + shadow_offset),
        watermark_text,
        font=font,
        fill=shadow_fill,
    )
    draw.text(
        text_xy,
        watermark_text,
        font=font,
        fill=text_fill,
    )

    logo_file = Path(logo_path)
    if logo_file.exists():
        try:
            logo = Image.open(logo_file).convert("RGBA")

            logo_w = max(40, int(image.width * logo_scale))
            ratio = logo.height / logo.width
            logo_h = int(logo_w * ratio)
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

            alpha = logo.getchannel("A")
            alpha = alpha.point(lambda p: int(p * logo_opacity))
            logo.putalpha(alpha)

            logo_xy = _get_position(
                image.width,
                image.height,
                logo_w,
                logo_h,
                margin,
                logo_position,
            )

            layer.paste(logo, logo_xy, logo)
        except Exception as e:
            print(f"[IMG] logo overlay failed: {e}")

    combined = Image.alpha_composite(image, layer)

    output = BytesIO()
    combined.convert("RGB").save(output, format="JPEG", quality=95)
    output.seek(0)
    return output
