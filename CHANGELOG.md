# Histórico de mudanças

## 2.1.3 — correções do 2º Q/A no Windows e documentação
- Documentação completa: README, SRS da 2.1 (o da v6 foi para `docs/historico/`), manual do usuário, modelo de dados e plano de testes com relatório de QA.
- "Esqueci minha senha" mostrava "Erro inesperado": o ajuste de quebra de texto da 2.1.2 era chamado para rótulos já destruídos ao trocar de tela (Windows/Python 3.15). A chamada agora ignora rótulos inexistentes.
- Exportar CSV: no Windows o botão não abria o diálogo "Salvar como". Causa provável (ainda a confirmar na máquina): rótulo de filtro com parênteses (`CSV (Excel)`); rótulo simplificado e filtro "Todos os arquivos" adicionado.

## 2.1.2 — ajustes do QA no Windows

- Textos longos dos painéis laterais passam a quebrar conforme a largura real (antes ficavam cortados).
- Roda do mouse rola o formulário também sobre campos e botões (Limpar/Cancelar ficavam fora de vista).
- Mensagens de nome vazio/sem sobrenome mais claras no cadastro de usuários.

## 2.1.1 — correção das máscaras

- CPF, telefone e placa deixam de perder/empurrar dígitos ao digitar (`FormattedEntry` reformata no `KeyRelease` e reposiciona o cursor); teste de digitação real incluído.

## 2.1.0 — roteiro "Sistema de Portaria" (A3)

- Novas telas no menu lateral: **Início**, **Cadastro**, **Controle de acesso**, **Veículos**, **Autorizações**, **Relatórios** (Auditoria, Usuários e Aparência mantidos; "Sair").
- Cadastro de pessoas com CPF validado e único, telefone, empresa, tipo, data/horário, motivo e código gerado (P0001…).
- Controle de entrada e saída com busca por nome/CPF/código/placa, filtro Todos/Dentro/Saiu, horário automático e bloqueio de segunda entrada sem saída.
- Extras: veículos e placas (padrão antigo e Mercosul) e autorizações de entrada (consumo único, cancelamento, comprovante HTML).
- Relatórios com gráficos em Canvas e exportação CSV (CPF mascarado).
- Login com logo, botão Limpar e bloqueio de campos vazios.
- Cofre: três seções opcionais novas (`pessoas`, `veiculos`, `autorizacoes`); cofres 2.0 abrem sem conversão. Registros ganham colunas opcionais `Codigo`, `Placa`, `Autorizacao`, `Motivo`.
- Permissões novas: `entrada`, `veiculos`, `autorizar`, `exportar`.
- Auditoria registra veículos e autorizações; novos filtros.
- Testes: `tests/test_gate.py` (regras de negócio e compatibilidade do cofre) e novos testes de interface (58 no total).

## 2.0.1 — correção de formulário cortado

- Adiciona rolagem vertical com barra visível, roda do mouse e deslocamento ao focar campos fora da tela nos formulários de autenticação.
- Centraliza os cartões apenas quando cabem; remove largura mínima artificial que cortava formulários menores.
- Reorganiza o formulário de primeiro acesso e novos usuários em uma coluna na largura compacta.
- Faz a janela de cadastro de usuários rolável e reduz a dimensão mínima do desktop para suportar resoluções menores.
- Inclui testes gráficos de rolagem, botão final visível e alternância entre layouts estreito/amplo.

## 2.0 — nova interface e reforço de arquitetura

- Substitui a apresentação antiga por `presentation_v2` com tema Claro, Escuro e Floresta e composição adaptativa desktop.
- Divide as operações da aplicação entre acesso, identidade e ciclo de vida do cofre, com fachada `PortariaService` preservada.
- Centraliza RBAC em `domain/permissions.py`; a UI reflete as capacidades, mas não é a barreira de autorização.
- Introduz chave de operação para idempotência de cadastro persistente no ID, guarda contra reentrância e edição multicoluna atômica.
- Audita cadastro de usuários, alterações de papéis, desbloqueios, exclusões e tipos temporários sem armazenar senhas na auditoria.
- Recuperação de contas passa a usar token efêmero validado na aplicação, de uso único.
- Implementa lock de instância local e detecção otimista de mudanças externas no arquivo criptografado.
- Mantém cofre **PORTARIA-COFRE-v2** original com AES-256-GCM e compatibilidade de hashes de contas.
- Adiciona `--data-dir` para selecionar a pasta de dados (padrão anterior mantido).
- Substitui testes da UI antiga por testes de versão 2; inclui documentação das 10 heurísticas e modelo de ameaças.

## Compatibilidade

**Cofres 2.0 abrem na 2.1 sem conversão, mas, depois da primeira gravação das novas seções, a 2.0 não consegue mais abrir o cofre — faça backup.** Para migrar CSVs/JSON legados, siga `README.md`. Não distribua arquivos de dados reais junto do projeto.
