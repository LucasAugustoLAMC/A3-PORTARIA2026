# Portaria 2.1 — Especificação de Requisitos de Software (SRS)

**Sistema de Portaria — controle local de acessos** · Software versão 2.1.3 · Documento versão 2.0

## Controle do documento

| Item | Descrição |
|---|---|
| Produto | Portaria — Controle local de acessos (repositório `A3-PORTARIA2026`) |
| Versão do software | 2.1.3 |
| Versão do documento | 2.0 (substitui o SRS da v6, preservado em `docs/historico/`) |
| Data | 26/11/2026 |
| Autores | Lucas Augusto Morais Carvalho; Lucas Andrian Pieroni |
| Instituição / disciplina | Faculdade UNA — Ciência da Computação · Teoria da Computação e Compiladores |
| Orientação | Prof.ª Cíntia Silvana de Souza |
| Padrão seguido | Estrutura da IEEE 830-1998 e da ISO/IEC/IEEE 29148:2018, adaptada ao porte do projeto |

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 29/10/2026 | SRS do software v6.0 (arquivado) |
| 2.0 | 26/11/2026 | Reescrita para a versão 2.1.x: cadastro de pessoas, controle de entrada/saída, veículos, autorizações, relatórios e cofre criptografado |

## Sumário

1. Introdução
2. Descrição geral
3. Requisitos funcionais
4. Requisitos não funcionais
5. Regras de negócio
6. Matriz de permissões
7. Casos de uso
8. Interfaces com o usuário
9. Modelo de dados
10. Arquitetura (resumo)
11. Rastreabilidade requisitos × testes
12. Riscos, limitações e trabalhos futuros

---

## 1. Introdução

### 1.1 Propósito
Este documento especifica o **Portaria 2.1.3**, aplicativo desktop para cadastrar pessoas, registrar entradas e saídas em uma portaria, vincular veículos e placas, emitir autorizações de entrada antecipadas, gerar relatórios e manter trilha de auditoria. Destina-se à avaliação acadêmica (A3), à manutenção do código e à operação do sistema.

### 1.2 Escopo
**Inclui:** autenticação por cargo; cadastro de pessoas com código de identificação; controle de entrada e saída com horário do sistema; veículos e placas; autorizações de entrada; relatórios com gráficos e exportação CSV; auditoria; gestão de usuários; temas visuais; armazenamento local criptografado.

**Não inclui:** acesso em rede ou uso simultâneo por várias máquinas; servidor ou banco de dados SQL; envio de e-mail/SMS; leitura de documentos, QR code, câmeras ou catracas; aplicativo móvel; backup automático.

### 1.3 Definições e siglas

| Termo | Significado |
|---|---|
| SRS | Software Requirements Specification |
| RF / RNF / RN | Requisito funcional / não funcional / regra de negócio |
| UC / CT | Caso de uso / caso de teste |
| Admin Final | Cargo de maior nível, único, criado no primeiro acesso |
| Adm | Cargo intermediário: opera a portaria, autoriza, exporta e audita |
| Usuário | Cargo operacional restrito |
| Cofre | Arquivo `dados_portaria.enc`, que guarda todos os dados cifrados |
| Código | Identificador da pessoa (`P0001`…) ou da autorização (`A0001`…) |
| Situação | *Dentro* (existe entrada sem saída) ou *Saiu* |
| AES-GCM | Cifra autenticada de 256 bits usada no cofre |
| PBKDF2 | Função de derivação de chave/hash de senha |
| RBAC | Controle de acesso por papéis |
| LGPD | Lei Geral de Proteção de Dados (Lei 13.709/2018) |

### 1.4 Referências
IEEE 830-1998; ISO/IEC/IEEE 29148:2018; ISO/IEC 25010:2011; RFC 8018 (PBKDF2); Lei 13.709/2018; documentação do Python (`tkinter`, `csv`, `json`, `hashlib`) e da biblioteca `cryptography`; roteiro "Sistema de Portaria" (A3) da disciplina.

