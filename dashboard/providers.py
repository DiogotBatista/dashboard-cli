import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from dashboard.models import ProviderStatus, Window

CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


def parse_codex_usage(payload: dict) -> tuple[Window, ...]:
    rate_limit = payload["rate_limit"]
    return tuple(
        Window(
            name=name,
            remaining_percent=100 - int(window["used_percent"]),
            resets_at=datetime.fromtimestamp(window["reset_at"], timezone.utc).astimezone(),
        )
        for name, key in (("5 h", "primary_window"), ("7 dias", "secondary_window"))
        if (window := rate_limit.get(key))
    )


def parse_claude_usage(payload: dict) -> tuple[Window, ...]:
    return tuple(
        Window(
            name=name,
            remaining_percent=100 - int(window["utilization"]),
            resets_at=datetime.fromisoformat(window["resets_at"].replace("Z", "+00:00")).astimezone(),
        )
        for name, key in (("5 h", "five_hour"), ("7 dias", "seven_day"))
        if (window := payload.get(key))
    )


def _request_json(url: str, headers: dict[str, str]) -> dict:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def fetch_codex(now: datetime) -> ProviderStatus:
    try:
        tokens = _load_json(Path.home() / ".codex" / "auth.json")["tokens"]
        payload = _request_json(
            CODEX_USAGE_URL,
            {
                "Authorization": f"Bearer {tokens['access_token']}",
                "ChatGPT-Account-Id": tokens["account_id"],
            },
        )
        return ProviderStatus("Codex", parse_codex_usage(payload), now)
    except Exception:
        return ProviderStatus("Codex", error="consulta indisponível")


def fetch_claude(now: datetime) -> ProviderStatus:
    try:
        oauth = _load_json(Path.home() / ".claude" / ".credentials.json")["claudeAiOauth"]
        payload = _request_json(
            CLAUDE_USAGE_URL,
            {
                "Authorization": f"Bearer {oauth['accessToken']}",
                "anthropic-beta": "oauth-2025-04-20",
            },
        )
        return ProviderStatus("Claude Code", parse_claude_usage(payload), now)
    except Exception:
        return ProviderStatus("Claude Code", error="consulta indisponível")


def fetch_all(now: datetime) -> tuple[ProviderStatus, ProviderStatus]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        codex = executor.submit(fetch_codex, now)
        claude = executor.submit(fetch_claude, now)
        return codex.result(), claude.result()
