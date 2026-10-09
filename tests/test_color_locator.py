import unittest

import numpy as np

from natural_mouse.vision.color_locator import ColorLocator, parse_hex_colour


def screen_with(*boxes, size=(300, 400)):
    """A grey BGR 'screenshot' with solid boxes: (x, y, w, h, bgr)."""
    img = np.full((*size, 3), 200, dtype=np.uint8)
    for x, y, w, h, bgr in boxes:
        img[y:y + h, x:x + w] = bgr
    return img


MAGENTA = (255, 0, 255)  # BGR, same as RGB for magenta
CYAN = (255, 255, 0)     # BGR for #00ffff


class TestParseHexColour(unittest.TestCase):
    def test_returns_bgr(self):
        self.assertEqual(parse_hex_colour("#ff8800"), (0, 136, 255))
        self.assertEqual(parse_hex_colour("00FFFF"), (255, 255, 0))

    def test_rejects_bad_input(self):
        for bad in ("", "#fff", "#gg0000", "red", "#ff00ff00"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_hex_colour(bad)


class TestColorLocator(unittest.TestCase):
    def test_finds_box_bounds(self):
        locator = ColorLocator(grab=lambda region: screen_with((50, 20, 120, 40, MAGENTA)))

        match = locator.locate("#ff00ff")

        self.assertEqual((match.x, match.y, match.width, match.height), (50, 20, 120, 40))
        self.assertAlmostEqual(match.confidence, 1.0)

    def test_ignores_other_colours_and_returns_none(self):
        locator = ColorLocator(grab=lambda region: screen_with((50, 20, 120, 40, CYAN)))

        self.assertIsNone(locator.locate("#ff00ff"))

    def test_tolerates_slight_colour_shift(self):
        # Colour management or anti-aliasing can shift a colour a little.
        locator = ColorLocator(grab=lambda region: screen_with((10, 10, 60, 60, (250, 4, 251))))

        self.assertIsNotNone(locator.locate("#ff00ff"))

    def test_ignores_specks_below_min_area(self):
        locator = ColorLocator(min_area=100, grab=lambda region: screen_with((5, 5, 5, 5, MAGENTA)))

        self.assertIsNone(locator.locate("#ff00ff"))

    def test_low_fill_ratio_is_rejected(self):
        # A hollow outline: big bounding box, few pixels of the colour.
        img = screen_with()
        img[10:110, 10] = MAGENTA
        img[10:110, 109] = MAGENTA
        img[10, 10:110] = MAGENTA
        img[109, 10:110] = MAGENTA
        locator = ColorLocator(grab=lambda region: img)

        self.assertIsNone(locator.locate("#ff00ff", confidence=0.85))
        self.assertIsNotNone(locator.locate("#ff00ff", confidence=0.01))

    def test_locate_all_largest_first_and_region_offset(self):
        img = screen_with((0, 0, 20, 20, MAGENTA), (100, 100, 60, 30, MAGENTA))
        seen_regions = []

        def grab(region):
            seen_regions.append(region)
            return img

        matches = ColorLocator(grab=grab).locate_all("#ff00ff", region=(1000, 500, 400, 300))

        self.assertEqual(seen_regions, [(1000, 500, 400, 300)])
        self.assertEqual([(m.x, m.y) for m in matches], [(1100, 600), (1000, 500)])


if __name__ == "__main__":
    unittest.main()