### 1.5 Convenções
Identificadores RF-nn, RNF-nn, RN-nn, UC-nn, CT-nn. Prioridade: **Essencial**, **Importante**, **Desejável**. Nomes em `crase` são arquivos, funções ou constantes reais do código.

---

## 2. Descrição geral

### 2.1 Perspectiva do produto
Aplicativo independente (stand-alone) em Python/Tkinter. Os dados ficam em um único cofre local criptografado, na pasta do projeto ou em pasta indicada por `--data-dir` / `PORTARIA_DATA_DIR`. Substitui o controle em papel por um sistema com permissões por cargo e auditoria.

### 2.2 Funções principais
1. Login (e-mail ou CPF), primeiro acesso, recuperação de senha, bloqueio por tentativas.
2. Cadastro de pessoas (código gerado, CPF único) e primeira entrada opcional.
3. Controle de entrada e saída com busca, filtro e bloqueio de entrada dupla.
4. Veículos e placas vinculados às pessoas.
5. Autorizações de entrada (consumidas automaticamente), com comprovante HTML.
6. Relatórios (indicadores, gráficos) e exportação CSV.
7. Auditoria e gestão de usuários e papéis.
8. Temas Claro, Escuro e Floresta; layout adaptativo.

### 2.3 Classes de usuários

| Cargo | Perfil | Resumo das capacidades |
|---|---|---|
| Admin Final | Responsável pelo sistema (único) | Tudo, inclusive gerir usuários |
| Adm | Supervisor da portaria | Tudo, exceto gerir usuários |
| Usuário | Porteiro / operador | Consultar, cadastrar, entrada, saída, veículos |

### 2.4 Ambiente operacional
Windows, Linux ou macOS com Python 3.10 ou superior e Tkinter; dependência externa única: `cryptography` (>=42,<48). Testes com `pytest`. Resolução mínima funcional: janelas estreitas passam ao modo alternado formulário/lista.

### 2.5 Restrições
Armazenamento local sem SQL (decisão do projeto, mantendo compatibilidade com o cofre v2); interface Tk/ttk (design próprio, sem toolkit de terceiros); o cofre deve continuar legível pela versão 2.0 até a primeira gravação das seções novas (ver RN-14).

### 2.6 Premissas e dependências
O computador da portaria é de uso controlado; o Admin Final guarda a senha e o código de recuperação; backups do cofre são feitos com a aplicação fechada.

---

## 3. Requisitos funcionais

### 3.1 Autenticação e sessão
| ID | Requisito | Prioridade |
|---|---|---|
| RF-01 | O sistema deve autenticar o usuário por e-mail ou CPF e senha, definindo o cargo a partir da conta, nunca de uma escolha no login. | Essencial |
| RF-02 | A tela de login deve ter logo, opção *Mostrar senha* e botão **Limpar**, e bloquear campos vazios com mensagem ("Informe o e-mail/CPF e a senha para entrar."), na tela e no serviço. | Essencial |
| RF-03 | Após 5 tentativas incorretas a conta deve ser bloqueada por 5 minutos; o Admin Final pode desbloquear. | Essencial |
| RF-04 | O primeiro acesso deve criar o Admin Final, o cofre e exibir uma única vez o código de recuperação. | Essencial |
| RF-05 | A recuperação de senha deve exigir CPF, e-mail e três desafios; emitir autorização de uso único com validade de 5 minutos. | Importante |
| RF-06 | O usuário deve poder encerrar a sessão (*Sair*). | Essencial |

### 3.2 Cadastro de pessoas
| ID | Requisito | Prioridade |
|---|---|---|
| RF-10 | O cadastro deve coletar Nome\*, CPF\*, Telefone\*, Empresa, Tipo de acesso\*, Data\*, Horário\* e Motivo\*. | Essencial |
| RF-11 | O CPF deve ser validado pelos dígitos verificadores e ser único. | Essencial |
| RF-12 | O sistema deve gerar o código de identificação sequencial (`P0001`, `P0002`…) e exibir confirmação. | Essencial |
| RF-13 | Os botões **Cadastrar**, **Limpar** e **Cancelar** devem estar disponíveis; campos obrigatórios vazios devem bloquear o envio com mensagem clara. | Essencial |
| RF-14 | CPF, telefone, data e horário devem ter máscara de digitação sem perda de dígitos. | Essencial |
| RF-15 | A caixa *Registrar a entrada neste horário* deve criar a primeira entrada junto ao cadastro. | Importante |
| RF-16 | Devem existir tipos de acesso fixos (Visitante, Morador, Entregador, Funcionário) e tipos temporários válidos por 24 h. | Importante |

