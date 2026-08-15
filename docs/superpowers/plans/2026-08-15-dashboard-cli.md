# Dashboard CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar um TUI local que acompanhe as cotas de assinatura do Codex e do Claude Code.

**Architecture:** Dois adaptadores leem somente o token de acesso da sessão local e consultam a rota de uso do respectivo provedor. Eles devolvem o mesmo modelo imutável para um loop `curses`, que atualiza a tela a cada segundo e busca dados novos a cada 60 segundos.

**Tech Stack:** Python 3.12; biblioteca padrão (`curses`, `dataclasses`, `datetime`, `json`, `urllib`, `unittest`).

**Spec:** `docs/superpowers/specs/2026-08-15-dashboard-cli-design.md`

## Global Constraints

- Suportar Ubuntu sob WSL e Python 3.12.
- Consultar sessões autenticadas existentes somente em memória.
- Nunca registrar, persistir ou imprimir credenciais, tokens ou respostas HTTP brutas.
- Exibir percentual gasto, percentual restante, contador e data/hora local de reinício.
- Atualizar automaticamente a cada 60 segundos; `r` atualiza já; `q` e `Ctrl-C` encerram.
- Uma falha em um provedor não bloqueia o outro e nunca produz estimativa de cota.
- Não adicionar dependências, banco, histórico, alertas, gráficos, configuração persistida ou empacotamento global.

---

## Estrutura de arquivos

```text
dashboard-cli/
├── dashboard/                 # pacote Python, sem dependências externas
│   ├── __init__.py
│   ├── __main__.py            # ponto de entrada de `python -m dashboard`
│   ├── models.py              # contrato normalizado e erros públicos
│   ├── providers.py           # leitura de sessão e consultas HTTP dos provedores
│   └── tui.py                 # loop curses, relógio e renderização
├── tests/
│   ├── test_models.py
│   ├── test_providers.py
│   └── test_tui.py
├── dashboard                  # lançador executável local: `./dashboard`
└── README.md                  # instalação, uso e limites conhecidos
```

## Task 1: Contrato de domínio e inicialização mínima

**Files:**
- Create: `.gitignore`
- Create: `dashboard/__init__.py`
- Create: `dashboard/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces: `Window(name: str, remaining_percent: int, resets_at: datetime)` e `ProviderStatus(provider: str, windows: tuple[Window, ...], fetched_at: datetime | None, error: str | None)`.
- Produces: `remaining_to_used(remaining_percent: int) -> int` e `format_reset(resets_at: datetime, now: datetime) -> tuple[str, str]`.

- [ ] **Step 1: Inicializar o repositório local, conectar o remoto vazio e ignorar artefatos locais**

Run:

```bash
git init
git remote add origin git@github.com:DiogotBatista/dashboard-cli.git
printf '__pycache__/\n.pytest_cache/\n' > .gitignore
```

- [ ] **Step 2: Escrever os testes que falham para o contrato e o relógio**

```python
# tests/test_models.py
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest import TestCase

from dashboard.models import Window, format_reset, remaining_to_used


class ModelsTest(TestCase):
    def test_derives_used_percentage(self):
        self.assertEqual(remaining_to_used(62), 38)

    def test_formats_countdown_and_local_date(self):
        zone = ZoneInfo("America/Sao_Paulo")
        now = datetime(2026, 8, 15, 17, 15, tzinfo=zone)
        reset = datetime(2026, 8, 15, 19, 30, tzinfo=zone)
        self.assertEqual(format_reset(reset, now), ("em 02:15:00", "hoje, 19:30"))
```

- [ ] **Step 3: Executar o teste para confirmar a falha**

Run: `python3 -m unittest tests.test_models -v`

Expected: FAIL ao importar `dashboard.models`.

- [ ] **Step 4: Implementar o menor contrato validado**

```python
# dashboard/models.py
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
    countdown = f"em {days}d {hours:02}:{minutes:02}:{seconds:02}" if days else f"em {hours:02}:{minutes:02}:{seconds:02}"
    date = f"hoje, {resets_at:%H:%M}" if resets_at.date() == now.date() else resets_at.strftime("%d/%m, %H:%M")
    return countdown, date
```

- [ ] **Step 5: Executar testes e criar o primeiro commit**

Run: `python3 -m unittest tests.test_models -v`

Expected: PASS.

```bash
git add .gitignore dashboard tests/test_models.py
git commit -m "feat: add usage domain model"
```

## Task 2: Adaptadores autenticados e normalização de respostas

**Files:**
- Create: `dashboard/providers.py`
- Create: `tests/test_providers.py`

**Interfaces:**
- Consumes: `Window` e `ProviderStatus` de `dashboard.models`.
- Produces: `fetch_codex(now: datetime) -> ProviderStatus`, `fetch_claude(now: datetime) -> ProviderStatus` e `fetch_all(now: datetime) -> tuple[ProviderStatus, ProviderStatus]`.

- [ ] **Step 1: Escrever fixtures sem credenciais e testes de normalização**

```python
# tests/test_providers.py
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

