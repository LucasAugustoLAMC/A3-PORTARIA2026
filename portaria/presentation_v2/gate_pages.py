"""Páginas da portaria 2.1: Início, Cadastro, Veículos, Autorizações e Relatórios."""
import os
import tempfile
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

from .theme import FONT, button, entry, text
from .fields import DateTimeInput, MaskedEntry
from .layout import SplitPage
from .widgets import BarChart, PersonPicker, cpf_entry, phone_entry, plate_entry
from ..config import TIPOS_ACESSO, TIPOS_VEICULO
from ..domain.validation import formatar_cpf, formatar_telefone, formatar_placa, mascarar_cpf


def split_datetime(value):
    data, _, hora = value.partition(' ')
    return data, hora


# --------------------------------------------------------------------------- Cadastro
class RegisterView(SplitPage):
    title = 'Cadastro de portaria'
    subtitle = 'Cadastre pessoas, valide o CPF e gere o código de identificação.'
    form_label = '+ Novo cadastro'
    list_label = 'Ver cadastrados'

    def build_form(self, f):
        p = self.p
        text(f, p, 'Novo cadastro', size=16, weight='bold').pack(anchor='w')
        text(f, p, 'Dados obrigatórios marcados com *', muted=True).pack(anchor='w', pady=(3, 14))
        text(f, p, 'Nome *', muted=True).pack(anchor='w')
        self.name = entry(f, p, limit=100)
        self.name.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'CPF *', muted=True).pack(anchor='w')
        self.cpf = cpf_entry(f, p)
        self.cpf.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Telefone *', muted=True).pack(anchor='w')
        self.phone = phone_entry(f, p)
        self.phone.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Empresa', muted=True).pack(anchor='w')
        self.company = entry(f, p, limit=80)
        self.company.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Tipo de acesso *', muted=True).pack(anchor='w')
        type_box = tk.Frame(f, bg=p.card)
        type_box.pack(fill='x', pady=(4, 10))
        type_box.columnconfigure(0, weight=1)
        self.type = ttk.Combobox(type_box, values=(), state='readonly')
        self.type.grid(row=0, column=0, sticky='ew')
        button(type_box, p, '+ Tipo', self.add_type, kind='secondary', padx=8).grid(row=0, column=1, padx=(7, 0))
        text(f, p, 'Data e horário *', muted=True).pack(anchor='w')
        self.when = DateTimeInput(f, p)
        self.when.pack(fill='x', pady=(4, 5))
        button(f, p, 'Usar data e hora atuais', self.when.set_now, kind='link',
               anchor='w', padx=2, pady=5).pack(anchor='w', pady=(0, 6))
        text(f, p, 'Motivo *', muted=True).pack(anchor='w')
        self.reason = entry(f, p, limit=120)
        self.reason.pack(fill='x', ipady=8, pady=(4, 10))
        self.enter_now = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text='Registrar a entrada neste horário', variable=self.enter_now,
                       bg=p.card, fg=p.text, activebackground=p.card, selectcolor=p.card,
                       font=(FONT, 10)).pack(anchor='w', pady=(0, 12))
        self.submit = button(f, p, 'Cadastrar', self.create)
        self.submit.pack(fill='x')
        row = tk.Frame(f, bg=p.card)
        row.pack(fill='x', pady=(8, 0))
        row.columnconfigure((0, 1), weight=1, uniform='a')
        button(row, p, 'Limpar', self.clear, kind='secondary').grid(row=0, column=0, sticky='ew', padx=(0, 4))
        button(row, p, 'Cancelar', self.cancel, kind='secondary').grid(row=0, column=1, sticky='ew', padx=(4, 0))
        self.when.set_now()
        self.load_types()

    def load_types(self):
        types = TIPOS_ACESSO + self.s.tipos_temporarios_ativos()
        current = self.type.get()
        self.type['values'] = types
        self.type.set(current if current in types else types[0])

    def add_type(self):
        from tkinter import simpledialog
        name = simpledialog.askstring('Tipo de acesso', 'Nome do novo tipo temporário (24 horas):', parent=self)
        if name is None:
            return
        def work():
            result = self.s.criar_tipo_temporario(name)
            self.load_types()
            self.type.set(result)
            self.app.toast('Tipo temporário disponível por 24 horas.')
        self.app.execute(work)

    def build_list(self, f):
        p = self.p
        self.search = tk.StringVar()
        title_line = tk.Frame(f, bg=p.card)
        title_line.pack(fill='x')
        text(title_line, p, 'Pessoas cadastradas', size=16, weight='bold').pack(side='left')
        self.total_text = text(title_line, p, '', muted=True)
        self.total_text.pack(side='right')
        self.search_entry = entry(f, p, textvariable=self.search)
        self.search_entry.pack(fill='x', ipady=8, pady=(15, 4))
        text(f, p, 'Busque por nome, CPF, código ou empresa.', muted=True, size=9).pack(anchor='w', pady=(0, 8))
        self.search.trace_add('write', lambda *_: self.refresh())
        self.table = self.make_table(f, [('Codigo', 'Código', 68), ('Nome', 'Nome', 120), ('CPF', 'CPF', 98),
                                         ('Telefone', 'Telefone', 110), ('Tipo', 'Tipo', 76),
                                         ('Situacao', 'Situação', 70), ('Empresa', 'Empresa', 90)],
                                    selectmode='browse')
        row = tk.Frame(f, bg=p.card)
        row.pack(fill='x', pady=(14, 0))
        button(row, p, 'Registrar entrada', self.go_enter).pack(side='left')
        button(row, p, 'Voltar', lambda: self.app.show_page('home'), kind='secondary').pack(side='right')

    def go_enter(self):
        self.app.show_page('records')

    def refresh(self):
        if not hasattr(self, 'table'):
            return
        self.table.delete(*self.table.get_children())
        found = list(reversed(self.s.pesquisar_pessoas(self.search.get())))
        for x in found:
            inside = self.s.situacao_pessoa(x['Codigo']) == 'Dentro'
            self.table.insert('', 'end', iid=x['Codigo'], values=(
                x['Codigo'], x['Nome'], mascarar_cpf(x['CPF']), formatar_telefone(x['Telefone']),
                x['Tipo'], 'Dentro' if inside else 'Saiu', x.get('Empresa') or '—'),
                tags=('pending',) if inside else ())
        self.counts.configure(text='%d pessoas cadastradas' % len(self.s.pessoas))
        self.total_text.configure(text='%d exibido(s)' % len(found))

    def clear(self):
        self.name.delete(0, 'end')
        self.cpf.clear()
        self.phone.clear()
        self.company.delete(0, 'end')
        self.reason.delete(0, 'end')
        self.type.set(TIPOS_ACESSO[0])
        self.when.set_now()
        self.enter_now.set(True)
        self.name.focus_set()

    def cancel(self):
        self.clear()
        self.app.show_page('home')

    def create(self):
        data, hora = split_datetime(self.when.get())
        def work():
            pessoa, registro = self.s.cadastrar_pessoa(
                self.name.get(), self.cpf.get(), self.phone.get(), self.company.get(), self.type.get(),
                data, hora, self.reason.get(), registrar_entrada=self.enter_now.get())
            self.clear()
            self.refresh()
            self._select_mobile('records')
            extra = 'Entrada registrada.' if registro else 'Entrada ainda não registrada.'
            self.app.toast('Cadastro concluído. Código %s.' % pessoa['Codigo'])
            messagebox.showinfo('Cadastro realizado', 'Pessoa cadastrada com sucesso!\n\nCódigo: %s\n%s' % (
                pessoa['Codigo'], extra), parent=self)
        self.app.execute(work, controls=[self.submit])


