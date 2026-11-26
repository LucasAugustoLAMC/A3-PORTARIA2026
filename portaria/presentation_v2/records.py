"""Controle de entrada e saída: busca, filtro, registrar entrada/saída e edição validada."""
import tkinter as tk
from tkinter import ttk, messagebox

from .theme import FONT, button, entry, text
from .fields import DateTimeInput
from .layout import SplitPage
from .widgets import PersonPicker
from ..config import TIPOS_ACESSO
from ..application.gate_operations import SITUACOES
from ..domain.validation import formatar_placa


class RecordDialog(tk.Toplevel):
    def __init__(self, parent, p, record, types, *, checkout_only=False):
        super().__init__(parent)
        self.title('Registrar saída' if checkout_only else 'Editar registro')
        self.configure(bg=p.card)
        self.result = None
        self.resizable(True, False)
        self.minsize(620, 350 if checkout_only else 470)
        body = tk.Frame(self, bg=p.card, padx=25, pady=22)
        body.pack(fill='both', expand=True)
        text(body, p, 'Registrar saída' if checkout_only else 'Editar registro', size=19, weight='bold').pack(anchor='w')
        text(body, p, record['Nome'] + '  •  ' + record['Tipo'], muted=True).pack(anchor='w', pady=(3, 18))
        self.name = entry(body, p, limit=100)
        self.name.insert(0, record['Nome'])
        self.type = ttk.Combobox(body, values=types, state='readonly')
        self.type.set(record['Tipo'])
        if not checkout_only:
            text(body, p, 'Nome completo', muted=True).pack(anchor='w')
            self.name.pack(fill='x', ipady=8, pady=(3, 12))
            text(body, p, 'Tipo de acesso', muted=True).pack(anchor='w')
            self.type.pack(fill='x', pady=(3, 12))
            text(body, p, 'Entrada', muted=True).pack(anchor='w')
            self.in_date = DateTimeInput(body, p, initial=record['Entrada'])
            self.in_date.pack(fill='x', pady=(3, 12))
        else:
            self.in_date = None
            text(body, p, 'Entrada registrada: ' + record['Entrada'], muted=True).pack(anchor='w', pady=(0, 12))
        text(body, p, 'Saída (deixe vazia se ainda estiver presente)', muted=True).pack(anchor='w')
        self.out_date = DateTimeInput(body, p, initial=record['Saida'], optional=True)
        self.out_date.pack(fill='x', pady=(4, 18))
        if checkout_only and not record['Saida']:
            self.out_date.set_now()
        actions = tk.Frame(body, bg=p.card)
        actions.pack(fill='x')
        button(actions, p, 'Cancelar', self.destroy, kind='secondary').pack(side='right', padx=(8, 0))
        button(actions, p, 'Salvar alteração', self.confirm).pack(side='right')
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.wait_window()

    def confirm(self):
        self.result = {'Saida': self.out_date.get()}
        if self.in_date:
            self.result.update({'Nome': self.name.get().strip(), 'Tipo': self.type.get(),
                                'Entrada': self.in_date.get()})
        self.destroy()


