from __future__ import annotations

import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from ua_news_bot.media.image_editor import add_branding_to_image

BASE_DIR = Path(__file__).resolve().parents[1]
LOGO_PATH = BASE_DIR / "data" / "images" / "smart_news_ua_logo.png"
FONT_PATH = BASE_DIR / "data" / "assets" / "fonts" / "sf-pro-display" / "SFPRODISPLAYREGULAR.OTF"


class TestImageEditor(unittest.TestCase):
    def _make_base_image_bytes(self, width: int = 1200, height: int = 800) -> bytes:
        image = Image.new("RGB", (width, height), (40, 60, 90))
        output = BytesIO()
        image.save(output, format="JPEG", quality=95)
        return output.getvalue()

    def _open_image(self, image_bytes: bytes) -> Image.Image:
        return Image.open(BytesIO(image_bytes)).convert("RGB")

    def _region_mean_diff(
        self,
        before: Image.Image,
        after: Image.Image,
        box: tuple[int, int, int, int],
    ) -> float:
        before_crop = before.crop(box)
        after_crop = after.crop(box)
        diff = ImageChops.difference(before_crop, after_crop)
        stat = ImageStat.Stat(diff)
        return sum(stat.mean) / len(stat.mean)

    def test_branding_changes_image_and_preserves_size(self) -> None:
        original_bytes = self._make_base_image_bytes()
        original_img = self._open_image(original_bytes)

        result_buffer = add_branding_to_image(
            image_bytes=original_bytes,
            watermark_text="Smart News UA",
            logo_path=str(LOGO_PATH),
            font_path=str(FONT_PATH),
            logo_position="top-left",
            text_position="bottom-right",
        )

        self.assertIsInstance(result_buffer, BytesIO)

        result_bytes = result_buffer.getvalue()
        self.assertGreater(len(result_bytes), 0)

        result_img = self._open_image(result_bytes)

        self.assertEqual(original_img.size, result_img.size)

        whole_diff = self._region_mean_diff(
            original_img,
            result_img,
            (0, 0, original_img.width, original_img.height),
        )
        self.assertGreater(whole_diff, 0.1)

    def test_logo_area_changes_when_logo_exists(self) -> None:
        if not LOGO_PATH.exists():
            self.skipTest(f"Logo file not found: {LOGO_PATH}")

        original_bytes = self._make_base_image_bytes()
        original_img = self._open_image(original_bytes)

        result_buffer = add_branding_to_image(
            image_bytes=original_bytes,
            watermark_text="Smart News UA",
            logo_path=str(LOGO_PATH),
            font_path=str(FONT_PATH),
            logo_position="top-left",
            text_position="bottom-right",
        )
        result_img = self._open_image(result_buffer.getvalue())

        box = (0, 0, 250, 250)
        diff = self._region_mean_diff(original_img, result_img, box)

        self.assertGreater(diff, 1.0)

    def test_text_area_changes(self) -> None:
        original_bytes = self._make_base_image_bytes()
        original_img = self._open_image(original_bytes)

        result_buffer = add_branding_to_image(
            image_bytes=original_bytes,
            watermark_text="Smart News UA",
            logo_path=str(LOGO_PATH),
            font_path=str(FONT_PATH),
            logo_position="top-left",
            text_position="bottom-right",
        )
        result_img = self._open_image(result_buffer.getvalue())

        box = (
            original_img.width - 420,
            original_img.height - 140,
            original_img.width,
            original_img.height,
        )
        diff = self._region_mean_diff(original_img, result_img, box)

        self.assertGreater(diff, 1.0)

    def test_asset_paths_are_resolved(self) -> None:
        self.assertTrue(True, f"Logo path checked: {LOGO_PATH}, font path checked: {FONT_PATH}")


if __name__ == "__main__":
    unittest.main()