# --------------------------------------------------------------------------- Veículos
class VehiclesView(SplitPage):
    title = 'Veículos e placas'
    subtitle = 'Vincule veículos às pessoas cadastradas e use a placa na entrada.'
    form_label = '+ Novo veículo'
    list_label = 'Ver veículos'

    def build_form(self, f):
        p = self.p
        text(f, p, 'Novo veículo', size=16, weight='bold').pack(anchor='w')
        text(f, p, 'Dados obrigatórios marcados com *', muted=True).pack(anchor='w', pady=(3, 14))
        text(f, p, 'Proprietário (nome, CPF ou código) *', muted=True).pack(anchor='w')
        self.owner = PersonPicker(f, p, self.s)
        self.owner.pack(fill='x', pady=(4, 10))
        text(f, p, 'Placa * (ABC-1234 ou ABC1D23)', muted=True).pack(anchor='w')
        self.plate = plate_entry(f, p)
        self.plate.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Modelo *', muted=True).pack(anchor='w')
        self.model = entry(f, p, limit=40)
        self.model.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Cor', muted=True).pack(anchor='w')
        self.color = entry(f, p, limit=20)
        self.color.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Tipo de veículo *', muted=True).pack(anchor='w')
        self.kind = ttk.Combobox(f, values=TIPOS_VEICULO, state='readonly')
        self.kind.set(TIPOS_VEICULO[0])
        self.kind.pack(fill='x', pady=(4, 16))
        self.submit = button(f, p, 'Cadastrar veículo', self.create)
        self.submit.pack(fill='x')
        button(f, p, 'Limpar', self.clear, kind='secondary').pack(fill='x', pady=(8, 0))

    def build_list(self, f):
        p = self.p
        self.search = tk.StringVar()
        title_line = tk.Frame(f, bg=p.card)
        title_line.pack(fill='x')
        text(title_line, p, 'Veículos cadastrados', size=16, weight='bold').pack(side='left')
        self.total_text = text(title_line, p, '', muted=True)
        self.total_text.pack(side='right')
        self.search_entry = entry(f, p, textvariable=self.search)
        self.search_entry.pack(fill='x', ipady=8, pady=(15, 4))
        text(f, p, 'Busque por placa, modelo ou proprietário.', muted=True, size=9).pack(anchor='w', pady=(0, 8))
        self.search.trace_add('write', lambda *_: self.refresh())
        self.table = self.make_table(f, [('Placa', 'Placa', 90), ('Modelo', 'Modelo', 130), ('Cor', 'Cor', 80),
                                         ('Tipo', 'Tipo', 80), ('Codigo', 'Código', 70),
                                         ('Dono', 'Proprietário', 170)], selectmode='browse')
        row = tk.Frame(f, bg=p.card)
        row.pack(fill='x', pady=(14, 0))
        if self.s.pode('excluir'):
            button(row, p, 'Remover', self.remove, kind='danger').pack(side='left')
        button(row, p, 'Voltar', lambda: self.app.show_page('home'), kind='secondary').pack(side='right')

    def refresh(self):
        if not hasattr(self, 'table'):
            return
        from ..domain.validation import normalizar
        self.table.delete(*self.table.get_children())
        terms = normalizar(self.search.get()).split()
        shown = 0
        for v in reversed(self.s.veiculos):
            dono = (self.s.buscar_pessoa(v['Codigo']) or {}).get('Nome', '—')
            blob = normalizar(' '.join([v['Placa'], formatar_placa(v['Placa']), v['Modelo'], dono, v['Codigo']]))
            if all(t in blob for t in terms):
                self.table.insert('', 'end', iid=v['Id'], values=(
                    formatar_placa(v['Placa']), v['Modelo'], v['Cor'] or '—', v['Tipo'], v['Codigo'], dono))
                shown += 1
        self.counts.configure(text='%d veículos cadastrados' % len(self.s.veiculos))
        self.total_text.configure(text='%d exibido(s)' % shown)

    def clear(self):
        self.owner.clear()
        self.plate.clear()
        self.model.delete(0, 'end')
        self.color.delete(0, 'end')
        self.kind.set(TIPOS_VEICULO[0])

    def create(self):
        def work():
            v = self.s.cadastrar_veiculo(self.owner.code, self.plate.get(), self.model.get(),
                                         self.color.get(), self.kind.get())
            self.clear()
            self.refresh()
            self._select_mobile('records')
            self.app.toast('Veículo %s cadastrado.' % formatar_placa(v['Placa']))
        self.app.execute(work, controls=[self.submit])

    def remove(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning('Seleção necessária', 'Selecione um veículo.', parent=self)
            return
        if not messagebox.askyesno('Remover veículo', 'Remover o veículo selecionado? A ação será auditada.', parent=self):
            return
        def work():
            self.s.remover_veiculo(selected[0])
            self.refresh()
            self.app.toast('Veículo removido.')
        self.app.execute(work)


# --------------------------------------------------------------------------- Autorizações
class AuthorizationsView(SplitPage):
    title = 'Autorização de entrada'
    subtitle = 'Autorize antecipadamente uma pessoa (e um veículo) para uma data e horário limite.'
    form_label = '+ Nova autorização'
    list_label = 'Ver autorizações'

    def build_form(self, f):
        p = self.p
        can = self.s.pode('autorizar')
        text(f, p, 'Nova autorização', size=16, weight='bold').pack(anchor='w')
        text(f, p, ('Dados obrigatórios marcados com *' if can else
                    'Somente Adm e Admin Final emitem autorizações.'), muted=True,
             wraplength=290, justify='left').pack(anchor='w', pady=(3, 14))
        text(f, p, 'Pessoa (nome, CPF ou código) *', muted=True).pack(anchor='w')
        self.person = PersonPicker(f, p, self.s, on_change=self._person_changed)
        self.person.pack(fill='x', pady=(4, 10))
        text(f, p, 'Data e horário limite *', muted=True).pack(anchor='w')
        self.until = DateTimeInput(f, p)
        self.until.pack(fill='x', pady=(4, 10))
        text(f, p, 'Veículo (opcional)', muted=True).pack(anchor='w')
        self.vehicle = ttk.Combobox(f, state='readonly', values=())
        self.vehicle.pack(fill='x', pady=(4, 10))
        text(f, p, 'Motivo *', muted=True).pack(anchor='w')
        self.reason = entry(f, p, limit=120)
        self.reason.pack(fill='x', ipady=8, pady=(4, 16))
        self.submit = button(f, p, 'Autorizar entrada', self.create)
        self.submit.pack(fill='x')
        if not can:
            self.submit.configure(state='disabled')
        button(f, p, 'Limpar', self.clear, kind='secondary').pack(fill='x', pady=(8, 0))
        self._default_until()
        self._person_changed(self.person.code)

    NO_VEHICLE = 'Sem veículo'

    def _default_until(self):
        self.until.set(datetime.now().strftime('%d/%m/%Y') + ' 23:59')

    def _person_changed(self, code):
        if not hasattr(self, 'vehicle'):
            return
        plates = [formatar_placa(v['Placa']) + ' · ' + v['Modelo'] for v in self.s.veiculos_da_pessoa(code)]
        self.vehicle['values'] = [self.NO_VEHICLE] + plates
        self.vehicle.set(self.NO_VEHICLE)

    def build_list(self, f):
        p = self.p
        title_line = tk.Frame(f, bg=p.card)
        title_line.pack(fill='x')
        text(title_line, p, 'Autorizações emitidas', size=16, weight='bold').pack(side='left')
        self.total_text = text(title_line, p, '', muted=True)
        self.total_text.pack(side='right')
        text(f, p, 'Uma autorização ativa é consumida automaticamente na próxima entrada da pessoa.',
             muted=True, size=9, wraplength=520, justify='left').pack(anchor='w', pady=(10, 10))
        self.table = self.make_table(f, [('Id', 'Número', 70), ('Pessoa', 'Pessoa', 120), ('Data', 'Data', 84),
                                         ('Ate', 'Até', 50), ('Status', 'Situação', 82),
                                         ('Placa', 'Placa', 74), ('Motivo', 'Motivo', 130)],
                                    selectmode='browse')
        self.table.tag_configure('ativa', background=p.pill)
        row = tk.Frame(f, bg=p.card)
        row.pack(fill='x', pady=(14, 0))
        if self.s.pode('autorizar'):
            button(row, p, 'Cancelar autorização', self.cancel_auth, kind='danger').pack(side='left')
        button(row, p, 'Comprovante', self.receipt, kind='secondary').pack(side='left', padx=7)
        button(row, p, 'Voltar', lambda: self.app.show_page('home'), kind='secondary').pack(side='right')

    def refresh(self):
        if not hasattr(self, 'table'):
            return
        self.table.delete(*self.table.get_children())
        for a in reversed(self.s.autorizacoes):
            status = self.s.status_autorizacao(a)
            nome = (self.s.buscar_pessoa(a['Codigo']) or {}).get('Nome', a['Codigo'])
            self.table.insert('', 'end', iid=a['Id'], values=(
                a['Id'], nome, a['Data'], a['Ate'], status, formatar_placa(a['Placa']) or '—', a['Motivo']),
                tags=('ativa',) if status == 'Ativa' else ())
        ativas = sum(self.s.autorizacao_vigente(a) for a in self.s.autorizacoes)
        self.counts.configure(text='%d autorizações emitidas  ·  %d ativas agora' % (len(self.s.autorizacoes), ativas))
        self.total_text.configure(text='%d exibida(s)' % len(self.s.autorizacoes))

    def clear(self):
        self.person.clear()
        self._default_until()
        self.reason.delete(0, 'end')

    def create(self):
        data, hora = split_datetime(self.until.get())
        plate = ''
        if self.vehicle.get() and self.vehicle.get() != self.NO_VEHICLE:
            plate = self.vehicle.get().split(' · ')[0]
        def work():
            a = self.s.criar_autorizacao(self.person.code, data, hora, self.reason.get(), plate)
            self.clear()
            self.refresh()
            self._select_mobile('records')
            self.app.toast('Autorização %s emitida.' % a['Id'])
        self.app.execute(work, controls=[self.submit])

    def _selected(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning('Seleção necessária', 'Selecione uma autorização.', parent=self)
            return None
        return selected[0]

    def cancel_auth(self):
        key = self._selected()
        if not key:
            return
        if not messagebox.askyesno('Cancelar autorização', f'Cancelar a autorização {key}?', parent=self):
            return
        def work():
            self.s.cancelar_autorizacao(key)
            self.refresh()
            self._person_changed(self.person.code)
            self.app.toast('Autorização cancelada.')
        self.app.execute(work)

    def receipt(self):
        key = self._selected()
        if not key:
            return
        def work():
            html = self.s.comprovante_autorizacao_html(key)
            path = filedialog.asksaveasfilename(parent=self, defaultextension='.html',
                                                initialfile='autorizacao_%s.html' % key,
                                                filetypes=[('Página HTML', '*.html')])
            if not path:
                return
            with open(path, 'w', encoding='utf-8') as stream:
                stream.write(html)
            self.app.toast('Comprovante salvo.')
        self.app.execute(work)


# --------------------------------------------------------------------------- Início
class HomeView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.p.bg)
        self.app, self.s, self.p = app, app.service, app.p
        p = self.p
        user = self.s.sessao['usuario']
        text(self, p, 'Início', bg=p.bg, size=21, weight='bold').pack(anchor='w', padx=24, pady=(22, 3))
        text(self, p, 'Olá, %s. Veja o resumo da portaria e acesse as rotinas principais.' % user['NomeExibicao'],
             bg=p.bg, muted=True).pack(anchor='w', padx=24, pady=(0, 14))
        stats = self.s.estatisticas()
        row = tk.Frame(self, bg=p.bg)
        row.pack(fill='x', padx=24)
        items = [('Dentro agora', stats['dentro']), ('Entradas hoje', stats['entradas_hoje']),
                 ('Saídas hoje', stats['saidas_hoje']), ('Pessoas cadastradas', stats['pessoas']),
                 ('Autorizações ativas', stats['autorizacoes_ativas'])]
        for i, (label, value) in enumerate(items):
            row.columnconfigure(i, weight=1, uniform='stat')
            card = tk.Frame(row, bg=p.card, padx=16, pady=14, highlightbackground=p.border, highlightthickness=1)
            card.grid(row=0, column=i, sticky='ew', padx=(0 if i == 0 else 8, 0))
            text(card, p, str(value), size=24, weight='bold').pack(anchor='w')
            text(card, p, label, muted=True, size=9).pack(anchor='w')
        actions = tk.Frame(self, bg=p.bg)
        actions.pack(fill='x', padx=24, pady=(16, 8))
        button(actions, p, 'Cadastrar pessoa', lambda: app.show_page('register')).pack(side='left')
        button(actions, p, 'Registrar entrada / saída', lambda: app.show_page('records'),
               kind='secondary').pack(side='left', padx=8)
        button(actions, p, 'Ver relatórios', lambda: app.show_page('reports'), kind='secondary').pack(side='left')
        card = tk.Frame(self, bg=p.card, padx=18, pady=16, highlightbackground=p.border, highlightthickness=1)
        card.pack(fill='both', expand=True, padx=24, pady=(4, 18))
        text(card, p, 'Quem está dentro agora', size=15, weight='bold').pack(anchor='w', pady=(0, 10))
        grid = tk.Frame(card, bg=p.card)
        grid.pack(fill='both', expand=True)
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)
        cols = (('Codigo', 'Código', 70), ('Nome', 'Nome', 200), ('Tipo', 'Tipo', 100),
                ('Placa', 'Placa', 80), ('Entrada', 'Entrada', 130))
        self.table = ttk.Treeview(grid, columns=[c[0] for c in cols], show='headings', height=3)
        for key, title, width in cols:
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=60, anchor='w')
        self.table.grid(row=0, column=0, sticky='nsew')
        sy = ttk.Scrollbar(grid, orient='vertical', command=self.table.yview)
        sy.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=sy.set)
        inside = self.s.consultar(situacao='Dentro')
        for r in inside:
            self.table.insert('', 'end', values=(r.get('Codigo') or '—', r['Nome'], r['Tipo'],
                                                 formatar_placa(r.get('Placa', '')) or '—', r['Entrada']))
        if not inside:
            text(card, p, 'Ninguém dentro no momento.', muted=True).pack(anchor='w', pady=(8, 0))


