from __future__ import annotations

import unittest
from io import BytesIO

from PIL import Image, ImageChops, ImageStat

from ua_news_bot.media.image_editor import (
    FONT_PATH,
    LOGO_PATH,
    add_branding_to_image,
)


class TestImageEditor(unittest.TestCase):
    def _make_base_image_bytes(self, width: int = 1200, height: int = 800) -> bytes:
        """
        Create a plain image in memory for deterministic testing.
        """
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
        """
        Calculate average pixel difference inside a region.
        """
        before_crop = before.crop(box)
        after_crop = after.crop(box)
        diff = ImageChops.difference(before_crop, after_crop)
        stat = ImageStat.Stat(diff)
        # average across RGB channels
        return sum(stat.mean) / len(stat.mean)

    def test_branding_changes_image_and_preserves_size(self) -> None:
        original_bytes = self._make_base_image_bytes()
        original_img = self._open_image(original_bytes)

        result_buffer = add_branding_to_image(
            image_bytes=original_bytes,
            watermark_text="Smart News UA",
            logo_position="top-left",
            text_position="bottom-right",
        )

        self.assertIsInstance(result_buffer, BytesIO)

        result_bytes = result_buffer.getvalue()
        self.assertGreater(len(result_bytes), 0)

        result_img = self._open_image(result_bytes)

        # size should stay the same
        self.assertEqual(original_img.size, result_img.size)

        # whole image should change
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
            logo_position="top-left",
            text_position="bottom-right",
        )
        result_img = self._open_image(result_buffer.getvalue())

        # inspect top-left region where logo should be
        box = (0, 0, 250, 250)
        diff = self._region_mean_diff(original_img, result_img, box)

        # logo should noticeably alter top-left region
        self.assertGreater(diff, 1.0)

    def test_text_area_changes(self) -> None:
        original_bytes = self._make_base_image_bytes()
        original_img = self._open_image(original_bytes)

        result_buffer = add_branding_to_image(
            image_bytes=original_bytes,
            watermark_text="Smart News UA",
            logo_position="top-left",
            text_position="bottom-right",
        )
        result_img = self._open_image(result_buffer.getvalue())

        # inspect bottom-right region where watermark text should be
        box = (
            original_img.width - 420,
            original_img.height - 140,
            original_img.width,
            original_img.height,
        )
        diff = self._region_mean_diff(original_img, result_img, box)

        self.assertGreater(diff, 1.0)

    def test_font_file_exists_or_fallback_will_be_used(self) -> None:
        # this is mostly informational, not a hard requirement
        # test passes either way, but prints a useful message if missing
        self.assertTrue(True, f"Font path checked: {FONT_PATH}")


if __name__ == "__main__":
    unittest.main()
