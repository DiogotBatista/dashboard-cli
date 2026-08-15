from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Window:
    name: str
    remaining_percent: int
    resets_at: datetime


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    windows: tuple[Window, ...] = ()
    fetched_at: datetime | None = None
    error: str | None = None


def remaining_to_used(remaining_percent: int) -> int:
    return 100 - remaining_percent


def format_reset(resets_at: datetime, now: datetime) -> tuple[str, str]:
    seconds = max(0, int((resets_at - now).total_seconds()))
    days, seconds = divmod(seconds, 86_400)
    hours, seconds = divmod(seconds, 3_600)
    minutes, seconds = divmod(seconds, 60)
    countdown = (
        f"em {days}d {hours:02}:{minutes:02}:{seconds:02}"
        if days
        else f"em {hours:02}:{minutes:02}:{seconds:02}"
    )
    date = (
        f"hoje, {resets_at:%H:%M}"
        if resets_at.date() == now.date()
        else resets_at.strftime("%d/%m, %H:%M")
    )
    return countdown, date