from dashboard.providers import parse_codex_usage, parse_claude_usage


class ProviderParserTest(TestCase):
    def test_parses_codex_primary_and_secondary_windows(self):
        payload = {"rate_limit": {"primary_window": {"used_percent": 38, "reset_at": 1786836600}, "secondary_window": {"used_percent": 52, "reset_at": 1787130000}}}
        windows = parse_codex_usage(payload)
        self.assertEqual([window.remaining_percent for window in windows], [62, 48])

    def test_parses_claude_five_hour_and_seven_day_windows(self):
        payload = {"five_hour": {"utilization": 29, "resets_at": "2026-08-15T21:22:00Z"}, "seven_day": {"utilization": 52, "resets_at": "2026-08-19T08:00:00Z"}}
        windows = parse_claude_usage(payload)
        self.assertEqual([window.name for window in windows], ["5 h", "7 dias"])
        self.assertEqual([window.remaining_percent for window in windows], [71, 48])
```

- [ ] **Step 2: Confirmar que os parsers ainda falham**

Run: `python3 -m unittest tests.test_providers -v`

Expected: FAIL ao importar `dashboard.providers`.

- [ ] **Step 3: Implementar o parser e a leitura segura de credenciais**

```python
# dashboard/providers.py
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


def _read_access_token(path: Path, root: str, field: str) -> str:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    token = value[root][field]
    if not isinstance(token, str) or not token:
        raise RuntimeError("sessão não autenticada")
    return token


def parse_codex_usage(payload: dict) -> tuple[Window, ...]:
    windows = payload["rate_limit"]
    return tuple(
        Window(name, 100 - int(windows[key]["used_percent"]), datetime.fromtimestamp(windows[key]["reset_at"], timezone.utc).astimezone())
        for name, key in (("5 h", "primary_window"), ("7 dias", "secondary_window"))
        if windows.get(key)
    )
```

Implement `parse_claude_usage` com as chaves `five_hour` e `seven_day`, usando
`utilization` como percentual gasto e `datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()` para `resets_at`. O parser deve levantar `RuntimeError("resposta de uso inválida")` para chaves ou tipos ausentes; `fetch_*` converte toda exceção nessa mensagem pública por provedor, sem incluir token, URL ou corpo HTTP.

Implement `fetch_codex` lendo `~/.codex/auth.json`, usando `tokens.access_token`
e `tokens.account_id`, e enviando `Authorization: Bearer <access_token>` e
`ChatGPT-Account-Id: <account_id>`. Implement `fetch_claude` lendo
`~/.claude/.credentials.json`, usando `claudeAiOauth.accessToken`, e enviando
`Authorization: Bearer <access_token>` e `anthropic-beta: oauth-2025-04-20`.
Use `urllib.request.urlopen(..., timeout=10)` e decode JSON com UTF-8. Não
implemente refresh de token: o erro instrui a executar o login do CLI.

- [ ] **Step 4: Fazer os parsers passarem e testar falha isolada**

Adicione este teste:

```python
    @patch("dashboard.providers._request_json", side_effect=OSError("offline"))
    def test_fetch_returns_safe_error_without_raising(self, _request):
        from dashboard.providers import fetch_codex
        status = fetch_codex(datetime.now(timezone.utc))
        self.assertEqual(status.provider, "Codex")
        self.assertEqual(status.windows, ())
        self.assertEqual(status.error, "consulta indisponível")
```

Run: `python3 -m unittest tests.test_providers -v`

Expected: PASS.

- [ ] **Step 5: Implementar consulta paralela e criar commit**

Use `concurrent.futures.ThreadPoolExecutor(max_workers=2)` em `fetch_all` para
executar `fetch_codex` e `fetch_claude` simultaneamente, retornando sempre os
dois `ProviderStatus` na ordem Codex, Claude Code.

Run: `python3 -m unittest tests.test_models tests.test_providers -v`

Expected: PASS.

```bash
git add dashboard/providers.py tests/test_providers.py
git commit -m "feat: fetch subscription usage"
```

## Task 3: TUI persistente e atualização

**Files:**
- Create: `dashboard/tui.py`
- Create: `dashboard/__main__.py`
- Create: `tests/test_tui.py`
- Create: `dashboard`

**Interfaces:**
- Consumes: `ProviderStatus`, `format_reset` e `fetch_all`.
- Produces: `render_lines(statuses: tuple[ProviderStatus, ...], now: datetime, next_fetch_at: datetime) -> list[str]` e `run(screen: curses.window) -> None`.

- [ ] **Step 1: Escrever teste de linhas para sucesso e indisponibilidade**

```python
# tests/test_tui.py
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest import TestCase

