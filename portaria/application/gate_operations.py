"""Casos de uso da portaria 2.1: pessoas, entrada/saída, veículos, autorizações e relatórios.

Regras principais:
* o cadastro de pessoa recebe um código sequencial (P0001...) e nunca repete CPF;
* uma pessoa não pode ter uma segunda entrada enquanto a anterior estiver sem saída;
* entrada e saída usam o relógio do sistema (correções são feitas por edição auditada);
* veículos pertencem a uma pessoa e a placa é única na base;
* autorização de entrada é opcional, vale para uma data até um horário limite e é
  consumida na entrada (uma única vez).
"""
import csv
from collections import Counter
from datetime import datetime, timedelta
from html import escape

from ..config import (TIPOS_ACESSO, TIPOS_VEICULO, FORMATO_DATA, FORMATO_DATA_HORA,
                      FORMATO_CRIACAO)
from ..domain.validation import (ValidationError, novo_id, converter_data_hora, so_digitos,
                                 cpf_valido, formatar_cpf, mascarar_cpf, telefone_valido,
                                 formatar_telefone, placa_valida, normalizar_placa,
                                 formatar_placa, normalizar)
from ..infrastructure.vault import FILES, EXTRA_FILES

SECOES = {'registros': FILES[0], 'auditoria': FILES[1], 'pessoas': EXTRA_FILES[0],
          'veiculos': EXTRA_FILES[1], 'autorizacoes': EXTRA_FILES[2]}
SITUACOES = ('Todos', 'Dentro', 'Saiu')


def _agora():
    return datetime.now().strftime(FORMATO_DATA_HORA)


