# Modelo de dados — Portaria 2.1

Todos os dados ficam em **um único arquivo**, `dados_portaria.enc`, cifrado com **AES-256-GCM**. Não há SQLite nem arquivos legíveis em uso normal. Dentro do cofre existem sete seções lógicas, cada uma com o formato dos arquivos de origem (CSV ou JSON) para manter compatibilidade com as versões anteriores.

## Visão geral

```text
pessoas (1) ───< registros (N)         registro.Codigo → pessoa.Codigo
pessoas (1) ───< veículos (N)          veículo.Codigo  → pessoa.Codigo
pessoas (1) ───< autorizações (N)      autorização.Codigo → pessoa.Codigo
autorização (1) ──(consumida em)── (0..1) registro   registro.Autorizacao → autorização.Id
veículo.Placa ── (opcional) ── registro.Placa / autorização.Placa
usuários ─── geram ───> auditoria (campo Usuario)
```

A situação **Dentro/Saiu** não é armazenada: é derivada (existe registro da pessoa com `Saida` vazia).

## Seções

### registros (`registros_portaria.csv`)
| Coluna | Descrição |
|---|---|
| `Id` | Identificador único (8 caracteres hexadecimais) |
| `Nome` | Nome da pessoa no momento do registro |
| `Tipo` | Tipo de acesso (fixo ou temporário) |
| `Entrada` | `dd/mm/aaaa hh:mm` |
| `Saida` | `dd/mm/aaaa hh:mm`; vazia enquanto a pessoa está dentro |
| `Codigo` *(2.1)* | Código da pessoa (`P0001`); vazio em registros antigos |
| `Placa` *(2.1)* | Placa usada na entrada, sem hífen |
| `Autorizacao` *(2.1)* | Id da autorização consumida (`A0001`) |
| `Motivo` *(2.1)* | Motivo do acesso |

### pessoas (`pessoas_portaria.json`) *(2.1)*
`Codigo` (chave, `P0001`…), `Nome`, `CPF` (11 dígitos, único), `Telefone`, `Empresa`, `Tipo`, `Motivo`, `CriadoEm`.

### veículos (`veiculos_portaria.json`) *(2.1)*
`Id`, `Codigo` (proprietário), `Placa` (única), `Modelo`, `Cor`, `Tipo` (Carro, Moto, Caminhão, Outro), `CriadoEm`.

### autorizações (`autorizacoes_portaria.json`) *(2.1)*
`Id` (`A0001`…), `Codigo`, `Data`, `Ate` (horário limite), `Motivo`, `Placa` (opcional), `Status` (`Ativa`, `Utilizada`, `Cancelada`; "Vencida" é só rótulo de exibição), `AutorizadoPor`, `CriadoEm`, `UsadaEm`.

### auditoria (`auditoria_portaria.csv`)
`Quando`, `Acao`, `Id`, `Nome`, `Campo`, `Anterior`, `Novo`, `Usuario`. Ações: edição, exclusão, USUÁRIO, DESBLOQUEIO, VEÍCULO, AUTORIZAÇÃO e outras de gestão.

### tipos temporários (`tipos_temporarios.csv`)
`Tipo`, `CriadoEm`. Válidos por 24 horas.

### usuários (`usuarios_portaria.json`)
Id, nome completo, nome de exibição, e-mail, CPF, cargo, salt e hash da senha (PBKDF2, 200 000 iterações), hashes das palavras de recuperação, contador de tentativas e data de bloqueio.

## Formato do arquivo do cofre

| Elemento | Valor |
|---|---|
| Cabeçalho | `PORTARIA-COFRE-v2` |
| Derivação | PBKDF2-HMAC-SHA256, 600 000 iterações, sal de 16 bytes |
| Cifra | AES-256-GCM, nonce de 12 bytes (integridade autenticada) |
| Chaves | Segredo de dados aleatório protegido pela senha do Admin Final **e** por um código de recuperação |
| Escrita | Arquivo temporário cifrado → `fsync` → `os.replace` (atômica) |
| Concorrência | Revisão (SHA-256 dos bytes) comparada antes de gravar |

## Compatibilidade e migração

- Cofre 2.0 abre na 2.1 sem conversão: seções ausentes são lidas como listas vazias.
- Após a primeira gravação das seções novas, **a versão 2.0 não abre mais o cofre**. Faça backup antes de atualizar.
- Instalações legadas com CSV/JSON em texto claro são migradas para o cofre (exige a senha do Admin Final); os originais são removidos depois do commit.

## Arquivos auxiliares (fora do cofre)

| Arquivo | Função | Versionar no Git? |
|---|---|---|
| `dados_portaria.lock` | Lock de instância | Não |
| `ui_settings.json` | Tema escolhido | Não |
| `portaria.log` | Erros técnicos | Não |
