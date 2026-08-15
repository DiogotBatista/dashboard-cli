from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

from dashboard.providers import (
    fetch_all,
    fetch_claude,
    fetch_codex,
    parse_claude_usage,
    parse_codex_usage,
)


class ProviderParserTest(TestCase):
    def test_parses_codex_primary_and_secondary_windows(self):
        payload = {
            "rate_limit": {
                "primary_window": {"used_percent": 38, "reset_at": 1_786_836_600},
                "secondary_window": {"used_percent": 52, "reset_at": 1_787_130_000},
            }
        }

        windows = parse_codex_usage(payload)

        self.assertEqual([window.remaining_percent for window in windows], [62, 48])

    def test_parses_claude_five_hour_and_seven_day_windows(self):
        payload = {
            "five_hour": {"utilization": 29, "resets_at": "2026-08-15T21:22:00Z"},
            "seven_day": {"utilization": 52, "resets_at": "2026-08-19T08:00:00Z"},
        }

        windows = parse_claude_usage(payload)

        self.assertEqual([window.name for window in windows], ["5 h", "7 dias"])
        self.assertEqual([window.remaining_percent for window in windows], [71, 48])

    @patch("dashboard.providers._request_json", side_effect=OSError("offline"))
    def test_fetch_returns_safe_error_without_raising(self, _request):
        status = fetch_codex(datetime.now(timezone.utc))

        self.assertEqual(status.provider, "Codex")
        self.assertEqual(status.windows, ())
        self.assertEqual(status.error, "consulta indisponível")

    @patch("dashboard.providers._request_json", side_effect=OSError("offline"))
    def test_fetch_claude_returns_safe_error_without_raising(self, _request):
        status = fetch_claude(datetime.now(timezone.utc))

        self.assertEqual(status.provider, "Claude Code")
        self.assertEqual(status.windows, ())
        self.assertEqual(status.error, "consulta indisponível")

    @patch("dashboard.providers.fetch_claude")
    @patch("dashboard.providers.fetch_codex")
    def test_fetches_providers_in_display_order(self, codex, claude):
        now = datetime.now(timezone.utc)
        codex.return_value.provider = "Codex"
        claude.return_value.provider = "Claude Code"

        statuses = fetch_all(now)

        self.assertEqual([status.provider for status in statuses], ["Codex", "Claude Code"])
