import unittest
from datetime import date

from api.holiday_api import HolidayAPI


class FixedTodayHolidayAPI(HolidayAPI):
    def __init__(self, today: date):
        super().__init__(token="")
        self._today = today

    def _get_today(self) -> date:
        return self._today


def holiday_data(*items):
    return {"data": list(items)}


def off_day(name: str, date_str: str):
    return {"name": name, "date": date_str, "is_off_day": 1}


class HolidayAPITestCase(unittest.TestCase):
    def test_holiday_first_day_can_show_zero_days_left(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 20))
        result = api.parse_holidays(
            holiday_data(
                off_day("端午节", "2026-06-20"),
                off_day("端午节", "2026-06-21"),
                off_day("中秋节", "2026-09-25"),
            )
        )

        self.assertEqual(result[0], {"name": "端午节", "days_left": 0})

    def test_holiday_after_first_day_skips_whole_holiday_block(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 21))
        result = api.parse_holidays(
            holiday_data(
                off_day("端午节", "2026-06-20"),
                off_day("端午节", "2026-06-21"),
                off_day("端午节", "2026-06-22"),
                off_day("中秋节", "2026-09-25"),
            )
        )

        self.assertEqual(result[0], {"name": "中秋节", "days_left": 96})
        self.assertNotIn({"name": "端午节", "days_left": 0}, result)

    def test_holiday_period_label_is_not_returned(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 21))
        result = api.parse_holidays(
            holiday_data(
                off_day("端午节", "2026-06-20"),
                off_day("端午假期", "2026-06-21"),
                off_day("端午假期", "2026-06-22"),
                off_day("中秋节", "2026-09-25"),
            )
        )

        self.assertEqual(result, [{"name": "中秋节", "days_left": 96}])

    def test_holiday_last_day_context_uses_displayable_holiday_name(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 22))
        result = api.parse_holiday_last_day_context(
            holiday_data(
                off_day("端午节", "2026-06-20"),
                off_day("端午假期", "2026-06-21"),
                off_day("端午假期", "2026-06-22"),
            )
        )

        self.assertEqual(
            result,
            {"name": "端午节", "days_left": 0, "type": "holiday_last_day"},
        )

    def test_holiday_last_day_context_ignores_middle_day(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 21))
        result = api.parse_holiday_last_day_context(
            holiday_data(
                off_day("端午节", "2026-06-20"),
                off_day("端午假期", "2026-06-21"),
                off_day("端午假期", "2026-06-22"),
            )
        )

        self.assertIsNone(result)

    def test_holiday_last_day_context_ignores_single_day_holiday(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 20))
        result = api.parse_holiday_last_day_context(
            holiday_data(off_day("端午节", "2026-06-20"))
        )

        self.assertIsNone(result)

    def test_holiday_last_day_context_uses_generic_name_for_period_only_block(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 22))
        result = api.parse_holiday_last_day_context(
            holiday_data(
                off_day("端午假期", "2026-06-20"),
                off_day("端午假期", "2026-06-21"),
                off_day("端午假期", "2026-06-22"),
            )
        )

        self.assertEqual(
            result,
            {"name": None, "days_left": 0, "type": "holiday_last_day"},
        )

    def test_holiday_last_day_context_ignores_weekend_block(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 21))
        result = api.parse_holiday_last_day_context(
            holiday_data(
                off_day("周末", "2026-06-20"),
                off_day("周末", "2026-06-21"),
            )
        )

        self.assertIsNone(result)

    def test_past_single_day_holiday_is_not_returned(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 21))
        result = api.parse_holidays(
            holiday_data(
                off_day("儿童节", "2026-06-01"),
                off_day("中秋节", "2026-09-25"),
            )
        )

        self.assertEqual(result, [{"name": "中秋节", "days_left": 96}])

    def test_future_holidays_are_sorted_and_limited(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 20))
        result = api.parse_holidays(
            holiday_data(
                off_day("国庆节", "2026-10-01"),
                off_day("中秋节", "2026-09-25"),
                off_day("七夕节", "2026-08-19"),
            ),
            max_count=2,
        )

        self.assertEqual(
            result,
            [
                {"name": "七夕节", "days_left": 60},
                {"name": "中秋节", "days_left": 97},
            ],
        )

    def test_no_future_holiday_uses_default_holidays(self):
        api = FixedTodayHolidayAPI(date(2026, 6, 21))
        result = api.parse_holidays(holiday_data(off_day("儿童节", "2026-06-01")))

        self.assertEqual(result, api._get_default_holidays())


if __name__ == "__main__":
    unittest.main()