# --------------------------------------------------------------------------- Relatórios
class ReportsView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.p.bg)
        self.app, self.s, self.p = app, app.service, app.p
        p = self.p
        head = tk.Frame(self, bg=p.bg)
        head.pack(fill='x', padx=24, pady=(22, 12))
        left = tk.Frame(head, bg=p.bg)
        left.pack(side='left')
        text(left, p, 'Relatórios', bg=p.bg, size=21, weight='bold').pack(anchor='w')
        text(left, p, 'Indicadores de movimento e exportação dos registros.', bg=p.bg, muted=True).pack(anchor='w', pady=(3, 0))
        if self.s.pode('exportar'):
            button(head, p, 'Exportar CSV', self.export).pack(side='right')
        st = self.s.estatisticas()
        summary = tk.Frame(self, bg=p.bg)
        summary.pack(fill='x', padx=24)
        for i, (label, value) in enumerate([('Dentro agora', st['dentro']), ('Entradas hoje', st['entradas_hoje']),
                                            ('Saídas hoje', st['saidas_hoje']), ('Veículos', st['veiculos'])]):
            summary.columnconfigure(i, weight=1, uniform='s')
            card = tk.Frame(summary, bg=p.card, padx=16, pady=12, highlightbackground=p.border, highlightthickness=1)
            card.grid(row=0, column=i, sticky='ew', padx=(0 if i == 0 else 8, 0))
            text(card, p, str(value), size=22, weight='bold').pack(anchor='w')
            text(card, p, label, muted=True, size=9).pack(anchor='w')
        charts = tk.Frame(self, bg=p.bg)
        charts.pack(fill='both', expand=True, padx=24, pady=(14, 18))
        charts.columnconfigure((0, 1), weight=1, uniform='c')
        charts.rowconfigure((0, 1), weight=1, uniform='r')
        self._chart(charts, 0, 0, 'Entradas nos últimos 7 dias', st['por_dia'])
        self._chart(charts, 0, 1, 'Entradas por tipo de acesso', st['por_tipo'])
        self._chart(charts, 1, 0, 'Entradas por hora do dia', st['por_hora'], span=2)

    def _chart(self, parent, row, column, title, data, span=1):
        card = tk.Frame(parent, bg=self.p.card, padx=14, pady=10, highlightbackground=self.p.border, highlightthickness=1)
        card.grid(row=row, column=column, columnspan=span, sticky='nsew',
                  padx=(0 if column == 0 else 8, 8 if column == 0 and span == 1 else 0),
                  pady=(0 if row == 0 else 8, 0))
        chart = BarChart(card, self.p, data, title=title, height=120)
        chart.pack(fill='both', expand=True)

    def export(self):
        def work():
            path = filedialog.asksaveasfilename(
                parent=self, defaultextension='.csv', initialfile='controle_de_acesso.csv',
                filetypes=[('Arquivo CSV', '*.csv'), ('Todos os arquivos', '*.*')])
            if not path:
                return
            total = self.s.exportar_csv(path)
            self.app.toast('%d registro(s) exportado(s).' % total)
            messagebox.showinfo('Exportação concluída',
                                '%d registro(s) exportado(s).\nO CPF é exportado de forma mascarada.' % total,
                                parent=self)
        self.app.execute(work)
