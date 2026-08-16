# Dashboard CLI

Painel local de terminal para acompanhar as janelas de uso das assinaturas do
Codex e do Claude Code. Não usa chave de API e não salva credenciais.

## Pré-requisitos

- Linux ou macOS com `python3` instalado.
- O CLI do Codex e/ou o Claude Code instalados e autenticados.

```bash
codex login
claude auth login
```

Você pode usar apenas um dos provedores: se o outro não estiver autenticado ou
disponível, o painel continua mostrando o que conseguir consultar.

## Instalação

Clone o repositório e instale o lançador:

```bash
git clone git@github.com:DiogotBatista/dashboard-cli.git
cd dashboard-cli
./bin/install
```

O instalador cria `~/.local/bin/ai-dashboard`. Para que o comando funcione em
todo novo terminal Bash, copie e execute esta linha uma única vez:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

Feche e abra o terminal, ou carregue a alteração agora:

```bash
source ~/.bashrc
```

## Primeiro uso

```bash
ai-dashboard
```

Também é possível abrir o painel a partir da pasta do repositório, sem instalar
o lançador:

```bash
./bin/dashboard
```

## Comandos

| Tecla | Ação |
| --- | --- |
| `r` | Atualiza os dados imediatamente. |
| `q` ou `Ctrl-C` | Fecha o painel. |

O painel atualiza automaticamente a cada 60 segundos.

## Problemas comuns

**`ai-dashboard: command not found`**

Execute `source ~/.bashrc` ou abra outro terminal. Se usar Zsh, troque
`~/.bashrc` por `~/.zshrc` no comando de instalação do `PATH`.

**Um provedor aparece como indisponível**

Faça login novamente no CLI correspondente (`codex login` ou `claude auth
login`) e pressione `r`. Se houver uma leitura anterior válida, ela permanece
na tela marcada como desatualizada.

## O que mostra

Para cada janela disponível, o painel exibe percentual gasto, percentual
restante, contagem regressiva e data/hora local de reinício. Se um provedor
falhar após uma leitura válida, os últimos valores ficam marcados como
desatualizados.

No Codex, a janela exibida é semanal (`7 dias`).

## Limite conhecido

As rotas de uso de assinatura são contratos internos dos provedores. Se uma
rota mudar, o painel mostra aquele provedor como indisponível; não estima
cotas.
