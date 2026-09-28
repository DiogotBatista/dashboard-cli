import curses
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta

from dashboard.models import ProviderStatus, format_reset
from dashboard.providers import fetch_all


def merge_statuses(
    previous: tuple[ProviderStatus, ...], current: tuple[ProviderStatus, ...]
) -> tuple[ProviderStatus, ...]:
    last_by_provider = {status.provider: status for status in previous}
    return tuple(
        replace(status, windows=last_by_provider[status.provider].windows)
        if status.error and not status.windows and status.provider in last_by_provider
        else status
        for status in current
    )


def render_lines(
    statuses: tuple[ProviderStatus, ...],
    now: datetime,
    next_fetch_at: datetime,
    refreshing: bool = False,
) -> list[str]:
    seconds = max(0, int((next_fetch_at - now).total_seconds()))
    lines = ["AI Usage Dashboard", "─" * 57]

    if refreshing and not statuses:
        statuses = (ProviderStatus("Codex"), ProviderStatus("Claude Code"))

    for status in statuses:
        lines.append(status.provider)
        if not status.windows:
            lines.append(
                "  consultando…"
                if refreshing and not status.error
                else f"  indisponível · {status.error or 'sem dados'}"
            )
        for window in status.windows:
            countdown, reset_date = format_reset(window.resets_at, now)
            lines.append(
                f"  {window.name:<8}{100 - window.remaining_percent}% gasto · "
                f"{window.remaining_percent}% restante"
            )
            lines.append(f"          {countdown} · {reset_date}")
        if status.windows and status.error:
            lines.append(f"  desatualizado · {status.error}")
        lines.append("")

    if refreshing:
        lines.append("[q] sair   consultando…")
    else:
        lines.extend(("[r] atualizar   [q] sair", f"próxima consulta em {seconds:02}s"))
    return lines


def run(screen: curses.window) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    screen.nodelay(True)
    statuses: tuple[ProviderStatus, ...] = ()
    next_fetch_at = datetime.now().astimezone()
    executor = ThreadPoolExecutor(max_workers=1)
    refresh = None

    try:
        while True:
            now = datetime.now().astimezone()
            if refresh is not None and refresh.done():
                statuses = merge_statuses(statuses, refresh.result())
                refresh = None
                next_fetch_at = now + timedelta(seconds=60)
            if refresh is None and now >= next_fetch_at:
                refresh = executor.submit(fetch_all)

            height, width = screen.getmaxyx()
            screen.erase()
            lines = render_lines(statuses, now, next_fetch_at, refreshing=refresh is not None)
            for row, line in enumerate(lines[:height]):
                try:
                    screen.addnstr(row, 0, line, max(0, width - 1))
                except curses.error:
                    pass
            screen.refresh()

            key = screen.getch()
            if key in (ord("q"), ord("Q")):
                return
            if key in (ord("r"), ord("R")):
                next_fetch_at = now
            time.sleep(0.1)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