class RecordsView(SplitPage):
    title = 'Controle de entrada e saída'
    subtitle = 'Registre entradas e saídas com o horário do sistema e acompanhe quem está dentro.'
    form_label = '+ Registrar entrada'
    list_label = 'Ver controle'
    form_min = 300

    def build_form(self, f):
        p = self.p
        text(f, p, 'Registrar entrada', size=16, weight='bold').pack(anchor='w')
        text(f, p, 'Pessoa já cadastrada. A hora de entrada é a do sistema.', muted=True,
             wraplength=260, justify='left').pack(anchor='w', pady=(3, 14))
        text(f, p, 'Pessoa (nome, CPF ou código) *', muted=True).pack(anchor='w')
        self.person = PersonPicker(f, p, self.s, on_change=self._person_changed)
        self.person.pack(fill='x', pady=(4, 8))
        self.state_label = text(f, p, '', muted=True, wraplength=250, justify='left')
        self.state_label.pack(anchor='w', pady=(0, 10))
        text(f, p, 'Veículo (opcional)', muted=True).pack(anchor='w')
        self.vehicle = ttk.Combobox(f, state='readonly', values=())
        self.vehicle.pack(fill='x', pady=(4, 10))
        text(f, p, 'Autorização de entrada', muted=True).pack(anchor='w')
        self.auth_label = text(f, p, '—', wraplength=260, justify='left')
        self.auth_label.pack(anchor='w', pady=(4, 16))
        self.submit = button(f, p, 'Registrar entrada', self.enter)
        self.submit.pack(fill='x')
        button(f, p, 'Cadastrar nova pessoa', lambda: self.app.show_page('register'),
               kind='secondary').pack(fill='x', pady=(8, 0))
        self._person_changed(self.person.code)

    NO_VEHICLE = 'Sem veículo'

    def _person_changed(self, code):
        if not hasattr(self, 'vehicle'):
            return
        plates = [formatar_placa(v['Placa']) + ' · ' + v['Modelo'] for v in self.s.veiculos_da_pessoa(code)]
        self.vehicle['values'] = [self.NO_VEHICLE] + plates
        self.vehicle.set(self.NO_VEHICLE)
        if not code:
            self.state_label.configure(text='Nenhuma pessoa selecionada.')
            self.auth_label.configure(text='—')
            return
        inside = self.s.situacao_pessoa(code) == 'Dentro'
        self.state_label.configure(text='Situação atual: ' + ('DENTRO — registre a saída antes de uma nova entrada.'
                                                              if inside else 'Saiu'))
        valid = self.s.autorizacoes_validas(code)
        self.auth_label.configure(text=('%s · até %s · %s (será usada automaticamente)' % (
            valid[0]['Id'], valid[0]['Ate'], valid[0]['Motivo'])) if valid else 'Sem autorização ativa hoje.')

    def build_list(self, f):
        p = self.p
        self.search = tk.StringVar()
        self.situation = tk.StringVar(value='Todos')
        title_line = tk.Frame(f, bg=p.card)
        title_line.pack(fill='x')
        text(title_line, p, 'Registros de acesso', size=16, weight='bold').pack(side='left')
        self.total_text = text(title_line, p, '', muted=True)
        self.total_text.pack(side='right')
        search_row = tk.Frame(f, bg=p.card)
        search_row.pack(fill='x', pady=(15, 6))
        search_row.columnconfigure(0, weight=1)
        self.search_entry = entry(search_row, p, textvariable=self.search)
        self.search_entry.grid(row=0, column=0, sticky='ew', ipady=8)
        self.situation_box = ttk.Combobox(search_row, textvariable=self.situation, state='readonly',
                                          values=list(SITUACOES), width=9)
        self.situation_box.grid(row=0, column=1, padx=(8, 0))
        self.situation_box.bind('<<ComboboxSelected>>', lambda _e: self.refresh())
        self.search.trace_add('write', lambda *_: self.refresh())
        text(f, p, 'Busque por nome, CPF, código ou placa. Filtro: Todos, Dentro ou Saiu.', muted=True,
             size=9).pack(anchor='w', pady=(0, 8))
        self.table = self.make_table(f, [('Codigo', 'Código', 64), ('Nome', 'Nome', 84), ('CPF', 'CPF', 96),
                                         ('Tipo', 'Tipo', 66), ('Entrada', 'Entrada', 98),
                                         ('Saida', 'Saída', 98), ('Situacao', 'Situação', 78),
                                         ('Placa', 'Placa', 66)])
        self.table.bind('<Double-1>', lambda _e: self.edit())
        self.table.bind('<<TreeviewSelect>>', self._row_selected)
        action_row = tk.Frame(f, bg=p.card)
        action_row.pack(fill='x', pady=(14, 0))
        self.checkout_btn = button(action_row, p, 'Registrar saída', self.checkout)
        self.checkout_btn.pack(side='left')
        if self.s.pode('editar'):
            button(action_row, p, 'Editar', self.edit, kind='secondary').pack(side='left', padx=7)
        button(action_row, p, 'Atualizar', self.reload, kind='secondary').pack(side='left')
        button(action_row, p, 'Voltar', lambda: self.app.show_page('home'), kind='secondary').pack(side='right')
        if self.s.pode('excluir'):
            button(action_row, p, 'Excluir', self.remove, kind='danger').pack(side='right', padx=(0, 7))

    def reload(self):
        self.person.reload()
        self.refresh()
        self.app.toast('Lista atualizada.')

    def _row_selected(self, _event=None):
        selected = self.table.selection()
        if len(selected) == 1:
            reg = self.s.buscar_registro(selected[0])
            if reg and reg.get('Codigo') and self.s.buscar_pessoa(reg['Codigo']):
                self.person.select(reg['Codigo'])

    def refresh(self):
        if not hasattr(self, 'table'):
            return
        selected = set(self.table.selection())
        self.table.delete(*self.table.get_children())
        rows = self.s.consultar(self.search.get(), self.situation.get())
        for reg in rows:
            tipo = reg['Tipo'] + (' ·temp.' if reg['Tipo'] not in TIPOS_ACESSO else '')
            self.table.insert('', 'end', iid=reg['Id'], values=(
                reg.get('Codigo') or '—', reg['Nome'], reg['CPFMascarado'], tipo,
                reg['Entrada'], reg['Saida'] or '—', reg['Situacao'],
                formatar_placa(reg.get('Placa', '')) or '—'), tags=('pending',) if reg['Situacao'] == 'Dentro' else ())
        for key in selected:
            if self.table.exists(key):
                self.table.selection_add(key)
        inside = sum(not r['Saida'] for r in self.s.registros)
        self.counts.configure(text=f'{len(self.s.registros)} entradas registradas  ·  {inside} pessoas dentro')
        self.total_text.configure(text=f'{len(rows)} exibido(s)')

    def enter(self):
        code = self.person.code
        if not code:
            messagebox.showwarning('Seleção necessária', 'Selecione uma pessoa cadastrada.', parent=self)
            return
        plate = ''
        if self.vehicle.get() and self.vehicle.get() != self.NO_VEHICLE:
            plate = self.vehicle.get().split(' · ')[0]
        def work():
            reg = self.s.registrar_entrada(code, placa=plate)
            self.refresh()
            self._person_changed(code)
            self._select_mobile('records')
            self.app.toast('Entrada registrada às ' + reg['Entrada'][11:] + '.')
        self.app.execute(work, controls=[self.submit])

    def one_record(self):
        selected = self.table.selection()
        if len(selected) != 1:
            messagebox.showwarning('Seleção necessária', 'Selecione exatamente um registro.', parent=self)
            return None
        return self.s.buscar_registro(selected[0])

    def checkout(self):
        reg = self.one_record()
        if not reg:
            return
        if reg['Saida']:
            messagebox.showinfo('Saída já registrada', 'Este registro já possui saída. Use Editar para corrigir.', parent=self)
            return
        if not messagebox.askyesno('Registrar saída', f'Registrar a saída de {reg["Nome"]} agora?', parent=self):
            return
        def work():
            done = self.s.registrar_saida(reg['Id'])
            self.refresh()
            self._person_changed(self.person.code)
            self.app.toast('Saída registrada às ' + done['Saida'][11:] + '.')
        self.app.execute(work)

    def edit(self):
        reg = self.one_record()
        if not reg:
            return
        only_checkout = not self.s.pode('editar') and not reg['Saida']
        if not self.s.pode('editar') and not only_checkout:
            messagebox.showwarning('Sem permissão', 'Seu cargo não pode editar este registro.', parent=self)
            return
        dialog = RecordDialog(self, self.p, reg, TIPOS_ACESSO + self.s.tipos_temporarios_ativos(),
                              checkout_only=only_checkout)
        if dialog.result is not None:
            def work():
                self.s.atualizar_registro(reg['Id'], dialog.result)
                self.refresh()
                self.app.toast('Alteração salva.')
            self.app.execute(work)

    def remove(self):
        ids = self.table.selection()
        if not ids:
            messagebox.showwarning('Seleção necessária', 'Selecione os registros a excluir.', parent=self)
            return
        if not messagebox.askyesno('Confirmar exclusão',
                f'Excluir {len(ids)} registro(s)? Esta ação será registrada na auditoria.', parent=self):
            return
        def work():
            n = self.s.excluir(ids)
            self.refresh()
            self._person_changed(self.person.code)
            self.app.toast(f'{n} registro(s) excluído(s).')
        self.app.execute(work)
