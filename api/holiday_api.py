"""
节假日 API 处理模块
用于获取和解析节假日数据，供日报模板使用
"""

import aiohttp
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

from astrbot.api import logger
from .base_api import BaseAPI


class HolidayAPI(BaseAPI):
    """节假日 API 处理类"""

    def __init__(
        self,
        token: str,
        session: Optional[aiohttp.ClientSession] = None,
        year: Optional[int] = None,
    ):
        """
        初始化

        Args:
            token: API token
            session: 可选的 aiohttp.ClientSession，如果提供则复用
            year: 指定年份，None 则使用当前年份
        """
        super().__init__(session)
        self.token = token
        self.url = "https://v3.alapi.cn/api/holiday"
        self.headers = {"Content-Type": "application/json"}
        self.year = year or datetime.now().year

    async def get_holidays_async(self) -> Optional[Dict]:
        """
        异步方式获取节假日数据（推荐用于 AstrBot）

        Returns:
            API 返回的原始数据，失败返回 None
        """
        try:
            session = await self._get_session()
            params = {"token": self.token}
            async with session.get(
                self.url,
                headers=self.headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.warning(f"请求节假日 API 失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取节假日数据失败: {e}", exc_info=True)
            return None

    def parse_holidays(
        self, api_data: Optional[Dict], max_count: int = 3
    ) -> List[Dict]:
        """
        解析节假日数据，转换为模板需要的格式

        Args:
            api_data: API 返回的原始数据
            max_count: 最多返回几个节假日

        Returns:
            格式化的节假日列表，格式：
            [
                {'name': '春节', 'days_left': 25},
                {'name': '清明节', 'days_left': 78},
                ...
            ]
        """
        if not api_data:
            return self._get_default_holidays()

        try:
            # 提取数据
            holidays_data = api_data.get("data", [])
            if not isinstance(holidays_data, list) or len(holidays_data) == 0:
                return self._get_default_holidays()

            # 获取当前日期
            today = self._get_today()

            # 处理节假日数据
            holiday_dates = {}

            for holiday in holidays_data:
                off_day = self._parse_off_day(holiday)
                if off_day is None:
                    continue

                name = off_day["name"]
                if not self._is_displayable_holiday_name(name):
                    continue
                holiday_dates.setdefault(name, set()).add(off_day["date"])

            processed_holidays = []
            for name, dates in holiday_dates.items():
                for start_date in self._iter_holiday_start_dates(dates):
                    # 多天节假日按首日计算；首日已过则跳过整个假期块。
                    if start_date < today:
                        continue
                    days_left = (start_date - today).days
                    processed_holidays.append(
                        {"name": name, "days_left": days_left, "date": start_date}
                    )

            # 按天数排序，取最近的几个
            processed_holidays.sort(key=lambda x: x["days_left"])
            result = processed_holidays[:max_count]

            # 如果没有找到未来的节假日，返回默认值
            if len(result) == 0:
                logger.warning("未找到未来的节假日数据，使用默认数据")
                return self._get_default_holidays()

            # 格式化输出（移除 date 字段，只保留模板需要的）
            return [
                {"name": item["name"], "days_left": item["days_left"]}
                for item in result
            ]

        except Exception as e:
            logger.error(f"解析节假日数据时出错: {e}", exc_info=True)
            return self._get_default_holidays()

    def parse_holiday_last_day_context(
        self, api_data: Optional[Dict]
    ) -> Optional[Dict]:
        """解析今天是否为多天假期最后一天，用于问候语隐藏上下文。"""
        if not api_data:
            return None

        try:
            holidays_data = api_data.get("data", [])
            if not isinstance(holidays_data, list) or len(holidays_data) == 0:
                return None

            today = self._get_today()
            off_days = []
            for holiday in holidays_data:
                off_day = self._parse_off_day(holiday)
                if off_day is not None:
                    off_days.append(off_day)

            for holiday_block in self._iter_holiday_blocks(off_days):
                if len(holiday_block) <= 1:
                    continue
                if holiday_block[-1]["date"] != today:
                    continue
                if not self._is_holiday_block_contextual(holiday_block):
                    continue
                return {
                    "name": self._get_display_name_from_holiday_block(holiday_block),
                    "days_left": 0,
                    "type": "holiday_last_day",
                }

        except Exception as e:
            logger.error(f"解析假期最后一天上下文时出错: {e}", exc_info=True)

        return None

    def _get_default_holidays(self) -> List[Dict]:
        """
        返回默认的节假日数据（当 API 失败时使用）

        Returns:
            默认节假日列表
        """
        return [
            {"name": "周末", "days_left": 3},
            {"name": "春节", "days_left": 25},
            {"name": "清明节", "days_left": 78},
        ]

    def _get_today(self) -> date:
        """返回当前日期，便于测试中固定日期。"""
        return date.today()

    def _parse_off_day(self, holiday: Dict) -> Optional[Dict]:
        """从 API 单条数据中解析实际放假日期。"""
        if not isinstance(holiday, dict):
            return None

        is_off_day = holiday.get("is_off_day")
        if is_off_day != 1:
            return None

        date_str = holiday.get("date")
        if not date_str:
            return None

        try:
            holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            logger.warning(f"日期解析失败: {date_str}, 错误: {e}")
            return None

        name = str(holiday.get("name", "未知")).strip() or "未知"
        return {"name": name, "date": holiday_date}

    def _is_displayable_holiday_name(self, name: str) -> bool:
        """过滤假期段标签，只展示真正的节日名。"""
        return not str(name).strip().endswith("假期")

    def _is_holiday_block_contextual(self, holiday_block: List[Dict]) -> bool:
        """判断连续放假块是否应该触发假期最后一天问候。"""
        for day_info in holiday_block:
            for name in day_info["names"]:
                if name in {"周末", "未知"}:
                    continue
                if name.endswith("假期") or self._is_displayable_holiday_name(name):
                    return True
        return False

    def _get_display_name_from_holiday_block(self, holiday_block: List[Dict]):
        """从假期块中取真实节日名；只有假期标签时返回 None。"""
        for day_info in holiday_block:
            for name in day_info["names"]:
                if self._is_displayable_holiday_name(name) and name != "周末":
                    return name
        return None

    def _iter_holiday_blocks(self, off_days: List[Dict]) -> List[List[Dict]]:
        """按连续日期聚合实际放假日期。"""
        names_by_date = {}
        for off_day in off_days:
            names_by_date.setdefault(off_day["date"], set()).add(off_day["name"])

        holiday_blocks = []
        current_block = []
        previous_date = None

        for current_date in sorted(names_by_date):
            if previous_date is None or current_date > previous_date + timedelta(
                days=1
            ):
                if current_block:
                    holiday_blocks.append(current_block)
                current_block = []
            current_block.append(
                {"date": current_date, "names": sorted(names_by_date[current_date])}
            )
            previous_date = current_date

        if current_block:
            holiday_blocks.append(current_block)

        return holiday_blocks

    def _iter_holiday_start_dates(self, dates) -> List[date]:
        """按连续假期块返回每个假期块的首日。"""
        start_dates = []
        previous_date = None

        for current_date in sorted(dates):
            if previous_date is None or current_date > previous_date + timedelta(
                days=1
            ):
                start_dates.append(current_date)
            previous_date = current_date

        return start_dates

    async def get_moyu_list_async(self, max_count: int = 3) -> List[Dict]:
        """
        异步方式获取摸鱼日历数据（推荐用于 AstrBot）

        Args:
            max_count: 最多返回几个节假日

        Returns:
            格式化的摸鱼日历列表
        """
        api_data = await self.get_holidays_async()
        return self.parse_holidays(api_data, max_count)
