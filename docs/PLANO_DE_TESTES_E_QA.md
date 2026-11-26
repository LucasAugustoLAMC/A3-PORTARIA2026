# Plano de testes e relatório de QA — Portaria 2.1.3

**Data:** 26/11/2026 · **Responsáveis:** Lucas Augusto Morais Carvalho e Lucas Andrian Pieroni · **Ambiente do QA manual:** Windows 11, Python 3.15, resolução 1456×819, tema Escuro

## 1. Estratégia

| Nível | Ferramenta | Objetivo |
|---|---|---|
| Unitário / domínio | `pytest` | Validadores (CPF, telefone, placa, datas), permissões, hashes |
| Aplicação / serviço | `pytest` | Regras de negócio: cadastro, entrada/saída, veículos, autorizações, auditoria |
| Infraestrutura | `pytest` | Cofre AES-GCM, gravação atômica, adulteração, migração, lock |
| Interface (Tk) | `pytest` + `xvfb-run` | Navegação, formulários, digitação real tecla a tecla, relatórios, layout compacto |
| Aceite manual | Execução no Windows | Fluxos completos com dados de teste |

Execução da suíte automatizada:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q            # Linux headless: xvfb-run -a python -m pytest -q
```

**Resultado (26/11/2026): 60 testes aprovados, 53 subtestes aprovados.** Testes de interface são pulados quando não há display.

| Arquivo | Testes | Foco |
|---|:---:|---|
| `tests/test_gate.py` | 15 | Pessoas, entrada/saída, veículos, autorizações, permissões, CSV, compatibilidade do cofre |
| `tests/test_service.py` | 8 | CRUD, auditoria, migração legada, falhas de gravação |
| `tests/test_security_v2.py` | 8 | Idempotência, edição atômica, recuperação de senha, concorrência, lock |
| `tests/test_vault.py` | 10 | Cofre: criação, senha, adulteração, recuperação, migração, commit único |
| `tests/test_input_masks.py` | 4 | Máscaras de data e hora |
| `tests/test_ui_v2.py` | 15 | Interface gráfica real |

A rastreabilidade requisito × teste está na seção 11 do [SRS](SRS_PORTARIA_2_1.md).

## 2. Casos de teste manuais (aceite no Windows)

Dados usados: Admin Final com CPF 069.156.286-57; segundo CPF reservado 949.499.726-34; e-mail de exemplo `exemplo@email.com`.

| ID | Caso | Resultado esperado | Resultado |
|---|---|---|---|
| CT-01 | Login com campos vazios | Mensagem "Informe o e-mail/CPF e a senha para entrar." | Aprovado |
| CT-02 | Login por CPF com senha correta | Abre o painel | Aprovado |
| CT-03 | Login com senha errada | "E-mail/CPF ou senha incorretos." | Aprovado |
| CT-04 | 5 senhas erradas seguidas | Conta bloqueada ("Conta bloqueada. Tente novamente mais tarde.") | Aprovado |
| CT-05 | Admin desbloqueia conta | Status volta a *Ativo*; evento DESBLOQUEIO na auditoria | Aprovado |
| CT-06 | Digitar CPF `06915628657` direto | Campo exibe `069.156.286-57` sem perder dígitos | Aprovado |
| CT-07 | Digitar telefone `31987654321` | `(31) 98765-4321` | Aprovado |
| CT-08 | Cadastrar sem motivo | Mensagem "Informe o motivo do acesso." | Aprovado |
| CT-09 | Cadastro válido | Código `P0003`, entrada registrada, confirmação | Aprovado |
| CT-10 | CPF repetido | "CPF já cadastrado…" | Aprovado |
| CT-11 | CPF `111.111.111-11` | "CPF inválido." | Aprovado |
| CT-12 | Botão **Limpar** do cadastro | Formulário esvaziado | Aprovado |
| CT-13 | Registrar saída | Horário preenchido; situação *Saiu*; contador de "dentro" diminui | Aprovado |
| CT-14 | Saída repetida | "Este registro já possui saída." | Aprovado |
| CT-15 | Nova entrada após saída | Novo registro criado | Aprovado |
| CT-16 | Entrada com pessoa *Dentro* | Bloqueio pedindo saída antes | Aprovado |
| CT-17 | Busca por nome / CPF / texto inexistente | Filtra corretamente; tabela vazia quando não há resultado | Aprovado |
| CT-18 | Filtro Dentro / Saiu / Todos | Lista conforme a situação | Aprovado |
| CT-19 | Editar com saída anterior à entrada | "A saída não pode ser anterior à entrada." | Aprovado (ver defeito D-04) |
| CT-20 | Relatórios | Indicadores e gráficos coerentes com os registros | Aprovado |
| CT-21 | Cadastrar veículo (placa minúscula) | Placa salva em maiúsculas | Aprovado |
| CT-22 | Placa duplicada | "Placa já cadastrada." | Aprovado |
| CT-23 | Emitir autorização | Autorização `A0002` *Ativa*; contador de ativas sobe | Aprovado |
| CT-24 | Comprovante da autorização | Diálogo de salvar; HTML gravado | Aprovado |
| CT-25 | Auditoria | Eventos de cadastro, bloqueio, desbloqueio, veículo e autorização | Aprovado |
| CT-26 | Persistência | Dados de execuções anteriores presentes ao reabrir | Aprovado |
| CT-27 | Exportar CSV | Diálogo de salvar e arquivo `.csv` | **Pendente** — botão sem resposta na 2.1.2; correção na 2.1.3 aguardando confirmação (D-02) |
| CT-28 | Abrir *Esqueci minha senha* | Tela de recuperação sem erro | **Pendente** — "Erro inesperado" na 2.1.2; correção na 2.1.3 aguardando confirmação (D-01) |
| CT-29 | Concluir recuperação de senha | Nova senha definida | Não executado (evitar alterar a senha do Admin) |
| CT-30 | Login do perfil Usuário (RBAC) | Menu restrito | Não executado nesta rodada (senha da conta de teste não disponível); coberto por `test_permissoes_refletidas_na_navegacao` |

## 3. Defeitos encontrados e tratamento

| ID | Versão | Descrição | Causa | Correção | Situação |
|---|---|---|---|---|---|
| D-00 | 2.1.0 | Máscara de CPF/telefone/placa "empurrava" dígitos ao digitar (123.456.789-00 virava 123.567.890-04) | Reformatação via `textvariable` durante a inserção | `FormattedEntry` reformatado no `KeyRelease`, com reposicionamento do cursor; teste de digitação real | Corrigido na 2.1.1; confirmado no Windows |
| D-01 | 2.1.2 | "Esqueci minha senha" mostra "Erro inesperado" | Ajuste de quebra de texto chamado para rótulo já destruído ao trocar de tela (`TclError` no `portaria.log`) | Callback ignora rótulos inexistentes (`theme.py`) | Corrigido na 2.1.3; **a confirmar no Windows** (o teste automático não reproduz a falha) |
| D-02 | 2.1.2 | **Exportar CSV** não abre o diálogo de salvar no Windows | Causa provável: rótulo do filtro do diálogo com parênteses (`CSV (Excel)`); não reproduzido fora do Windows | Rótulo simplificado e filtro "Todos os arquivos" (`gate_pages.py`) | Corrigido na 2.1.3; **a confirmar no Windows** |
| D-03 | 2.1.1 | Textos longos nos painéis laterais cortados; botões Limpar/Cancelar ocultos; sem rolagem do mouse sobre campos; mensagem de nome vazio pouco clara | Largura fixa de `wraplength`; eventos de roda não propagados | Quebra pela largura real, rolagem recursiva, mensagem "Informe o nome completo." | Corrigido na 2.1.2 e confirmado |
| D-04 | 2.1.3 | Ao falhar a validação na edição de registro, o diálogo fecha e os dados digitados se perdem | O diálogo é fechado antes de tratar o erro | — | **Aberto** (melhoria planejada) |
| D-05 | 2.1.3 | Tabela vazia (busca sem resultado) não exibe mensagem "Nenhum resultado" | Não implementado | — | **Aberto** (cosmético) |
| D-06 | 2.1.3 | Um teste de interface (`test_digitacao_real_do_cpf_nao_perde_digitos`) falhou uma vez em lote e passou nas demais execuções | Provável dependência do foco da janela em display virtual | — | Observado; em acompanhamento |

## 4. Critérios de aceite da versão

- Suíte automatizada sem falhas (60/60).
- CT-01 a CT-26 aprovados no Windows.
- CT-27 e CT-28 confirmados após aplicar a 2.1.3 (pendentes).

## 5. Ambiente e como repetir

1. `python -m pip install -r requirements-dev.txt`.
2. `python -m pytest -q` (ou `xvfb-run -a python -m pytest -q` no Linux sem display).
3. Para o aceite manual: `python cadastro_portaria.py --data-dir <pasta de teste>` e percorrer a seção 2 com os dados de teste (CPFs válidos de teste, e-mail de exemplo e três palavras-chave de exemplo).
