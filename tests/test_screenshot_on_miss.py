"""ScreenshotOnMissPlugin: safe file names, and a failed save is reported
(security review, 2026-10-09: names came straight from the query, so a
colour like '#ff00ff' or text with ':' made Windows refuse the file and
cv2.imwrite failed silently)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from natural_mouse.plugins.base import ActionContext
from natural_mouse.plugins.screenshot_on_miss import ScreenshotOnMissPlugin, safe_stem

SCREEN = np.zeros((10, 10, 3), np.uint8)


def miss(query):
    return ActionContext(action="click", query=query)


class TestSafeStem(unittest.TestCase):
    def test_names(self):
        cases = {
            "templates/Save button.png": "Save_button",
            "#ff00ff": "ff00ff",
            "C:\\shots\\a:b*c?.png": "a_b_c",
            "../../../etc/passwd": "passwd",
            "": "query",
            None: "query",
            "***": "query",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(safe_stem(query), expected)

    def test_length_is_capped(self):
        self.assertEqual(len(safe_stem("x" * 500)), 60)


class TestPlugin(unittest.TestCase):
    def test_saves_inside_its_folder_with_a_safe_name(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("natural_mouse.plugins.screenshot_on_miss.grab_screen", return_value=SCREEN):
            plugin = ScreenshotOnMissPlugin(tmp)
            ctx = miss("../../#ff00ff")
            plugin.after_locate(ctx)
            saved = plugin.saved[0]
            self.assertTrue(saved.exists())
            self.assertEqual(saved.parent, Path(tmp))
            self.assertTrue(saved.name.endswith("_ff00ff.png"))
            self.assertEqual(ctx.extras["miss_screenshot"], saved)

    def test_a_failed_save_raises_instead_of_pretending(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("natural_mouse.plugins.screenshot_on_miss.grab_screen", return_value=SCREEN), \
                mock.patch("natural_mouse.plugins.screenshot_on_miss.cv2.imwrite", return_value=False):
            plugin = ScreenshotOnMissPlugin(tmp)
            with self.assertRaises(OSError):
                plugin.after_locate(miss("button.png"))
            self.assertEqual(plugin.saved, [])


if __name__ == "__main__":
    unittest.main()
