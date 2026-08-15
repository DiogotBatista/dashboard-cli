# Dashboard CLI

Painel local, em terminal, para acompanhar as janelas de uso das assinaturas
do Codex e do Claude Code.

## Uso

```bash
./bin/dashboard
```

Para abrir de qualquer diretório, instale o lançador uma vez:

```bash
./bin/install
```

Depois use:

```bash
ai-dashboard
```

O instalador cria `~/.local/bin/ai-dashboard`. Se `ai-dashboard` não for
encontrado, inclua `~/.local/bin` no `PATH` da sua sessão.

O comando exige sessões ativas de `codex login` e `claude auth login`. Ele não
salva credenciais nem usa uma chave API. Caso uma sessão expire, autentique de
novo no CLI correspondente e pressione `r`.

O painel atualiza automaticamente a cada 60 segundos. Use `r` para atualizar
imediatamente e `q` ou `Ctrl-C` para sair.

## O que mostra

Para cada janela disponível, o painel exibe percentual gasto, percentual
restante, contagem regressiva e data/hora local de reinício. Se um provedor
falhar após uma leitura válida, os últimos valores ficam marcados como
desatualizados.

## Limite conhecido

As rotas de uso de assinatura são contratos internos dos provedores. Se uma
rota mudar, o painel mostra aquele provedor como indisponível; não estima
cotas.