### 3.3 Controle de entrada e saída
| ID | Requisito | Prioridade |
|---|---|---|
| RF-20 | A tela deve listar Código, Nome, CPF (mascarado), Tipo, Entrada, Saída, Situação e Placa. | Essencial |
| RF-21 | Deve haver busca por nome, CPF, código ou placa (sem diferenciar acentos/maiúsculas) e filtro **Todos / Dentro / Saiu**. | Essencial |
| RF-22 | **Registrar entrada** usa o horário do sistema; **Registrar saída** preenche a saída do registro aberto selecionado. | Essencial |
| RF-23 | Uma nova entrada deve ser bloqueada enquanto a pessoa estiver *Dentro*; saída já registrada não pode ser repetida. | Essencial |
| RF-24 | Devem existir **Atualizar**, **Voltar**, **Editar** e **Excluir** (os dois últimos conforme o cargo). | Importante |
| RF-25 | A edição deve recusar saída anterior à entrada e gravar todos os campos alterados em um único commit. | Importante |

### 3.4 Veículos e placas *(extra)*
| ID | Requisito | Prioridade |
|---|---|---|
| RF-30 | Cadastrar veículo com proprietário, placa\*, modelo\*, cor e tipo (Carro, Moto, Caminhão, Outro). | Importante |
| RF-31 | Aceitar placa no padrão antigo (ABC-1234) e Mercosul (ABC1D23), convertendo para maiúsculas; placa única. | Importante |
| RF-32 | Permitir escolher a placa do proprietário na entrada. | Importante |
| RF-33 | Remover veículo (Adm e Admin Final), exceto se houver autorização ativa para a placa. | Desejável |

### 3.5 Autorização de entrada *(extra)*
| ID | Requisito | Prioridade |
|---|---|---|
| RF-40 | Emitir autorização antecipada por pessoa (e, opcionalmente, placa) com data e horário limite e motivo. | Importante |
| RF-41 | A autorização deve ser consumida automaticamente na próxima entrada válida, uma única vez. | Importante |
| RF-42 | Cancelar autorização ativa e emitir comprovante em HTML. | Desejável |
| RF-43 | Não permitir duas autorizações ativas para a mesma pessoa e data. | Importante |

### 3.6 Relatórios, auditoria e usuários
| ID | Requisito | Prioridade |
|---|---|---|
| RF-50 | Mostrar indicadores (dentro agora, entradas e saídas de hoje, veículos) e gráficos de entradas nos últimos 7 dias, por tipo e por hora. | Importante |
| RF-51 | Exportar o controle de acesso em CSV (UTF-8 com BOM, separador `;`, CPF mascarado). | Importante |
| RF-52 | Registrar em auditoria edições, exclusões, veículos, autorizações, usuários, bloqueios e desbloqueios, com responsável e valores anterior/novo. | Essencial |
| RF-53 | O Admin Final deve criar usuários, alterar papéis, excluir e desbloquear contas. | Essencial |
| RF-54 | A tela *Início* deve resumir a operação e listar quem está dentro. | Desejável |
| RF-55 | O usuário deve escolher entre três temas, com preferência persistida. | Desejável |

---

## 4. Requisitos não funcionais

