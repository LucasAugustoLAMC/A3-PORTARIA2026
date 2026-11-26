# Manual do usuário — Portaria 2.1

## 1. Primeiros passos

### Instalação
1. Instale o **Python 3.10 ou superior** (no Windows, marque *Add Python to PATH*; no Ubuntu/Debian, `sudo apt install python3-tk`).
2. Na pasta do projeto, instale a dependência e abra o programa:

```bash
python -m pip install -r requirements.txt
python cadastro_portaria.py
```

No Windows, se `python` não funcionar, use `py`. Para guardar os dados em outra pasta: `python cadastro_portaria.py --data-dir "C:\DadosPortaria"`.

### Primeiro acesso
Na primeira execução o programa pede a criação do **Admin Final**: nome completo, nome de exibição, e-mail, CPF, senha forte e **três palavras-chave** (4 a 20 letras, todas diferentes). Ao concluir, o sistema mostra o **código de recuperação do cofre uma única vez**. **Anote-o e guarde fora do computador**: com ele (ou com a senha) é possível reabrir os dados.

### Login
Entre com **e-mail ou CPF** e a senha. O botão **Limpar** esvazia os campos; *Mostrar senha* revela o que foi digitado. Após **5 tentativas erradas** a conta fica bloqueada por 5 minutos (o Admin Final pode desbloquear). Em *Esqueci minha senha*, informe CPF, e-mail e responda aos desafios.

## 2. Navegação

O menu lateral (ocultável pelo botão ☰) tem: **Início, Cadastro, Controle de acesso, Veículos, Autorizações, Relatórios, Auditoria, Usuários e permissões, Aparência e sistema** e **Sair**. Itens sem permissão para o seu cargo não aparecem. Campos marcados com **\*** são obrigatórios. Em janelas pequenas, a tela alterna entre formulário e lista e o formulário rola com o mouse.

## 3. Início
Mostra quantas pessoas estão dentro, as entradas e saídas de hoje, as pessoas cadastradas e as autorizações ativas, com atalhos (*Cadastrar pessoa*, *Registrar entrada/saída*, *Ver relatórios*) e a lista de quem está dentro agora.

## 4. Cadastrar uma pessoa
1. Abra **Cadastro**.
2. Preencha **Nome**, **CPF**, **Telefone**, Empresa (opcional), **Tipo de acesso**, **Data e horário** (botão *Usar data e hora atuais*) e **Motivo**.
3. Mantenha marcada *Registrar a entrada neste horário* para já lançar a entrada.
4. Clique em **Cadastrar**. O sistema confirma e informa o **código** (ex.: P0003).

Os campos de CPF, telefone, data e hora formatam sozinhos enquanto você digita — digite só os números. **Limpar** esvazia o formulário; **Cancelar** volta ao início. O botão **+ Tipo** cria um tipo de acesso temporário válido por 24 horas.

**Mensagens comuns:** "Informe o motivo do acesso", "CPF inválido", "CPF já cadastrado. Use o Controle de acesso para registrar a entrada" e "Telefone inválido. Use DDD + número".

## 5. Controle de entrada e saída
- **Registrar entrada (painel esquerdo):** escolha a pessoa (busque por nome, CPF ou código), opcionalmente o veículo e a autorização, e clique em **Registrar entrada**. O horário é o do sistema. Se a pessoa já estiver *Dentro*, o sistema bloqueia e pede a saída antes.
- **Registrar saída:** selecione o registro na tabela e clique em **Registrar saída** → **Sim**.
- **Buscar e filtrar:** digite nome, CPF, código ou placa na busca e use o filtro **Todos / Dentro / Saiu**.
- **Atualizar** recarrega a tabela; **Voltar** retorna ao início.
- **Editar** e **Excluir** (Adm e Admin Final) corrigem ou removem registros e ficam na auditoria. Na edição, a saída não pode ser anterior à entrada.

O CPF aparece mascarado (`***.***.286-57`); a busca aceita o CPF completo.

## 6. Veículos e placas
Em **Veículos**, escolha o proprietário, informe a **placa** (ABC-1234 ou ABC1D23; vira maiúscula sozinha), o **modelo**, a cor e o tipo e clique em **Cadastrar veículo**. A placa é única. Na entrada, selecione o veículo do campo *Veículo (opcional)*. **Remover** (Adm e Admin Final) não é permitido se houver autorização ativa para a placa.

## 7. Autorização de entrada
(Adm e Admin Final.) Em **Autorizações**, escolha a pessoa, a data e o **horário limite**, o motivo e, se quiser, o veículo; clique em **Autorizar entrada**. A autorização vale só naquele dia e até o horário limite e é **consumida automaticamente** na próxima entrada da pessoa (passa a *Utilizada*). Selecione uma autorização para **Cancelar autorização** ou gerar o **Comprovante** (arquivo HTML que pode ser impresso).

## 8. Relatórios
Mostra indicadores e três gráficos: entradas nos últimos 7 dias, por tipo de acesso e por hora do dia. **Exportar CSV** (Adm e Admin Final) salva o controle de acesso em arquivo UTF-8 com separador `;`, que abre direto no Excel, com o CPF mascarado.

## 9. Auditoria
(Adm e Admin Final.) Lista edições, exclusões, veículos, autorizações e eventos de usuários, com responsável, valor anterior e novo. Use o filtro *Mostrar* para ver só um tipo de evento.

## 10. Usuários e permissões
(Admin Final.) **+ Novo usuário** cria contas Adm ou Usuário; **Alterar papel**, **Desbloquear** (contas bloqueadas por tentativas) e **Excluir** completam a gestão. O Admin Final não pode ser excluído nem rebaixado.

| Capacidade | Admin Final | Adm | Usuário |
|---|:---:|:---:|:---:|
| Consultar, cadastrar, entrada, saída, veículos | ✔ | ✔ | ✔ |
| Editar, excluir, autorizar, exportar, auditoria | ✔ | ✔ | — |
| Gerir usuários | ✔ | — | — |

## 11. Aparência
Em **Aparência e sistema** escolha o tema **Claro**, **Escuro** ou **Floresta**. A escolha fica salva.

## 12. Backup e cuidados
- Feche o programa e copie `dados_portaria.enc` regularmente para um local seguro; guarde a senha e o código de recuperação separadamente.
- Não apague nem edite o cofre com o programa aberto.
- **Não publique** o cofre, logs ou backups em repositórios.
- Antes de atualizar de uma versão 2.0 para a 2.1, faça backup: depois da atualização a 2.0 não abre mais o cofre.

## 13. Solução de problemas

| Sintoma | O que fazer |
|---|---|
| "A criptografia exige a biblioteca cryptography" | `python -m pip install -r requirements.txt` |
| `tkinter` não encontrado (Linux) | `sudo apt install python3-tk` |
| "Conta bloqueada" | Aguarde 5 minutos ou peça ao Admin Final para **Desbloquear** |
| Esqueci a senha do Admin Final | Use o **código de recuperação** do cofre ao abrir |
| Mensagem de "Erro inesperado" | Consulte `portaria.log` na pasta de dados e informe os autores |
| Outro programa já usa a pasta de dados | Feche a outra janela do Portaria (apenas uma instância por pasta) |
