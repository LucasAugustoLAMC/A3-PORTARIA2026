"""Smoke tests gráficos reais com Tk; pulam sem display gráfico (CI headless)."""
from types import SimpleNamespace
from unittest import mock
import tempfile
import tkinter as tk
import unittest

from portaria.presentation_v2.app import PortariaApp
from portaria.presentation_v2.auth import AuthView
from portaria.presentation_v2.users import UserForm, UserDialog
from portaria.presentation_v2.records import RecordsView
from portaria.presentation_v2.gate_pages import (HomeView, RegisterView, VehiclesView,
                                                  AuthorizationsView, ReportsView)
from portaria.presentation_v2.fields import MaskedEntry
from portaria.config import CARGO_FINAL, CARGO_USUARIO


def display_available():
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(display_available(), 'Tk requer display (use xvfb-run)')
class UiV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = PortariaApp(data_dir=self.tmp.name)
        self.addCleanup(self.app.destroy)
        self.app.update()
        self.app.service.cadastrar_usuario('Admin Principal', 'Admin', 'admin@teste.com',
            '52998224725', CARGO_FINAL, 'Abc12345!', ['banana','cavalo','janela'])
        self.app.service.chave_recuperacao = None
        self.app.show_auth('login')
        self.app.update()

    def login(self):
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        auth.login.insert(0, 'admin@teste.com')
        auth.password.insert(0, 'Abc12345!')
        auth.sign_in()
        self.app.update()
        self.assertTrue(self.app._dashboard)
        return next(w for w in self.app.content.winfo_children() if isinstance(w, HomeView))

    def page(self, name, cls):
        if not self.app._dashboard:
            self.login()
        self.app.show_page(name)
        self.app.update()
        return next(w for w in self.app.content.winfo_children() if isinstance(w, cls))

    def test_primeiro_acesso_cabe_e_pode_rolar_ate_salvar(self):
        self.app.show_auth('setup')
        self.app.geometry('1000x700')
        self.app.update()
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        form = next(w for w in auth.inner.winfo_children() if isinstance(w, UserForm))
        self.assertTrue(auth.scroller._scrollable)
        self.assertFalse(form._narrow)
        self.assertTrue(auth.scroller.scrollbar.winfo_ismapped())
        auth.scroller.ensure_visible(form.save_btn)
        self.app.update()
        self.assertGreater(auth.scroller.canvas.yview()[0], 0)
        bottom = auth.scroller.canvas.winfo_rooty() + auth.scroller.canvas.winfo_height()
        self.assertLessEqual(form.save_btn.winfo_rooty() + form.save_btn.winfo_height(), bottom)
        auth.scroller.canvas.yview_moveto(0)
        self.app.update()
        form.name.event_generate('<MouseWheel>', delta=-120)
        self.app.update()
        self.assertGreater(auth.scroller.canvas.yview()[0], 0)

    def test_primeiro_acesso_estreito_uma_coluna_sem_corte(self):
        self.app.show_auth('setup')
        self.app.geometry('550x520')
        self.app.update()
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        form = next(w for w in auth.inner.winfo_children() if isinstance(w, UserForm))
        self.assertTrue(form._narrow)
        self.assertLessEqual(auth.inner.winfo_width(), auth.scroller.canvas.winfo_width())
        self.assertEqual(form.name.winfo_width(), form.display.winfo_width())
        auth.scroller.canvas.yview_moveto(1)
        self.app.update()
        self.assertLessEqual(
            form.save_btn.winfo_rooty() + form.save_btn.winfo_height(),
            auth.scroller.canvas.winfo_rooty() + auth.scroller.canvas.winfo_height(),
        )
        self.app.geometry('1100x760')
        self.app.update()
        self.assertFalse(form._narrow)

    def test_novo_usuario_em_dialogo_pequeno_tem_rolagem(self):
        dialog = UserDialog(self.app, self.app, lambda _u: None)
        try:
            dialog.geometry('490x470')
            self.app.update()
            scroller = next(w for w in dialog.winfo_children()
                            if w.__class__.__name__ == 'ScrollableCard')
            form = next(w for w in scroller.content.winfo_children() if isinstance(w, UserForm))
            self.assertTrue(form._narrow)
            self.assertTrue(scroller._scrollable)
            scroller.ensure_visible(form.save_btn)
            self.app.update()
            self.assertGreater(scroller.canvas.yview()[0], 0)
        finally:
            dialog.destroy()

    def test_navegacao_completa_e_temas(self):
        self.login()
        for name in ('register', 'records', 'vehicles', 'auths', 'reports', 'audit', 'users', 'settings', 'home'):
            self.app.show_page(name)
            self.app.update()
        self.app.change_theme('Escuro')
        self.app.update()
        self.assertEqual(self.app.theme_name, 'Escuro')
        self.app.change_theme('Floresta')
        self.app.update()
        self.assertEqual(self.app.theme_name, 'Floresta')

    def test_digitacao_real_do_cpf_nao_perde_digitos(self):
        view = self.page('register', RegisterView)
        self.app.update()
        for entry, digits, expected in ((view.cpf, '12345678900', '123.456.789-00'),
                                        (view.phone, '31912345678', '(31) 91234-5678')):
            entry.focus_force()
            self.app.update()
            for d in digits:
                entry.event_generate('<KeyPress>', keysym=d)
                entry.event_generate('<KeyRelease>', keysym=d)
                self.app.update()
            self.assertEqual(entry.get(), expected)
        # edição no meio mantém o cursor e os demais dígitos
        view.cpf.focus_force()
        self.app.update()
        view.cpf.icursor(4)
        view.cpf.event_generate('<KeyPress>', keysym='9')
        view.cpf.event_generate('<KeyRelease>', keysym='9')
        self.app.update()
        self.assertEqual(view.cpf.get(), '123.945.678-90')  # campo cheio: o excedente sai no fim
        # data e hora digitadas tecla a tecla
        for entry, digits, expected in ((view.when.date, '23112026', '23/11/2026'),
                                        (view.when.time, '2040', '20:40')):
            entry.delete(0, 'end')
            entry.focus_force()
            self.app.update()
            for d in digits:
                entry.event_generate('<KeyPress>', keysym=d)
                self.app.update()
            self.assertEqual(entry.get(), expected)

    def test_trocar_de_tela_nao_dispara_callback_de_texto_destruido(self):
        """Regressão: login -> recuperar conta (e voltar) não pode gerar erro de Tk."""
        erros = []
        self.app.report_callback_exception = lambda *exc: erros.append(exc)
        for modo in ('recover', 'login', 'recover', 'login'):
            self.app.show_auth(modo)
            self.app.update()
            self.app.geometry('900x650')
            self.app.update()
        self.assertEqual(erros, [])

    def test_login_vazio_limpar_e_logo(self):
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        with mock.patch('portaria.presentation_v2.auth.messagebox.showwarning') as warn:
            auth.sign_in()
            warn.assert_called_once()
        self.assertFalse(self.app._dashboard)
        auth.login.insert(0, 'x@y.com')
        auth.password.insert(0, 'segredo')
        auth.clear_login()
        self.assertEqual((auth.login.get(), auth.password.get()), ('', ''))

    def test_cadastro_pessoa_formata_valida_e_gera_codigo(self):
        view = self.page('register', RegisterView)
        view.name.insert(0, 'Maria Souza')
        view.cpf.insert(0, '11144477735')
        view.phone.insert(0, '31912345678')
        view.reason.insert(0, 'Reunião')
        self.assertEqual(view.cpf.get(), '111.444.777-35')
        self.assertEqual(view.phone.get(), '(31) 91234-5678')
        with mock.patch('portaria.presentation_v2.gate_pages.messagebox.showinfo') as info:
            view.create()
            self.app.update()
            self.assertIn('P0001', info.call_args[0][1])
        self.assertEqual(len(self.app.service.pessoas), 1)
        self.assertEqual(self.app.service.situacao_pessoa('P0001'), 'Dentro')
        self.assertEqual(view.name.get(), '')
        self.assertEqual(len(view.table.get_children()), 1)
        # CPF duplicado: erro apresentado, nada gravado
        view.name.insert(0, 'Outra Pessoa')
        view.cpf.insert(0, '11144477735')
        view.phone.insert(0, '31912345678')
        view.reason.insert(0, 'x')
        with mock.patch('portaria.presentation_v2.app.messagebox.showerror') as err:
            view.create()
            self.assertIn('CPF já cadastrado', err.call_args[0][1])
        self.assertEqual(len(self.app.service.pessoas), 1)

    def test_controle_entrada_saida_busca_filtro_e_bloqueio(self):
        self.login()
        s = self.app.service
        from datetime import datetime
        t = datetime.now()
        s.cadastrar_pessoa('Maria Souza', '11144477735', '(31) 91234-5678', '', 'Visitante',
                           t.strftime('%d/%m/%Y'), t.strftime('%H:%M'), 'Reunião')
        view = self.page('records', RecordsView)
        self.assertEqual(len(view.table.get_children()), 1)
        row = view.table.item(view.table.get_children()[0])['values']
        self.assertEqual((row[0], row[2], row[6]), ('P0001', '***.***.777-35', 'Dentro'))
        view.situation.set('Saiu')
        view.refresh()
        self.assertEqual(len(view.table.get_children()), 0)
        view.situation.set('Todos')
        view.search.set('111.444.777-35')
        self.app.update()
        self.assertEqual(len(view.table.get_children()), 1)
        view.search.set('zzz')
        self.app.update()
        self.assertEqual(len(view.table.get_children()), 0)
        view.search.set('')
        # segunda entrada sem saída é bloqueada
        view.person.select('P0001')
        with mock.patch('portaria.presentation_v2.app.messagebox.showerror') as err:
            view.enter()
            self.assertIn('já está dentro', err.call_args[0][1])
        # saída automática
        view.table.selection_set(view.table.get_children()[0])
        with mock.patch('portaria.presentation_v2.records.messagebox.askyesno', return_value=True):
            view.checkout()
        self.assertEqual(s.situacao_pessoa('P0001'), 'Saiu')
        view.enter()
        self.assertEqual(s.situacao_pessoa('P0001'), 'Dentro')
        self.assertEqual(len(s.registros), 2)

    def test_veiculo_e_autorizacao_pela_interface(self):
        self.login()
        s = self.app.service
        from datetime import datetime
        t = datetime.now()
        s.cadastrar_pessoa('Maria Souza', '11144477735', '(31) 91234-5678', '', 'Visitante',
                           t.strftime('%d/%m/%Y'), t.strftime('%H:%M'), 'Reunião', registrar_entrada=False)
        veh = self.page('vehicles', VehiclesView)
        veh.owner.select('P0001')
        veh.plate.insert(0, 'abc1d23')
        veh.model.insert(0, 'Onix')
        veh.create()
        self.assertEqual(len(s.veiculos), 1)
        self.assertEqual(len(veh.table.get_children()), 1)
        auth = self.page('auths', AuthorizationsView)
        auth.person.select('P0001')
        auth.reason.insert(0, 'Visita')
        if datetime.now().hour == 23 and datetime.now().minute == 59:
            self.skipTest('limite do dia')
        auth.create()
        self.assertEqual(len(s.autorizacoes), 1)
        self.assertEqual(auth.table.item('A0001')['values'][4], 'Ativa')

    def test_relatorios_e_graficos_desenham(self):
        view = self.page('reports', ReportsView)
        self.app.update()
        charts = []
        def walk(w):
            for c in w.winfo_children():
                if c.winfo_class() == 'Canvas' and hasattr(c, 'set_data'):
                    charts.append(c)
                walk(c)
        walk(view)
        self.assertEqual(len(charts), 3)
        charts[0].set_data([('a', 3), ('b', 1)])
        self.assertTrue(charts[0].find_all())

    def test_mask_rejeita_emoji_e_valor_impossivel(self):
        from portaria.presentation_v2.theme import THEMES
        w = MaskedEntry(self.app, THEMES['Claro'], 'dd/mm/aaaa')
        w._replace_digits('31102026', 8)
        self.assertEqual(w.get(), '31/10/2026')
        w._replace_digits('32102026', 8)
        self.assertEqual(w.get(), '31/10/2026')
        w._key(SimpleNamespace(state=0, keysym='x', char='X'))
        self.assertEqual(w.get(), '31/10/2026')
        w._key(SimpleNamespace(state=0, keysym='smile', char='🙂'))
        self.assertEqual(w.get(), '31/10/2026')
        w.destroy()

    def test_janela_compacta_modo_alternavel(self):
        view = self.page('records', RecordsView)
        self.app.geometry('820x660')
        self.app.update()
        self.assertTrue(view._narrow)
        self.assertFalse(self.app._nav_visible)
        view._select_mobile('form')
        self.app.update()
        self.assertTrue(view.form_holder.winfo_ismapped())
        view._select_mobile('records')
        self.app.update()
        self.assertTrue(view.list_card.winfo_ismapped())

    def test_guarda_de_reentrancia_de_interface(self):
        self.login()
        calls = []
        def nested():
            calls.append(1)
            self.assertFalse(self.app.execute(lambda: calls.append(2)))
        self.assertTrue(self.app.execute(nested))
        self.assertEqual(calls, [1])

    def test_permissoes_refletidas_na_navegacao(self):
        self.login()
        self.app.service.cadastrar_usuario('Operador Segundo','Ope','ope@teste.com',
            '11144477735', CARGO_USUARIO, 'Abc12345!', ['banana','cavalo','janela'])
        self.app.logout()
        self.app.service.autenticar('ope@teste.com','Abc12345!')
        self.app.show_dashboard()
        self.app.update()
        self.assertNotIn('users', self.app.nav_buttons)
        self.assertNotIn('audit', self.app.nav_buttons)
        for visible in ('home', 'register', 'records', 'vehicles', 'auths', 'reports'):
            self.assertIn(visible, self.app.nav_buttons)
        from portaria.domain.validation import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.app.show_page('audit')


if __name__ == '__main__':
    unittest.main()
