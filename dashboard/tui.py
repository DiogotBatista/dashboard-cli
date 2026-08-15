import curses
import time
from datetime import datetime, timedelta

from dashboard.models import ProviderStatus, format_reset, remaining_to_used
from dashboard.providers import fetch_all


def merge_statuses(
    previous: tuple[ProviderStatus, ...], current: tuple[ProviderStatus, ...]
) -> tuple[ProviderStatus, ...]:
    last_by_provider = {status.provider: status for status in previous}
    return tuple(
        ProviderStatus(
            provider=status.provider,
            windows=last_by_provider[status.provider].windows,
            fetched_at=last_by_provider[status.provider].fetched_at,
            error=status.error,
        )
        if status.error and not status.windows and status.provider in last_by_provider
        else status
        for status in current
    )


def render_lines(
    statuses: tuple[ProviderStatus, ...], now: datetime, next_fetch_at: datetime
) -> list[str]:
    seconds = max(0, int((next_fetch_at - now).total_seconds()))
    lines = ["AI Usage Dashboard", "─" * 57]

    for status in statuses:
        lines.append(status.provider)
        if not status.windows:
            lines.append(f"  indisponível · {status.error or 'sem dados'}")
        for window in status.windows:
            countdown, reset_date = format_reset(window.resets_at, now)
            stale = " · desatualizado" if status.error else ""
            lines.append(
                f"  {window.name:<8}{remaining_to_used(window.remaining_percent)}% gasto · "
                f"{window.remaining_percent}% restante     {countdown} · {reset_date}{stale}"
            )
        lines.append("")

    lines.append(f"[r] atualizar   [q] sair   próxima consulta em {seconds:02}s")
    return lines


def run(screen: curses.window) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    screen.nodelay(True)
    statuses: tuple[ProviderStatus, ...] = ()
    next_fetch_at = datetime.now().astimezone()

    while True:
        now = datetime.now().astimezone()
        if now >= next_fetch_at:
            statuses = merge_statuses(statuses, fetch_all(now))
            next_fetch_at = now + timedelta(seconds=60)

        height, width = screen.getmaxyx()
        screen.erase()
        for row, line in enumerate(render_lines(statuses, now, next_fetch_at)[:height]):
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
