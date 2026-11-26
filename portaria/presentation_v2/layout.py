"""Página em duas colunas (formulário + lista) que vira alternância em janelas estreitas."""
import tkinter as tk
from tkinter import ttk

from .theme import text, button


class SplitPage(tk.Frame):
    """Estrutura comum de Cadastro, Controle, Veículos e Autorizações.

    Subclasses implementam `build_form(card)` e `build_list(card)`.
    Nomes preservados da versão 2.0: form_holder, form_card, list_card, _narrow, _select_mobile.
    """
    title = ''
    subtitle = ''
    form_label = '+ Novo'
    list_label = 'Ver lista'
    form_min = 400

    def __init__(self, parent, app):
        super().__init__(parent, bg=app.p.bg)
        self.app, self.s, self.p = app, app.service, app.p
        self._narrow = None
        self._mobile_page = 'records'
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._header()
        self.body = tk.Frame(self, bg=self.p.bg)
        self.body.grid(row=1, column=0, sticky='nsew', padx=23, pady=(0, 15))
        self.form_holder = tk.Frame(self.body, bg=self.p.bg)
        self.form_holder.columnconfigure(0, weight=1)
        self.form_holder.rowconfigure(0, weight=1)
        self.form_canvas = tk.Canvas(self.form_holder, bg=self.p.bg, highlightthickness=0,
                                     width=self.form_min - 20, height=100)
        self.form_canvas.grid(row=0, column=0, sticky='nsew')
        self.form_scroll = ttk.Scrollbar(self.form_holder, orient='vertical', command=self.form_canvas.yview)
        self.form_scroll.grid(row=0, column=1, sticky='ns')
        self.form_canvas.configure(yscrollcommand=self.form_scroll.set)
        self.form_card = tk.Frame(self.form_canvas, bg=self.p.card, padx=20, pady=19,
                                  highlightbackground=self.p.border, highlightthickness=1)
        self.form_window = self.form_canvas.create_window(0, 0, window=self.form_card, anchor='nw')
        self.form_card.bind('<Configure>', lambda _e: self.form_canvas.configure(
            scrollregion=self.form_canvas.bbox('all')))
        self.form_canvas.bind('<Configure>', lambda e: self.form_canvas.itemconfigure(
            self.form_window, width=e.width - 1))
        self.form_canvas.bind('<MouseWheel>', self._wheel)
        self.form_canvas.bind('<Button-4>', self._wheel)
        self.form_canvas.bind('<Button-5>', self._wheel)
        self.build_form(self.form_card)
        self._bind_wheel(self.form_card)
        self.list_card = tk.Frame(self.body, bg=self.p.card, padx=18, pady=17,
                                  highlightbackground=self.p.border, highlightthickness=1)
        self.build_list(self.list_card)
        self.body.bind('<Configure>', self._layout)
        self.refresh()

    def _bind_wheel(self, widget):
        """Roda do mouse rola o formulário mesmo sobre campos e botões."""
        for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(seq, self._wheel, add='+')
        for child in widget.winfo_children():
            if not isinstance(child, ttk.Combobox):  # na lista suspensa a roda troca o valor
                self._bind_wheel(child)

    def _wheel(self, event):
        if self.form_card.winfo_height() <= self.form_canvas.winfo_height():
            return
        step = -1 if (getattr(event, 'num', 0) == 4 or getattr(event, 'delta', 0) > 0) else 1
        self.form_canvas.yview_scroll(step, 'units')

    def _header(self):
        header = tk.Frame(self, bg=self.p.bg)
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(18, 14))
        text(header, self.p, self.title, bg=self.p.bg, size=21, weight='bold').pack(anchor='w')
        text(header, self.p, self.subtitle, bg=self.p.bg, muted=True).pack(anchor='w', pady=(3, 0))
        self.counts = text(header, self.p, '', bg=self.p.bg, muted=True)
        self.counts.pack(anchor='w', pady=(9, 0))
        self.mobile_controls = tk.Frame(header, bg=self.p.bg)
        button(self.mobile_controls, self.p, self.list_label, lambda: self._select_mobile('records'),
               kind='secondary').pack(side='left', padx=(0, 8))
        button(self.mobile_controls, self.p, self.form_label, lambda: self._select_mobile('form')).pack(side='left')

    def build_form(self, card):  # pragma: no cover - interface
        raise NotImplementedError

    def build_list(self, card):  # pragma: no cover - interface
        raise NotImplementedError

    def refresh(self):  # pragma: no cover - interface
        pass

    def _select_mobile(self, page):
        self._mobile_page = page
        if self._narrow:
            self.form_holder.grid_forget()
            self.list_card.grid_forget()
            if page == 'form':
                self.form_holder.grid(row=0, column=0, sticky='nsew')
            else:
                self.list_card.grid(row=0, column=0, sticky='nsew')

    def _layout(self, event):
        narrow = event.width < 925
        if narrow == self._narrow:
            return
        self._narrow = narrow
        self.form_holder.grid_forget()
        self.list_card.grid_forget()
        if narrow:
            self.mobile_controls.pack(anchor='w', pady=(9, 0))
            self.body.columnconfigure(0, weight=1, minsize=0)
            self.body.columnconfigure(1, weight=0, minsize=0)
            self.body.rowconfigure(0, weight=1)
            self._select_mobile(self._mobile_page)
        else:
            self.mobile_controls.pack_forget()
            self.body.columnconfigure(0, weight=0, minsize=self.form_min)
            self.body.columnconfigure(1, weight=1)
            self.body.rowconfigure(0, weight=1)
            self.form_holder.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
            self.list_card.grid(row=0, column=1, sticky='nsew')

    def make_table(self, parent, columns, *, height=3, selectmode='extended'):
        """columns: [(chave, título, largura)] → Treeview com barras de rolagem."""
        grid = tk.Frame(parent, bg=self.p.card)
        grid.pack(fill='both', expand=True)
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)
        table = ttk.Treeview(grid, columns=[c[0] for c in columns], show='headings',
                             selectmode=selectmode, height=height)
        for key, title, width in columns:
            table.heading(key, text=title)
            table.column(key, width=width, minwidth=60, anchor='w', stretch=True)
        table.grid(row=0, column=0, sticky='nsew')
        vert = ttk.Scrollbar(grid, orient='vertical', command=table.yview)
        vert.grid(row=0, column=1, sticky='ns')
        horiz = ttk.Scrollbar(grid, orient='horizontal', command=table.xview)
        horiz.grid(row=1, column=0, sticky='ew')
        table.configure(yscrollcommand=vert.set, xscrollcommand=horiz.set)
        table.tag_configure('pending', background=self.p.pill)
        return table