| ID | Categoria (ISO 25010) | Requisito |
|---|---|---|
| RNF-01 | Segurança | Dados em repouso cifrados com AES-256-GCM; chave derivada por PBKDF2 (600 000 iterações); senhas de contas com hash PBKDF2 individual. |
| RNF-02 | Segurança | Autorização verificada na camada de serviço, não apenas ocultando menus. |
| RNF-03 | Confiabilidade | Gravação atômica (arquivo temporário cifrado + `os.replace` + `fsync`); falha de gravação não altera o estado confirmado. |
| RNF-04 | Confiabilidade | Controle de concorrência otimista (revisão do cofre) e lock de instância por pasta de dados. |
| RNF-05 | Integridade | Operações compostas (ex.: consumo de autorização + entrada + auditoria) gravadas em um único commit. |
| RNF-06 | Usabilidade | Mensagens de erro objetivas; confirmação antes de saída/exclusão; máscaras de entrada; rolagem por mouse nos formulários. |
| RNF-07 | Usabilidade | Layout adaptativo (duas colunas em janelas largas, modo alternado em estreitas); três temas. |
| RNF-08 | Manutenibilidade | Camadas domain / application / infrastructure / presentation; serviços sem dependência do Tkinter. |
| RNF-09 | Testabilidade | Suíte automatizada com 60 testes (domínio, aplicação, cofre e interface em display virtual). |
| RNF-10 | Portabilidade | Biblioteca padrão + `cryptography`; executa em Windows, Linux e macOS. |
| RNF-11 | Privacidade | CPF mascarado em tabelas e CSV; dados pessoais fora do Git (`.gitignore`). |

---

## 5. Regras de negócio

| ID | Regra |
|---|---|
| RN-01 | CPF válido (11 dígitos, dígitos verificadores corretos, não repetido) e único no cadastro. |
| RN-02 | Telefone com DDD: 10 ou 11 dígitos; com 11, o terceiro dígito deve ser 9. |
| RN-03 | Nome: obrigatório, até 100 caracteres, sem caracteres de controle. Empresa até 80; motivo até 120 caracteres. |
| RN-04 | Data/hora no formato `dd/mm/aaaa hh:mm`, validada como data real de calendário. |
| RN-05 | A situação *Dentro* é derivada: existe registro da pessoa com saída vazia. |
| RN-06 | Entrada e saída usam o horário do sistema; a saída não pode ser anterior à entrada. |
| RN-07 | Uma pessoa *Dentro* não pode registrar nova entrada antes da saída. |
| RN-08 | Placas: padrão `AAA9999` ou Mercosul `AAA9A99`; únicas; só podem ser usadas pelo proprietário. |
| RN-09 | Autorização vale somente na data indicada, até o horário limite, com status *Ativa*; ao ser usada passa a *Utilizada*. |
| RN-10 | Tipos temporários expiram após 24 horas. |
| RN-11 | O Admin Final é único e não pode ser excluído ou rebaixado pela aplicação. |
| RN-12 | 5 tentativas de login incorretas bloqueiam a conta por 5 minutos. |
| RN-13 | A autorização de recuperação de senha é de uso único e expira em 5 minutos. |
| RN-14 | A primeira gravação de pessoas/veículos/autorizações cria seções novas no cofre; a partir daí a versão 2.0 não o abre mais. |

---

## 6. Matriz de permissões

| Capacidade (`Action`) | Admin Final | Adm | Usuário |
|---|:---:|:---:|:---:|
| Consultar registros (`consultar`) | ✔ | ✔ | ✔ |
| Cadastrar pessoa (`cadastrar`) | ✔ | ✔ | ✔ |
| Registrar entrada (`entrada`) | ✔ | ✔ | ✔ |
| Registrar saída (`saida`) | ✔ | ✔ | ✔ |
| Cadastrar veículos (`veiculos`) | ✔ | ✔ | ✔ |
| Editar registros (`editar`) | ✔ | ✔ | — |
| Excluir registros / remover veículos (`excluir`) | ✔ | ✔ | — |
| Autorizar entradas (`autorizar`) | ✔ | ✔ | — |
| Exportar CSV (`exportar`) | ✔ | ✔ | — |
| Consultar auditoria (`auditoria`) | ✔ | ✔ | — |
| Gerir usuários (`usuarios`) | ✔ | — | — |

---

## 7. Casos de uso