class GateOperations:
    """Operações ligadas ao contexto PortariaService."""

    # ------------------------------------------------------------------ infraestrutura
    def _salvar(self, **novas):
        """Grava várias coleções em um único commit atômico (cofre) e atualiza a memória."""
        if self.cofre.unlocked:
            self.cofre.save_sections({SECOES[k]: v for k, v in novas.items()})
        else:  # legado antes da migração; sem atomicidade entre arquivos
            for nome, valor in novas.items():
                getattr(self, nome + '_repo').save(valor)
        for nome, valor in novas.items():
            setattr(self, nome, valor)

    def _evento_geral(self, acao, id_, nome, campo, anterior, novo):
        return {'Quando': datetime.now().strftime(FORMATO_CRIACAO), 'Acao': acao, 'Id': id_,
                'Nome': nome, 'Campo': campo, 'Anterior': anterior, 'Novo': novo,
                'Usuario': self.nome_sessao()}

    # ------------------------------------------------------------------ pessoas
    def buscar_pessoa(self, codigo):
        return next((p for p in self.pessoas if p['Codigo'] == codigo), None)

    def buscar_pessoa_por_cpf(self, cpf):
        d = so_digitos(cpf)
        return next((p for p in self.pessoas if d and p['CPF'] == d), None)

    def _proximo_codigo(self):
        maior = 0
        for p in self.pessoas:
            try:
                maior = max(maior, int(p['Codigo'][1:]))
            except (ValueError, KeyError, IndexError):
                pass
        return 'P%04d' % (maior + 1)

    def _validar_pessoa(self, nome, cpf, telefone, empresa, motivo):
        if not isinstance(nome, str) or not nome.strip():
            raise ValidationError('Informe o nome da pessoa.')
        if any(ord(c) < 32 or ord(c) == 127 for c in nome):
            raise ValidationError('O nome contém caracteres de controle inválidos.')
        if len(nome.strip()) > 100:
            raise ValidationError('O nome deve conter no máximo 100 caracteres.')
        if not cpf_valido(cpf):
            raise ValidationError('CPF inválido.')
        if not telefone_valido(telefone):
            raise ValidationError('Telefone inválido. Use DDD + número (10 ou 11 dígitos).')
        if len(empresa) > 80 or any(ord(c) < 32 for c in empresa):
            raise ValidationError('Empresa inválida (até 80 caracteres).')
        if not motivo.strip():
            raise ValidationError('Informe o motivo do acesso.')
        if len(motivo) > 120 or any(ord(c) < 32 for c in motivo):
            raise ValidationError('Motivo inválido (até 120 caracteres).')

    def _tipo_permitido(self, tipo):
        return tipo in TIPOS_ACESSO + self.tipos_temporarios_ativos()

    def cadastrar_pessoa(self, nome, cpf, telefone, empresa, tipo, data, horario, motivo,
                         *, registrar_entrada=True):
        """Cadastra a pessoa (CPF único, código gerado) e, opcionalmente, a primeira entrada."""
        self.exigir('cadastrar')
        nome, empresa, motivo = ' '.join(nome.split()), ' '.join(empresa.split()), ' '.join(motivo.split())
        self._validar_pessoa(nome, cpf, telefone, empresa, motivo)
        if not self._tipo_permitido(tipo):
            raise ValidationError('Selecione um tipo de acesso válido (temporários expiram em 24 horas).')
        quando = '%s %s' % (data.strip(), horario.strip())
        if converter_data_hora(quando) is None:
            raise ValidationError('Data ou horário inválido.')
        if self.buscar_pessoa_por_cpf(cpf):
            raise ValidationError('CPF já cadastrado. Use o Controle de acesso para registrar a entrada.')
        pessoa = {'Codigo': self._proximo_codigo(), 'Nome': nome, 'CPF': so_digitos(cpf),
                  'Telefone': so_digitos(telefone), 'Empresa': empresa, 'Tipo': tipo,
                  'Motivo': motivo, 'CriadoEm': quando}
        novas = {'pessoas': self.pessoas + [pessoa]}
        registro = None
        if registrar_entrada:
            registro = self._montar_registro(pessoa, tipo, quando, '', '', motivo)
            novas['registros'] = self.registros + [registro]
        self._salvar(**novas)
        return pessoa, registro

    def pesquisar_pessoas(self, busca=''):
        termos = normalizar(busca).split()
        digitos = so_digitos(busca)
        resultado = []
        for p in self.pessoas:
            texto = normalizar(' '.join([p['Codigo'], p['Nome'], p.get('Empresa', ''), p['Tipo']]))
            if all(t in texto for t in termos) or (digitos and digitos in p['CPF']):
                resultado.append(p)
        return resultado

    def registro_aberto(self, codigo):
        return next((r for r in self.registros if r.get('Codigo') == codigo and not r['Saida']), None)

    def situacao_pessoa(self, codigo):
        return 'Dentro' if self.registro_aberto(codigo) else 'Saiu'

    # ------------------------------------------------------------------ entrada e saída
    def _montar_registro(self, pessoa, tipo, entrada, placa, autorizacao, motivo):
        existentes = {r['Id'] for r in self.registros}
        id_ = novo_id()
        while id_ in existentes:
            id_ = novo_id()
        registro = {'Id': id_, 'Nome': pessoa['Nome'], 'Tipo': tipo, 'Entrada': entrada,
                    'Saida': '', 'Codigo': pessoa['Codigo'], 'Placa': placa,
                    'Autorizacao': autorizacao, 'Motivo': motivo}
        self._validar_registro(registro)
        return registro

    def registrar_entrada(self, codigo, *, placa='', autorizacao_id='', tipo=None, motivo=None):
        """Entrada com horário do sistema. Bloqueia nova entrada sem saída anterior."""
        self.exigir('entrada')
        pessoa = self.buscar_pessoa(codigo)
        if pessoa is None:
            raise ValidationError('Pessoa não encontrada. Faça o cadastro primeiro.')
        if self.registro_aberto(codigo):
            raise ValidationError('%s já está dentro. Registre a saída antes de uma nova entrada.' % pessoa['Nome'])
        tipo = tipo or pessoa['Tipo']
        if not self._tipo_permitido(tipo):
            raise ValidationError('Tipo de acesso inválido ou expirado. Escolha outro tipo.')
        placa = normalizar_placa(placa)
        if placa and not any(v['Placa'] == placa and v['Codigo'] == codigo for v in self.veiculos):
            raise ValidationError('A placa informada não está cadastrada para esta pessoa.')
        novas = {}
        if not autorizacao_id:
            validas = self.autorizacoes_validas(codigo)
            autorizacao_id = validas[0]['Id'] if validas else ''
        if autorizacao_id:
            aut = self.buscar_autorizacao(autorizacao_id)
            if aut is None or aut['Codigo'] != codigo or aut not in self.autorizacoes_validas(codigo):
                raise ValidationError('Autorização inexistente, vencida ou já utilizada.')
            if aut.get('Placa') and placa and aut['Placa'] != placa:
                raise ValidationError('A autorização é válida apenas para a placa %s.' % formatar_placa(aut['Placa']))
            if aut.get('Placa') and not placa:
                placa = aut['Placa']
            novas['autorizacoes'] = [{**a, 'Status': 'Utilizada', 'UsadaEm': datetime.now().strftime(FORMATO_CRIACAO)}
                                     if a['Id'] == autorizacao_id else a for a in self.autorizacoes]
            novas['auditoria'] = self.auditoria + [self._evento_geral(
                'AUTORIZAÇÃO', autorizacao_id, pessoa['Nome'], 'Status', 'Ativa', 'Utilizada na entrada')]
        registro = self._montar_registro(pessoa, tipo, _agora(), placa, autorizacao_id,
                                         motivo if motivo is not None else pessoa.get('Motivo', ''))
        novas['registros'] = self.registros + [registro]
        self._salvar(**novas)
        return registro

    def registrar_saida(self, id_registro):
        """Saída com horário do sistema para um registro ainda aberto."""
        self.exigir('saida')
        reg = self.buscar_registro(id_registro)
        if reg is None:
            raise ValidationError('Registro não encontrado.')
        if reg['Saida']:
            raise ValidationError('A saída deste registro já foi registrada.')
        agora = _agora()
        if converter_data_hora(agora) < converter_data_hora(reg['Entrada']):
            raise ValidationError('A entrada está no futuro; corrija o horário antes de registrar a saída.')
        editado = {**reg, 'Saida': agora}
        self._validar_registro(editado)
        self._persistir_registros_auditoria(
            [editado if r['Id'] == id_registro else r for r in self.registros], [])
        return editado

    def consultar(self, busca='', situacao='Todos'):
        """Linhas do controle de acesso (mais recentes primeiro) com CPF mascarado."""
        if situacao not in SITUACOES:
            raise ValidationError('Filtro de situação inválido.')
        termos = normalizar(busca).split()
        digitos = so_digitos(busca)
        linhas = []
        for reg in reversed(self.registros):
            dentro = not reg['Saida']
            if (situacao == 'Dentro' and not dentro) or (situacao == 'Saiu' and dentro):
                continue
            pessoa = self.buscar_pessoa(reg.get('Codigo', ''))
            cpf = pessoa['CPF'] if pessoa else ''
            texto = normalizar(' '.join([reg['Nome'], reg.get('Codigo', ''), reg['Tipo'],
                                         reg['Entrada'], reg['Saida'], reg.get('Placa', '')]))
            if termos and not (all(t in texto for t in termos) or (digitos and digitos in cpf)):
                continue
            linhas.append({**reg, 'CPF': cpf, 'CPFMascarado': mascarar_cpf(cpf) if cpf else '—',
                           'Situacao': 'Dentro' if dentro else 'Saiu'})
        return linhas

    # ------------------------------------------------------------------ veículos
    def buscar_veiculo(self, id_veiculo):
        return next((v for v in self.veiculos if v['Id'] == id_veiculo), None)

    def veiculos_da_pessoa(self, codigo):
        return [v for v in self.veiculos if v['Codigo'] == codigo]

    def cadastrar_veiculo(self, codigo, placa, modelo, cor, tipo):
        self.exigir('veiculos')
        pessoa = self.buscar_pessoa(codigo)
        if pessoa is None:
            raise ValidationError('Selecione o proprietário do veículo.')
        if not placa_valida(placa):
            raise ValidationError('Placa inválida. Use o padrão ABC-1234 ou Mercosul ABC1D23.')
        placa = normalizar_placa(placa)
        if any(v['Placa'] == placa for v in self.veiculos):
            raise ValidationError('Placa já cadastrada.')
        modelo, cor = ' '.join(modelo.split()), ' '.join(cor.split())
        if not modelo or len(modelo) > 40 or any(ord(c) < 32 for c in modelo):
            raise ValidationError('Informe o modelo do veículo (até 40 caracteres).')
        if len(cor) > 20 or any(ord(c) < 32 for c in cor):
            raise ValidationError('Cor inválida (até 20 caracteres).')
        if tipo not in TIPOS_VEICULO:
            raise ValidationError('Tipo de veículo inválido.')
        veiculo = {'Id': novo_id(), 'Codigo': codigo, 'Placa': placa, 'Modelo': modelo,
                   'Cor': cor, 'Tipo': tipo, 'CriadoEm': datetime.now().strftime(FORMATO_CRIACAO)}
        evento = self._evento_geral('VEÍCULO', veiculo['Id'], pessoa['Nome'], 'Cadastro', '—',
                                    '%s · %s' % (formatar_placa(placa), modelo))
        self._salvar(veiculos=self.veiculos + [veiculo], auditoria=self.auditoria + [evento])
        return veiculo

    def remover_veiculo(self, id_veiculo):
        self.exigir('excluir')
        v = self.buscar_veiculo(id_veiculo)
        if v is None:
            raise ValidationError('Veículo não encontrado.')
        pessoa = self.buscar_pessoa(v['Codigo']) or {'Nome': v['Codigo']}
        if any(a.get('Placa') == v['Placa'] and a['Status'] == 'Ativa' for a in self.autorizacoes):
            raise ValidationError('Há autorização ativa para esta placa; cancele-a antes de remover.')
        evento = self._evento_geral('VEÍCULO', v['Id'], pessoa['Nome'], 'Remoção',
                                    '%s · %s' % (formatar_placa(v['Placa']), v['Modelo']), '—')
        self._salvar(veiculos=[x for x in self.veiculos if x['Id'] != id_veiculo],
                     auditoria=self.auditoria + [evento])

    # ------------------------------------------------------------------ autorizações
    def buscar_autorizacao(self, id_autorizacao):
        return next((a for a in self.autorizacoes if a['Id'] == id_autorizacao), None)

    def _proximo_codigo_autorizacao(self):
        maior = 0
        for a in self.autorizacoes:
            try:
                maior = max(maior, int(a['Id'][1:]))
            except (ValueError, KeyError, IndexError):
                pass
        return 'A%04d' % (maior + 1)

    def autorizacao_vigente(self, aut, agora=None):
        agora = agora or datetime.now()
        if aut.get('Status') != 'Ativa':
            return False
        limite = converter_data_hora('%s %s' % (aut['Data'], aut['Ate']))
        return limite is not None and agora.strftime(FORMATO_DATA) == aut['Data'] and agora <= limite

    def autorizacoes_validas(self, codigo, agora=None):
        return [a for a in self.autorizacoes
                if a['Codigo'] == codigo and self.autorizacao_vigente(a, agora)]

    def criar_autorizacao(self, codigo, data, ate, motivo, placa=''):
        self.exigir('autorizar')
        pessoa = self.buscar_pessoa(codigo)
        if pessoa is None:
            raise ValidationError('Selecione a pessoa autorizada.')
        limite = converter_data_hora('%s %s' % (data.strip(), ate.strip()))
        if limite is None:
            raise ValidationError('Data ou horário limite inválido.')
        if limite < datetime.now():
            raise ValidationError('O horário limite da autorização já passou.')
        if not motivo.strip() or len(motivo) > 120:
            raise ValidationError('Informe o motivo da autorização (até 120 caracteres).')
        placa = normalizar_placa(placa)
        if placa and not any(v['Placa'] == placa and v['Codigo'] == codigo for v in self.veiculos):
            raise ValidationError('A placa não pertence a esta pessoa. Cadastre o veículo antes.')
        if any(a['Codigo'] == codigo and a['Data'] == data.strip() and a['Status'] == 'Ativa'
               for a in self.autorizacoes):
            raise ValidationError('Já existe autorização ativa para esta pessoa nesta data.')
        aut = {'Id': self._proximo_codigo_autorizacao(), 'Codigo': codigo, 'Data': data.strip(),
               'Ate': ate.strip(), 'Motivo': ' '.join(motivo.split()), 'Placa': placa,
               'Status': 'Ativa', 'AutorizadoPor': self.nome_sessao(),
               'CriadoEm': datetime.now().strftime(FORMATO_CRIACAO), 'UsadaEm': ''}
        evento = self._evento_geral('AUTORIZAÇÃO', aut['Id'], pessoa['Nome'], 'Criação', '—',
                                    '%s até %s' % (aut['Data'], aut['Ate']))
        self._salvar(autorizacoes=self.autorizacoes + [aut], auditoria=self.auditoria + [evento])
        return aut

    def cancelar_autorizacao(self, id_autorizacao):
        self.exigir('autorizar')
        aut = self.buscar_autorizacao(id_autorizacao)
        if aut is None:
            raise ValidationError('Autorização não encontrada.')
        if aut['Status'] != 'Ativa':
            raise ValidationError('Somente autorizações ativas podem ser canceladas.')
        pessoa = self.buscar_pessoa(aut['Codigo']) or {'Nome': aut['Codigo']}
        evento = self._evento_geral('AUTORIZAÇÃO', aut['Id'], pessoa['Nome'], 'Status', 'Ativa', 'Cancelada')
        self._salvar(autorizacoes=[{**a, 'Status': 'Cancelada'} if a['Id'] == id_autorizacao else a
                                   for a in self.autorizacoes],
                     auditoria=self.auditoria + [evento])

    def status_autorizacao(self, aut):
        """Rótulo para exibição: Ativa, Vencida, Utilizada ou Cancelada."""
        if aut['Status'] == 'Ativa' and not self.autorizacao_vigente(aut):
            return 'Vencida'
        return aut['Status']

    def comprovante_autorizacao_html(self, id_autorizacao):
        self.exigir('consultar')
        aut = self.buscar_autorizacao(id_autorizacao)
        if aut is None:
            raise ValidationError('Autorização não encontrada.')
        pessoa = self.buscar_pessoa(aut['Codigo']) or {'Nome': aut['Codigo'], 'CPF': ''}
        linhas = [('Autorização', aut['Id']), ('Pessoa', pessoa['Nome']),
                  ('CPF', mascarar_cpf(pessoa['CPF'])), ('Válida em', aut['Data']),
                  ('Até', aut['Ate']), ('Placa', formatar_placa(aut['Placa']) or '—'),
                  ('Motivo', aut['Motivo']), ('Situação', self.status_autorizacao(aut)),
                  ('Autorizado por', aut.get('AutorizadoPor', '')), ('Emitido em', _agora())]
        corpo = ''.join('<tr><th>%s</th><td>%s</td></tr>' % (escape(k), escape(str(v))) for k, v in linhas)
        return ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Autorização %s</title>'
                '<style>body{font-family:Segoe UI,Arial,sans-serif;margin:40px;color:#1C342B}'
                'h1{font-size:22px}table{border-collapse:collapse;min-width:420px}'
                'th,td{border:1px solid #D7E5DA;padding:9px 14px;text-align:left}'
                'th{background:#EFF4F0;width:150px}</style>'
                '<h1>Autorização de entrada</h1><table>%s</table>'
                '<p>Documento gerado pelo sistema de portaria.</p></html>') % (escape(aut['Id']), corpo)

    # ------------------------------------------------------------------ relatórios
    def estatisticas(self, hoje=None):
        hoje = hoje or datetime.now()
        dia = hoje.strftime(FORMATO_DATA)
        entradas = [r for r in self.registros if converter_data_hora(r['Entrada'])]
        por_tipo = Counter(r['Tipo'] for r in entradas)
        ultimos = [(hoje - timedelta(days=i)) for i in range(6, -1, -1)]
        por_dia = [(d.strftime('%d/%m'), sum(r['Entrada'].startswith(d.strftime(FORMATO_DATA)) for r in entradas))
                   for d in ultimos]
        por_hora = Counter(int(r['Entrada'][11:13]) for r in entradas)
        return {
            'dentro': sum(not r['Saida'] for r in self.registros),
            'entradas_hoje': sum(r['Entrada'].startswith(dia) for r in entradas),
            'saidas_hoje': sum(r['Saida'].startswith(dia) for r in self.registros if r['Saida']),
            'pessoas': len(self.pessoas), 'veiculos': len(self.veiculos),
            'autorizacoes_ativas': sum(self.autorizacao_vigente(a, hoje) for a in self.autorizacoes),
            'por_tipo': sorted(por_tipo.items(), key=lambda kv: (-kv[1], kv[0])),
            'por_dia': por_dia,
            'por_hora': [(f'{h:02d}h', por_hora.get(h, 0)) for h in range(24)],
        }

    def exportar_csv(self, caminho):
        """Exporta o controle de acesso (CPF mascarado) em CSV UTF-8 com BOM para Excel."""
        self.exigir('exportar')
        colunas = ['Código', 'Nome', 'CPF', 'Tipo', 'Placa', 'Entrada', 'Saída', 'Situação', 'Motivo']
        linhas = self.consultar()
        try:
            with open(caminho, 'w', newline='', encoding='utf-8-sig') as f:
                out = csv.writer(f, delimiter=';')
                out.writerow(colunas)
                for r in reversed(linhas):
                    out.writerow([r.get('Codigo') or '—', r['Nome'], r['CPFMascarado'], r['Tipo'],
                                  formatar_placa(r.get('Placa', '')), r['Entrada'], r['Saida'],
                                  r['Situacao'], r.get('Motivo', '')])
        except OSError as exc:
            from ..infrastructure.storage import StorageError
            raise StorageError(f'Não foi possível exportar: {exc}') from exc
        return len(linhas)
