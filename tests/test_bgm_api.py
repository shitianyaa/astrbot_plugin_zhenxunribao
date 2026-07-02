import unittest
from datetime import datetime

from api.bgm_api import BGMAPI


def today_calendar_data(*items):
    return [
        {
            "weekday": {"id": datetime.now().weekday() + 1},
            "items": list(items),
        }
    ]


class BGMAPITestCase(unittest.TestCase):
    def test_parse_today_anime_skips_item_with_null_images(self):
        api = BGMAPI()

        result = api.parse_today_anime(
            today_calendar_data(
                {"name_cn": "No Image", "name": "No Image JP", "images": None},
                {
                    "name_cn": "With Image",
                    "name": "With Image JP",
                    "images": {"medium": "https://example.com/image.jpg"},
                },
            ),
            max_count=2,
        )

        self.assertEqual(
            result,
            [{"title": "With Image", "image": "https://example.com/image.jpg"}],
        )


if __name__ == "__main__":
    unittest.main()
