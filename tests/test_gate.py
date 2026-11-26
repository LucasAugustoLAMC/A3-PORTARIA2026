"""Pessoas, entrada/saída, veículos, autorizações, relatórios e compatibilidade do cofre."""
import csv
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from portaria.application.service import PortariaService
from portaria.config import CARGO_FINAL, CARGO_USUARIO, CARGO_ADM
from portaria.domain.validation import (ValidationError, PermissionDenied, placa_valida,
                                        telefone_valido, formatar_telefone, formatar_placa)

CPF, CPF2, CPF3 = '52998224725', '11144477735', '39053344705'
PAL = ['banana', 'cavalo', 'janela']


def agora(delta=0):
    return datetime.now() + timedelta(minutes=delta)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.s = PortariaService(self.base)
        self.s.carregar()
        self.s.cadastrar_usuario('Admin Inicial', 'Inicial', 'admin@teste.com', CPF,
                                 CARGO_FINAL, 'Abc12345!', PAL)
        self.s.autenticar('admin@teste.com', 'Abc12345!')

    def pessoa(self, nome='Maria Souza', cpf=CPF2, entrada=True, tipo='Visitante'):
        t = agora()
        return self.s.cadastrar_pessoa(nome, cpf, '(31) 91234-5678', 'ACME', tipo,
                                       t.strftime('%d/%m/%Y'), t.strftime('%H:%M'),
                                       'Reunião', registrar_entrada=entrada)

    # --- validadores
    def test_validadores(self):
        self.assertTrue(placa_valida('abc-1234'))
        self.assertTrue(placa_valida('ABC1D23'))
        self.assertFalse(placa_valida('AB-12345'))
        self.assertEqual(formatar_placa('abc1234'), 'ABC-1234')
        self.assertEqual(formatar_placa('abc1d23'), 'ABC1D23')
        self.assertTrue(telefone_valido('(31) 91234-5678'))
        self.assertTrue(telefone_valido('3112345678'))
        self.assertFalse(telefone_valido('(31) 81234-5678'))
        self.assertEqual(formatar_telefone('31912345678'), '(31) 91234-5678')

    # --- cadastro
    def test_cadastro_gera_codigo_e_primeira_entrada(self):
        p, r = self.pessoa()
        self.assertEqual(p['Codigo'], 'P0001')
        self.assertEqual(p['CPF'], CPF2)
        self.assertEqual(r['Codigo'], 'P0001')
        self.assertEqual(self.s.situacao_pessoa('P0001'), 'Dentro')
        p2, _ = self.pessoa('João Lima', CPF3)
        self.assertEqual(p2['Codigo'], 'P0002')

    def test_cadastro_sem_entrada(self):
        p, r = self.pessoa(entrada=False)
        self.assertIsNone(r)
        self.assertEqual(self.s.situacao_pessoa(p['Codigo']), 'Saiu')
        self.assertEqual(self.s.registros, [])

    def test_cadastro_rejeita_duplicado_e_dados_invalidos(self):
        self.pessoa()
        t = agora()
        d, h = t.strftime('%d/%m/%Y'), t.strftime('%H:%M')
        with self.assertRaisesRegex(ValidationError, 'já cadastrado'):
            self.s.cadastrar_pessoa('Outra Pessoa', '111.444.777-35',
                                    '(31) 91234-5678', '', 'Visitante', d, h, 'x')
        casos = [('', CPF3, '(31) 91234-5678', 'Visitante', d, h, 'm', 'nome'),
                 ('Ana Paula', '11111111111', '(31) 91234-5678', 'Visitante', d, h, 'm', 'CPF'),
                 ('Ana Paula', CPF3, '123', 'Visitante', d, h, 'm', 'Telefone'),
                 ('Ana Paula', CPF3, '(31) 91234-5678', 'Inexistente', d, h, 'm', 'tipo'),
                 ('Ana Paula', CPF3, '(31) 91234-5678', 'Visitante', '31/02/2026', h, 'm', 'Data'),
                 ('Ana Paula', CPF3, '(31) 91234-5678', 'Visitante', d, h, '  ', 'motivo')]
        for nome, cpf, tel, tipo, dd, hh, motivo, trecho in casos:
            with self.subTest(trecho):
                with self.assertRaisesRegex(ValidationError, '(?i)' + trecho):
                    self.s.cadastrar_pessoa(nome, cpf, tel, '', tipo, dd, hh, motivo)
        self.assertEqual(len(self.s.pessoas), 1)

    # --- entrada e saída
    def test_segunda_entrada_exige_saida_previa(self):
        p, _ = self.pessoa()
        with self.assertRaisesRegex(ValidationError, 'já está dentro'):
            self.s.registrar_entrada(p['Codigo'])
        aberto = self.s.registro_aberto(p['Codigo'])
        saida = self.s.registrar_saida(aberto['Id'])
        self.assertTrue(saida['Saida'])
        with self.assertRaisesRegex(ValidationError, 'já foi registrada'):
            self.s.registrar_saida(aberto['Id'])
        novo = self.s.registrar_entrada(p['Codigo'])
        self.assertEqual(self.s.situacao_pessoa(p['Codigo']), 'Dentro')
        self.assertNotEqual(novo['Id'], aberto['Id'])
        with self.assertRaises(ValidationError):
            self.s.registrar_entrada('P9999')

    def test_consulta_busca_por_nome_cpf_e_situacao(self):
        a, ra = self.pessoa('Maria Souza', CPF2)
        b, _ = self.pessoa('João Lima', CPF3)
        self.s.registrar_saida(ra['Id'])
        self.assertEqual({r['Nome'] for r in self.s.consultar()}, {'Maria Souza', 'João Lima'})
        self.assertEqual([r['Nome'] for r in self.s.consultar('maria')], ['Maria Souza'])
        self.assertEqual([r['Nome'] for r in self.s.consultar('390.533.447-05')], ['João Lima'])
        self.assertEqual([r['Nome'] for r in self.s.consultar('P0002')], ['João Lima'])
        self.assertEqual([r['Nome'] for r in self.s.consultar(situacao='Dentro')], ['João Lima'])
        self.assertEqual([r['Nome'] for r in self.s.consultar(situacao='Saiu')], ['Maria Souza'])
        self.assertEqual(self.s.consultar('maria')[0]['CPFMascarado'], '***.***.777-35')
        with self.assertRaises(ValidationError):
            self.s.consultar(situacao='Outro')

    def test_saida_com_entrada_no_futuro_e_bloqueada(self):
        p, _ = self.pessoa(entrada=False)
        r = self.s.registrar_entrada(p['Codigo'])
        futuro = {**r, 'Entrada': agora(120).strftime('%d/%m/%Y %H:%M')}
        self.s.registros = [futuro]
        with self.assertRaisesRegex(ValidationError, 'futuro'):
            self.s.registrar_saida(r['Id'])

    # --- veículos
    def test_veiculos(self):
        p, _ = self.pessoa()
        v = self.s.cadastrar_veiculo(p['Codigo'], 'abc-1234', 'Gol', 'Prata', 'Carro')
        self.assertEqual(v['Placa'], 'ABC1234')
        with self.assertRaisesRegex(ValidationError, 'já cadastrada'):
            self.s.cadastrar_veiculo(p['Codigo'], 'ABC1234', 'Uno', '', 'Carro')
        with self.assertRaisesRegex(ValidationError, 'inválida'):
            self.s.cadastrar_veiculo(p['Codigo'], 'XX', 'Uno', '', 'Carro')
        with self.assertRaises(ValidationError):
            self.s.cadastrar_veiculo('P9999', 'DEF1G23', 'Uno', '', 'Carro')
        with self.assertRaises(ValidationError):
            self.s.cadastrar_veiculo(p['Codigo'], 'DEF1G23', 'Uno', '', 'Disco voador')
        self.assertEqual(self.s.auditoria[-1]['Acao'], 'VEÍCULO')
        self.s.registrar_saida(self.s.registro_aberto(p['Codigo'])['Id'])
        r = self.s.registrar_entrada(p['Codigo'], placa='abc-1234')
        self.assertEqual(r['Placa'], 'ABC1234')
        self.s.registrar_saida(r['Id'])
        with self.assertRaisesRegex(ValidationError, 'não está cadastrada'):
            self.s.registrar_entrada(p['Codigo'], placa='ZZZ9999')
        self.s.remover_veiculo(v['Id'])
        self.assertEqual(self.s.veiculos, [])

    # --- autorizações
    def test_autorizacao_e_consumida_na_entrada(self):
        p, _ = self.pessoa(entrada=False)
        self.s.cadastrar_veiculo(p['Codigo'], 'ABC1D23', 'Onix', 'Branco', 'Carro')
        t = agora(60)
        data, ate = t.strftime('%d/%m/%Y'), t.strftime('%H:%M')
        if t.date() != datetime.now().date():
            self.skipTest('virada de dia durante o teste')
        aut = self.s.criar_autorizacao(p['Codigo'], data, ate, 'Visita ao 302', 'ABC1D23')
        self.assertEqual(aut['Id'], 'A0001')
        self.assertEqual(self.s.status_autorizacao(aut), 'Ativa')
        with self.assertRaisesRegex(ValidationError, 'ativa'):
            self.s.criar_autorizacao(p['Codigo'], data, ate, 'Outra', '')
        self.assertIn('Visita ao 302', self.s.comprovante_autorizacao_html('A0001'))
        reg = self.s.registrar_entrada(p['Codigo'])
        self.assertEqual(reg['Autorizacao'], 'A0001')
        self.assertEqual(reg['Placa'], 'ABC1D23')
        self.assertEqual(self.s.buscar_autorizacao('A0001')['Status'], 'Utilizada')
        self.assertEqual(self.s.autorizacoes_validas(p['Codigo']), [])
        with self.assertRaises(ValidationError):
            self.s.cancelar_autorizacao('A0001')

    def test_autorizacao_vencida_cancelada_e_validacoes(self):
        p, _ = self.pessoa(entrada=False)
        passado = agora(-30)
        with self.assertRaisesRegex(ValidationError, 'já passou'):
            self.s.criar_autorizacao(p['Codigo'], passado.strftime('%d/%m/%Y'), passado.strftime('%H:%M'), 'x')
        with self.assertRaises(ValidationError):
            self.s.criar_autorizacao(p['Codigo'], '99/99/2026', '10:00', 'x')
        with self.assertRaisesRegex(ValidationError, 'não pertence'):
            self.s.criar_autorizacao(p['Codigo'], (agora(60)).strftime('%d/%m/%Y'), '23:59', 'x', 'QQQ1111')
        amanha = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')
        aut = self.s.criar_autorizacao(p['Codigo'], amanha, '23:59', 'Entrega')
        self.assertFalse(self.s.autorizacao_vigente(aut))  # vale só no dia indicado
        self.s.cancelar_autorizacao(aut['Id'])
        self.assertEqual(self.s.status_autorizacao(self.s.buscar_autorizacao(aut['Id'])), 'Cancelada')
        with self.assertRaisesRegex(ValidationError, 'inexistente'):
            self.s.registrar_entrada(p['Codigo'], autorizacao_id=aut['Id'])

    # --- permissões
    def test_permissoes_por_cargo(self):
        p, _ = self.pessoa()
        self.s.cadastrar_usuario('Operador Segundo', 'Ope', 'ope@teste.com', CPF3, CARGO_USUARIO, 'Abc12345!', PAL)
        self.s.sair()
        self.s.autenticar('ope@teste.com', 'Abc12345!')
        self.s.cadastrar_veiculo(p['Codigo'], 'ABC1234', 'Gol', '', 'Carro')  # permitido
        self.s.registrar_saida(self.s.registro_aberto(p['Codigo'])['Id'])      # permitido
        self.s.registrar_entrada(p['Codigo'])                                   # permitido
        for acao in (lambda: self.s.criar_autorizacao(p['Codigo'], agora().strftime('%d/%m/%Y'), '23:59', 'x'),
                     lambda: self.s.cancelar_autorizacao('A0001'),
                     lambda: self.s.remover_veiculo(self.s.veiculos[0]['Id']),
                     lambda: self.s.exportar_csv(self.base / 'x.csv')):
            with self.assertRaises(PermissionDenied):
                acao()

    # --- relatórios
    def test_estatisticas_e_exportacao(self):
        a, ra = self.pessoa('Maria Souza', CPF2)
        self.pessoa('João Lima', CPF3, tipo='Morador')
        self.s.registrar_saida(ra['Id'])
        st = self.s.estatisticas()
        self.assertEqual((st['dentro'], st['entradas_hoje'], st['saidas_hoje'], st['pessoas']), (1, 2, 1, 2))
        self.assertEqual(dict(st['por_tipo']), {'Visitante': 1, 'Morador': 1})
        self.assertEqual(st['por_dia'][-1][1], 2)
        self.assertEqual(len(st['por_hora']), 24)
        destino = self.base / 'saida.csv'
        self.assertEqual(self.s.exportar_csv(destino), 2)
        with destino.open(encoding='utf-8-sig', newline='') as f:
            linhas = list(csv.reader(f, delimiter=';'))
        self.assertEqual(linhas[0][:3], ['Código', 'Nome', 'CPF'])
        self.assertTrue(all('***' in l[2] for l in linhas[1:]))
        self.assertNotIn(CPF2, destino.read_text(encoding='utf-8-sig'))

    # --- persistência e compatibilidade
    def test_persistencia_no_cofre_e_releitura(self):
        p, _ = self.pessoa()
        self.s.cadastrar_veiculo(p['Codigo'], 'ABC1234', 'Gol', 'Prata', 'Carro')
        s2 = PortariaService(self.base)
        s2.desbloquear_cofre('Abc12345!')
        s2.carregar()
        self.assertEqual([x['Codigo'] for x in s2.pessoas], ['P0001'])
        self.assertEqual(len(s2.veiculos), 1)
        self.assertEqual(s2.registros[0]['Codigo'], 'P0001')
        self.assertFalse(list(self.base.glob('pessoas_portaria.json')))

    def test_cofre_anterior_sem_secoes_novas_abre_e_evolui(self):
        from portaria.infrastructure.vault import EncryptedVault, FILES
        base = Path(self.tmp.name) / 'antigo'
        base.mkdir()
        vault = EncryptedVault(base / 'dados_portaria.enc')
        s0 = PortariaService(base)
        s0.carregar()
        s0.cadastrar_usuario('Admin Antigo', 'Antigo', 'a@teste.com', CPF, CARGO_FINAL, 'Abc12345!', PAL)
        # simula cofre 2.0: remove as seções novas e regrava
        dados = {k: s0.cofre.section(k) for k in FILES}
        (base / 'dados_portaria.enc').unlink()
        EncryptedVault(base / 'dados_portaria.enc').create('Abc12345!', dados)
        s1 = PortariaService(base)
        s1.desbloquear_cofre('Abc12345!')
        s1.carregar()
        self.assertEqual((s1.pessoas, s1.veiculos, s1.autorizacoes), ([], [], []))
        s1.autenticar('a@teste.com', 'Abc12345!')
        t = agora()
        s1.cadastrar_pessoa('Nova Pessoa', CPF2, '(31) 91234-5678', '', 'Morador',
                            t.strftime('%d/%m/%Y'), t.strftime('%H:%M'), 'Moradia')
        s2 = PortariaService(base)
        s2.desbloquear_cofre('Abc12345!')
        s2.carregar()
        self.assertEqual(len(s2.pessoas), 1)

    def test_login_vazio_e_bloqueado(self):
        self.s.sair()
        with self.assertRaisesRegex(ValidationError, 'Informe'):
            self.s.autenticar('', '')
        with self.assertRaisesRegex(ValidationError, 'Informe'):
            self.s.autenticar('admin@teste.com', '')


if __name__ == '__main__':
    unittest.main()
