# Dashboard CLI — Design do MVP

## Goal

Disponibilizar, no Ubuntu sob WSL, um comando que abre um TUI persistente para
mostrar o uso de assinaturas do Codex e do Claude Code em suas janelas de 5
horas e 7 dias.

## Context

O usuário já utiliza ambos os CLIs autenticados por assinatura. O painel deve
funcionar sem iniciar uma sessão de agente, sem navegador e sem publicar um
serviço na rede.

## Constraints

- Consultar os dados autoritativos de uso por meio das sessões autenticadas
  existentes, somente em memória.
- Não gravar, registrar ou exibir credenciais, tokens de acesso ou respostas
  brutas dos provedores.
- Não estimar uma cota quando a consulta falhar.
- Usar o fuso local do WSL para datas e horas exibidas.
- Não incluir banco, histórico, gráficos, alertas, configuração persistida ou
  empacotamento global no MVP.

## Done when

O comando abre um TUI que, para Codex e Claude Code, mostra em cada janela
disponível:

- percentual gasto e percentual restante;
- contagem regressiva até o reinício;
- data e hora local do reinício;
- estado de atualização ou indisponibilidade.

O painel atualiza automaticamente a cada 60 segundos, aceita `r` para
atualização imediata e encerra com `q` ou `Ctrl-C`.

## Arquitetura

```text
dashboard (TUI)
  ├─ CodexAdapter  → sessão local → consulta de uso
  ├─ ClaudeAdapter → sessão local → consulta de uso
  └─ atualização a cada 60 s → renderização
```

Cada adaptador é responsável exclusivamente por obter e normalizar a resposta
do seu provedor. Ambos entregam ao TUI uma lista de janelas com:

- nome da janela;
- percentual restante;
- instante de reinício;
- instante da consulta;
- erro opcional.

O percentual gasto é derivado no TUI como `100 - percentual restante`.
Adaptadores não compartilham credenciais nem detalhes de endpoint.

## Fluxo e resiliência

1. Na abertura, o TUI consulta Codex e Claude Code em paralelo.
2. Renderiza cada resposta logo que disponível e agenda a próxima consulta para
   60 segundos depois.
3. Entre consultas, a contagem regressiva e o horário de reinício são
   recalculados localmente a cada segundo.
4. Se um provedor falhar e houver leitura anterior, ela permanece visível com
   indicação de desatualizada e causa curta.
5. Se não houver leitura anterior, apenas aquele provedor fica como
   `indisponível`; o outro continua operante.

## Interface

```text
AI Usage Dashboard                         atualizado agora
─────────────────────────────────────────────────────────
Codex
  5 h     38% gasto · 62% restante     em 02:14:08 · hoje, 19:30
  7 dias  52% gasto · 48% restante     em 3d 11:42:08 · 19/08, 05:00

Claude Code
  5 h     29% gasto · 71% restante     em 01:06:31 · hoje, 18:22
  7 dias  indisponível                 última leitura: —

[r] atualizar   [q] sair   próxima consulta em 00:47
```

Os valores acima são ilustrativos. Quando uma janela não for fornecida pelo
provedor, ela será indicada como indisponível, sem inferência.

## Verificação

- Testes unitários para normalização das janelas, cálculo de gasto e formatação
  de tempo/data no fuso local.
- Testes para atualização da contagem regressiva e falha isolada de adaptador.
- Execução manual autenticada para cada provedor, sem imprimir segredos.
