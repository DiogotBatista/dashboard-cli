import runpy
import threading
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from dashboard.models import ProviderStatus, Window
from dashboard.tui import merge_statuses, render_lines, run


class TuiTest(TestCase):
    def test_shows_provider_placeholders_while_first_refresh_is_pending(self):
        rendered = []

        class Screen:
            nodelay = erase = refresh = lambda *args: None
            getmaxyx = lambda self: (24, 80)
            getch = lambda self: ord("q")

            def addnstr(self, _row, _column, line, width):
                rendered.append(line[:width])

        with patch("dashboard.tui.curses.curs_set"), patch(
            "dashboard.tui.fetch_all", return_value=()
        ):
            run(Screen())

        output = "\n".join(rendered)
        self.assertIn("Codex\n  consultando…", output)
        self.assertIn("Claude Code\n  consultando…", output)

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

        self.assertIn("  5 h     38% gasto · 62% restante", lines)
        self.assertIn("          em 02:15:00 · hoje, 19:30", lines)

    def test_renders_error_without_fake_percentage(self):
        now = datetime.now().astimezone()

        lines = render_lines((ProviderStatus("Claude Code", error="consulta indisponível"),), now, now)

        self.assertIn("indisponível", "\n".join(lines))

    def test_renders_controls_and_next_refresh_on_separate_lines(self):
        now = datetime.now().astimezone()

        lines = render_lines((), now, now)

        self.assertIn("[r] atualizar   [q] sair", lines)
        self.assertIn("próxima consulta em 00s", lines)

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

    def test_renders_stale_error_cause_on_its_own_line(self):
        zone = ZoneInfo("America/Sao_Paulo")
        now = datetime(2026, 8, 15, 17, 15, tzinfo=zone)
        status = ProviderStatus(
            "Codex",
            (Window("5 h", 62, datetime(2026, 8, 15, 19, 30, tzinfo=zone)),),
            error="consulta indisponível",
        )

        lines = render_lines((status,), now, now)

        self.assertIn("  desatualizado · consulta indisponível", lines)

    def test_ctrl_c_exits_cleanly(self):
        clean_exit = True
        with patch("curses.wrapper", side_effect=KeyboardInterrupt):
            try:
                runpy.run_module("dashboard.__main__", run_name="__main__")
            except KeyboardInterrupt:
                clean_exit = False

        self.assertTrue(clean_exit)