| ID | Caso de uso | Ator | Fluxo principal | Fluxos alternativos |
|---|---|---|---|---|
| UC-01 | Entrar no sistema | Todos | Informa e-mail/CPF e senha → sistema valida → abre o painel. | Campos vazios (RF-02); senha incorreta; conta bloqueada (RF-03). |
| UC-02 | Cadastrar pessoa | Todos | Preenche o formulário → **Cadastrar** → sistema valida, gera `P000n` e registra a entrada. | CPF inválido/duplicado; campo obrigatório vazio; **Limpar**/**Cancelar**. |
| UC-03 | Registrar entrada | Todos | Seleciona a pessoa (e veículo/autorização) → **Registrar entrada**. | Pessoa já *Dentro* (bloqueio); placa de outra pessoa; autorização vencida. |
| UC-04 | Registrar saída | Todos | Seleciona o registro aberto → **Registrar saída** → confirma. | Saída já registrada. |
| UC-05 | Consultar acessos | Todos | Digita busca e/ou escolhe filtro → tabela atualiza. | Nenhum resultado (tabela vazia). |
| UC-06 | Cadastrar veículo | Todos | Escolhe proprietário, informa placa, modelo, cor, tipo → **Cadastrar veículo**. | Placa inválida/duplicada. |
| UC-07 | Emitir autorização | Adm, Admin Final | Escolhe pessoa, data/limite, motivo, veículo → **Autorizar entrada**. | Limite no passado; autorização ativa duplicada; placa de outra pessoa. |
| UC-08 | Emitir comprovante | Adm, Admin Final | Seleciona a autorização → **Comprovante** → escolhe onde salvar o HTML. | Cancelar o diálogo. |
| UC-09 | Gerar relatório / CSV | Adm, Admin Final | Abre *Relatórios* → **Exportar CSV** → escolhe arquivo. | Erro de gravação (mensagem). |
| UC-10 | Gerir usuários | Admin Final | *Usuários e permissões* → Novo usuário / Alterar papel / Desbloquear / Excluir. | Tentativa de excluir o Admin Final (bloqueada). |
| UC-11 | Consultar auditoria | Adm, Admin Final | Abre *Auditoria* → filtra por tipo de evento. | — |
| UC-12 | Recuperar senha | Usuário com conta | *Esqueci minha senha* → CPF, e-mail e desafios → define nova senha. | Falhas contam para bloqueio; autorização expira em 5 min. |

---

## 8. Interfaces com o usuário

Janela única com barra lateral: **Início, Cadastro, Controle de acesso, Veículos, Autorizações, Relatórios, Auditoria, Usuários e permissões, Aparência e sistema, Sair** (itens exibidos conforme o cargo). As capturas estão em `docs/v21_*.png`. Detalhes de uso no [Manual do usuário](MANUAL_DO_USUARIO.md).

---

## 9. Modelo de dados

O cofre contém sete coleções lógicas (arquivo binário `PORTARIA-COFRE-v2`, AES-256-GCM). Descrição completa em [MODELO_DE_DADOS.md](MODELO_DE_DADOS.md).

| Coleção | Chave | Conteúdo |
|---|---|---|
| registros | `Id` | Entradas e saídas (Nome, Tipo, Entrada, Saída, Código, Placa, Autorização, Motivo) |
| auditoria | — | Eventos (Quando, Ação, Id, Nome, Campo, Anterior, Novo, Usuário) |
| tipos temporários | Tipo | Tipos criados na hora (válidos por 24 h) |
| usuários | `Id` | Contas, cargo, hashes, bloqueio |
| pessoas | `Codigo` | Cadastro de pessoas |
| veículos | `Id` | Placas vinculadas |
| autorizações | `Id` (`A0001`…) | Autorizações de entrada |

---

## 10. Arquitetura (resumo)

Camadas `presentation_v2` (Tk/ttk) → `application` (`PortariaService` + operações de acesso, identidade, portaria e cofre) → `domain` (validação, permissões, segurança) e `infrastructure` (cofre AES-GCM, lock). Detalhes e diagramas em [ARQUITETURA_V2.md](ARQUITETURA_V2.md).

---

## 11. Rastreabilidade requisitos × testes

Os testes automatizados estão em `tests/`. A tabela relaciona requisitos aos testes que os exercitam; a execução manual (QA no Windows) está em [PLANO_DE_TESTES_E_QA.md](PLANO_DE_TESTES_E_QA.md).

| Requisitos | Testes automatizados |
|---|---|
| RF-01, RF-02, RF-03 | `test_login_vazio_e_bloqueado`, `test_login_vazio_limpar_e_logo`, `test_login_bloqueio_e_redefinicao` |
| RF-04, RNF-01 | `test_base_vazia_cria_cofre_sem_csv_ou_json_legivel`, `test_senha_correta_abre_e_errada_nao_altera_dados` |
| RF-05, RN-13 | `test_recuperacao_exige_prova_valida_expira_e_uso_unico` |
| RF-10…RF-13, RN-01…RN-04 | `test_validadores`, `test_cadastro_gera_codigo_e_primeira_entrada`, `test_cadastro_rejeita_duplicado_e_dados_invalidos`, `test_cadastro_pessoa_formata_valida_e_gera_codigo` |
| RF-14 | `test_digitacao_real_do_cpf_nao_perde_digitos`, `test_data_aceita_parciais_e_datas_reais`, `test_mask_rejeita_emoji_e_valor_impossivel` |
| RF-20…RF-23, RN-05…RN-07 | `test_segunda_entrada_exige_saida_previa`, `test_consulta_busca_por_nome_cpf_e_situacao`, `test_saida_com_entrada_no_futuro_e_bloqueada`, `test_controle_entrada_saida_busca_filtro_e_bloqueio` |
| RF-25, RNF-05 | `test_edicao_multicampo_atomica_e_auditoria`, `test_multicampo_invalido_nao_persiste_nada`, `test_registro_e_auditoria_gravados_num_unico_commit` |
| RF-30…RF-33, RN-08 | `test_veiculos`, `test_veiculo_e_autorizacao_pela_interface` |
| RF-40…RF-43, RN-09 | `test_autorizacao_e_consumida_na_entrada`, `test_autorizacao_vencida_cancelada_e_validacoes` |
| RF-50, RF-51 | `test_estatisticas_e_exportacao`, `test_relatorios_e_graficos_desenham` |
| RF-52, RF-53, RN-11 | `test_crud_auditoria_e_releitura`, `test_correcao_de_cargo_e_criacao_de_tipo_exigem_permissao` |
| RF-55, RNF-07 | `test_navegacao_completa_e_temas`, `test_janela_compacta_modo_alternavel`, `test_primeiro_acesso_cabe_e_pode_rolar_ate_salvar` |
| RNF-02 | `test_permissoes_por_cargo`, `test_permissoes_refletidas_na_navegacao`, `test_validacao_e_permissoes` |
| RNF-03, RNF-04 | `test_falha_escrita_cofre_nao_altera_estado_ou_arquivo`, `test_detecta_adulteracao_entre_leitura_e_gravacao`, `test_lock_da_instancia` |
| RN-14 | `test_cofre_anterior_sem_secoes_novas_abre_e_evolui` |

---

## 12. Riscos, limitações e trabalhos futuros

**Limitações conhecidas**
1. Não protege contra quem administra a máquina (cópia/substituição de arquivos, rollback de backup). Ver [SEGURANCA_E_LIMITACOES.md](SEGURANCA_E_LIMITACOES.md).
2. O cofre é regravado por inteiro a cada operação; volumes grandes exigiriam outro formato de armazenamento.
3. A recuperação por desafios é legada e tem entropia limitada.
4. Uso em uma única máquina; sem acesso simultâneo em rede.
5. A interface foi validada por testes em display virtual Linux e por QA manual no Windows; acessibilidade (leitores de tela, alto contraste) não foi auditada.
6. Na edição de um registro, um erro de validação fecha o diálogo e descarta o que foi digitado (item aberto, ver plano de testes).

**Trabalhos futuros:** banco SQL e acesso em rede; recuperação de conta com segundo fator; leitura de QR code/documento; backup automático; relatórios em PDF; suporte a CNPJ; auditoria de acessibilidade.
