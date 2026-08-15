from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from dashboard.models import format_reset, remaining_to_used


class ModelsTest(TestCase):
    def test_derives_used_percentage(self):
        self.assertEqual(remaining_to_used(62), 38)

    def test_formats_countdown_and_local_date(self):
        zone = ZoneInfo("America/Sao_Paulo")
        now = datetime(2026, 8, 15, 17, 15, tzinfo=zone)
        reset = datetime(2026, 8, 15, 19, 30, tzinfo=zone)

        self.assertEqual(format_reset(reset, now), ("em 02:15:00", "hoje, 19:30"))
