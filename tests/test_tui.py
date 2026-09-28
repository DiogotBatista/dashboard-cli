import threading
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from dashboard.models import ProviderStatus, Window
from dashboard.tui import merge_statuses, render_lines, run


class TuiTest(TestCase):
    def test_accepts_quit_while_refresh_is_pending(self):
        started = threading.Event()
        release = threading.Event()
        quit_read = threading.Event()

        def slow_fetch():
            started.set()
            release.wait()
            return ()

        class Screen:
            nodelay = erase = refresh = lambda *args: None
            getmaxyx = lambda self: (24, 80)
            addnstr = lambda *args: None

            def getch(self):
                quit_read.set()
                return ord("q")

        with patch("dashboard.tui.curses.curs_set"), patch(
            "dashboard.tui.fetch_all", side_effect=slow_fetch
        ):
            worker = threading.Thread(target=run, args=(Screen(),), daemon=True)
            worker.start()
            try:
                self.assertTrue(started.wait(1))
                self.assertTrue(quit_read.wait(1))
                worker.join(1)
                self.assertFalse(worker.is_alive())
            finally:
                release.set()
                worker.join(1)

    def test_renders_percentages_and_absolute_reset_time(self):
        zone = ZoneInfo("America/Sao_Paulo")
        now = datetime(2026, 8, 15, 17, 15, tzinfo=zone)
        status = ProviderStatus(
            "Codex",
            (Window("5 h", 62, datetime(2026, 8, 15, 19, 30, tzinfo=zone)),),
        )

        lines = render_lines((status,), now, now)

        self.assertIn("5 h     38% gasto · 62% restante", "\n".join(lines))
        self.assertIn("hoje, 19:30", "\n".join(lines))

    def test_renders_error_without_fake_percentage(self):
        now = datetime.now().astimezone()

        lines = render_lines((ProviderStatus("Claude Code", error="consulta indisponível"),), now, now)

        self.assertIn("indisponível", "\n".join(lines))

    def test_keeps_last_windows_when_provider_refresh_fails(self):
        zone = ZoneInfo("America/Sao_Paulo")
        previous = ProviderStatus(
            "Codex",
            (Window("5 h", 62, datetime(2026, 8, 15, 19, 30, tzinfo=zone)),),
        )
        failed = ProviderStatus("Codex", error="consulta indisponível")

        result = merge_statuses((previous,), (failed,))

        self.assertEqual(result[0].windows, previous.windows)
        self.assertEqual(result[0].error, "consulta indisponível")