from dashboard.models import ProviderStatus, Window
from dashboard.tui import render_lines


class TuiTest(TestCase):
    def test_renders_percentages_and_absolute_reset_time(self):
        zone = ZoneInfo("America/Sao_Paulo")
        now = datetime(2026, 8, 15, 17, 15, tzinfo=zone)
        status = ProviderStatus("Codex", (Window("5 h", 62, datetime(2026, 8, 15, 19, 30, tzinfo=zone)),), now)
        lines = render_lines((status,), now, now)
        self.assertIn("5 h     38% gasto · 62% restante", "\n".join(lines))
        self.assertIn("hoje, 19:30", "\n".join(lines))

    def test_renders_error_without_fake_percentage(self):
        lines = render_lines((ProviderStatus("Claude Code", error="consulta indisponível"),), datetime.now().astimezone(), datetime.now().astimezone())
        self.assertIn("indisponível", "\n".join(lines))
```

- [ ] **Step 2: Confirmar falha antes de escrever o TUI**

Run: `python3 -m unittest tests.test_tui -v`

Expected: FAIL ao importar `dashboard.tui`.

- [ ] **Step 3: Implementar renderização pura e loop curses mínimo**

Implement `render_lines` para gerar título, blocos por provedor, uma linha por
janela no formato da especificação e rodapé `[r] atualizar   [q] sair`. Para
status com `error`, renderize somente `indisponível · <erro>`; para janelas
anteriores a uma falha, renderize as janelas e acrescente `desatualizado`.

Implement `run` com `screen.nodelay(True)`, `curses.curs_set(0)`, atualização
de relógio por `time.monotonic()` e renderização uma vez por segundo. Faça a
primeira chamada a `fetch_all` na abertura, outra quando vencerem 60 segundos
ou ao receber `r`; encerre em `q`. Escreva as linhas com
`screen.addnstr(row, 0, line, max(0, width - 1))`, ignorando `curses.error`
para terminais baixos/estreitos.

Crie `dashboard/__main__.py` com `curses.wrapper(run)`. Crie o arquivo
executável `dashboard`:

```sh
#!/usr/bin/env sh
exec python3 -m dashboard "$@"
```

- [ ] **Step 4: Executar os testes e verificar o lançador**

Run: `python3 -m unittest discover -v && chmod +x dashboard && ./dashboard`

Expected: todos os testes PASS; o TUI abre e `q` o encerra sem traceback.

- [ ] **Step 5: Criar commit do TUI**

```bash
git add dashboard tests/test_tui.py
git commit -m "feat: add live usage terminal dashboard"
```

## Task 4: Documentação, revisão de segurança e validação autenticada

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: o lançador `./dashboard` e a autenticação existente dos CLIs.
- Produces: instruções reproduzíveis de execução e recuperação de sessão expirada.

- [ ] **Step 1: Escrever README focado em execução e limites**

Inclua exatamente:

```markdown
## Uso

```bash
./dashboard
```

O comando exige sessões ativas de `codex login` e `claude auth login`. Ele não
salva credenciais nem usa uma chave API. Caso uma sessão expire, autentique de
novo no CLI correspondente e pressione `r`.

## Limite conhecido

As rotas de uso de assinatura são contratos internos dos provedores. Se uma
rota mudar, o painel mostra aquele provedor como indisponível; não estima cotas.
```

- [ ] **Step 2: Fazer a varredura contra vazamento de segredo**

Run:

```bash
rg -n 'access_token|refresh_token|Authorization: Bearer|\.credentials\.json|auth\.json' dashboard tests README.md
```

Expected: ocorrências somente na leitura de credencial e montagem de header em
`dashboard/providers.py`; nenhum `print`, logger, fixture real ou token literal.

- [ ] **Step 3: Rodar a verificação completa e a consulta manual**

Run:

```bash
python3 -m unittest discover -v
./dashboard
```

Expected: testes PASS; TUI mostra cada provedor autenticado com suas janelas ou
uma indicação segura de indisponibilidade. Encerrar com `q`.

- [ ] **Step 4: Revisar diff e criar commit final**

Run: `git diff --check && git status --short`

Expected: sem erro de whitespace; somente arquivos planejados aguardando commit.

```bash
git add README.md
git commit -m "docs: explain dashboard usage"
```
