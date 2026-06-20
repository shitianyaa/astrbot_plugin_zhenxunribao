import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_plugin_class():
    package_name = "zhenxunribao_under_test"
    plugin_dir = Path(__file__).resolve().parents[1]

    package = types.ModuleType(package_name)
    package.__path__ = [str(plugin_dir)]
    sys.modules[package_name] = package

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.main", plugin_dir / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.ZhenxunReportPlugin


ZhenxunReportPlugin = load_plugin_class()


class GreetingContextTestCase(unittest.TestCase):
    def setUp(self):
        self.plugin = object.__new__(ZhenxunReportPlugin)

    def test_default_greeting_uses_named_holiday_last_day_context(self):
        greeting = self.plugin._get_default_greeting(
            8,
            [{"name": "中秋节", "days_left": 1}],
            {"name": "端午节", "days_left": 0, "type": "holiday_last_day"},
        )

        self.assertEqual(greeting, "📰 端午节假期最后一天啦！日报送上~\n")

    def test_default_greeting_uses_generic_holiday_last_day_context(self):
        greeting = self.plugin._get_default_greeting(
            8,
            [{"name": "中秋节", "days_left": 1}],
            {"name": None, "days_left": 0, "type": "holiday_last_day"},
        )

        self.assertEqual(greeting, "📰 今天是假期最后一天啦！日报送上~\n")

    def test_holiday_today_context_takes_priority_over_last_day_context(self):
        greeting = self.plugin._get_default_greeting(
            8,
            [{"name": "中秋节", "days_left": 0}],
            {"name": "端午节", "days_left": 0, "type": "holiday_last_day"},
        )

        self.assertEqual(greeting, "📰 中秋节快乐！日报送上~\n")


if __name__ == "__main__":
    unittest.main()
