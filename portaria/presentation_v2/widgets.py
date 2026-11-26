"""Componentes reutilizáveis: campos formatados, seletor de pessoa e gráfico de barras."""
import tkinter as tk
from tkinter import ttk

from .theme import FONT, entry, text
from ..domain.validation import so_digitos, formatar_cpf, formatar_telefone, formatar_placa, normalizar_placa


class FormattedEntry(tk.Entry):
    """Entry que reformata enquanto o usuário digita (CPF, telefone, placa).

    O cursor é reposicionado pela quantidade de caracteres úteis à esquerda dele,
    então digitar no meio ou no fim nunca empurra ou perde caracteres.
    """

    def __init__(self, parent, p, formatter, *, max_chars, **kwargs):
        super().__init__(parent, relief='flat', borderwidth=0, bg=p.field, fg=p.text,
                         insertbackground=p.text, highlightthickness=1, highlightcolor=p.primary,
                         highlightbackground=p.border, font=(FONT, 11), **kwargs)
        self._formatter, self._max = formatter, max_chars
        self._busy = False
        self.bind('<KeyRelease>', self._on_change, add='+')
        self.bind('<<Paste>>', lambda _e: self.after_idle(self._on_change), add='+')
        self.bind('<<Cut>>', lambda _e: self.after_idle(self._on_change), add='+')

    @staticmethod
    def _core(texto):
        return ''.join(c for c in texto if c.isalnum())

    def _on_change(self, _event=None):
        if self._busy:
            return
        self._busy = True
        try:
            raw = self.get()
            useful_left = len(self._core(raw[:self.index('insert')]))
            formatted = self._formatter(raw)[:self._max]
            if formatted != raw:
                super().delete(0, 'end')
                super().insert(0, formatted)
            # volta o cursor para depois do mesmo número de caracteres úteis
            pos, seen = 0, 0
            while pos < len(formatted) and seen < useful_left:
                if formatted[pos].isalnum():
                    seen += 1
                pos += 1
            self.icursor(pos)
        finally:
            self._busy = False

    def insert(self, index, string):  # uso programático também formata
        super().insert(index, string)
        self._on_change()

    def clear(self):
        super().delete(0, 'end')


def cpf_entry(parent, p):
    return FormattedEntry(parent, p, formatar_cpf, max_chars=14)


def phone_entry(parent, p):
    return FormattedEntry(parent, p, formatar_telefone, max_chars=15)


def plate_entry(parent, p):
    def fmt(raw):
        norm = normalizar_placa(raw)[:7]
        return formatar_placa(norm) if len(norm) == 7 else norm
    return FormattedEntry(parent, p, fmt, max_chars=8)


class PersonPicker(tk.Frame):
    """Busca por nome, CPF ou código e lista de resultados em Combobox."""

    def __init__(self, parent, p, service, *, on_change=None):
        super().__init__(parent, bg=p.card)
        self.p, self.s, self._on_change = p, service, on_change
        self._map = {}
        self.search = entry(self, p)
        self.search.pack(fill='x', ipady=7)
        self.combo = ttk.Combobox(self, state='readonly')
        self.combo.pack(fill='x', pady=(6, 0))
        self.search.bind('<KeyRelease>', lambda _e: self.reload())
        self.combo.bind('<<ComboboxSelected>>', lambda _e: self._on_change and self._on_change(self.code))
        self.reload()

    def reload(self):
        found = self.s.pesquisar_pessoas(self.search.get())[:50]
        self._map = {'%s · %s' % (x['Codigo'], x['Nome']): x['Codigo'] for x in found}
        atual = self.combo.get()
        self.combo['values'] = list(self._map)
        if atual not in self._map:
            self.combo.set(next(iter(self._map), ''))
            if self._on_change:
                self._on_change(self.code)

    @property
    def code(self):
        return self._map.get(self.combo.get(), '')

    def select(self, codigo):
        pessoa = self.s.buscar_pessoa(codigo)
        if not pessoa:
            return
        self.search.delete(0, 'end')
        self.reload()
        label = '%s · %s' % (pessoa['Codigo'], pessoa['Nome'])
        if label in self._map:
            self.combo.set(label)
            if self._on_change:
                self._on_change(codigo)

    def clear(self):
        self.search.delete(0, 'end')
        self.reload()


class BarChart(tk.Canvas):
    """Gráfico de barras desenhado em Canvas (sem dependências externas)."""

    def __init__(self, parent, p, data, *, title='', height=200, horizontal=False):
        super().__init__(parent, bg=p.card, highlightthickness=0, height=height)
        self.p, self.data, self.title, self.horizontal = p, list(data), title, horizontal
        self.bind('<Configure>', lambda _e: self.draw())

    def set_data(self, data):
        self.data = list(data)
        self.draw()

    def draw(self):
        self.delete('all')
        p, w, h = self.p, max(self.winfo_width(), 120), max(self.winfo_height(), 80)
        self.create_text(2, 4, anchor='nw', text=self.title, fill=p.text, font=(FONT, 11, 'bold'))
        if not self.data or not any(v for _l, v in self.data):
            self.create_text(w / 2, h / 2 + 8, text='Sem dados para exibir', fill=p.muted, font=(FONT, 10))
            return
        top, bottom, left, right = 34, 24, 8, 8
        peak = max(v for _l, v in self.data)
        n = len(self.data)
        slot = (w - left - right) / n
        bar = max(4, min(46, slot * 0.62))
        base = h - bottom
        usable = base - top - 14
        for i, (label, value) in enumerate(self.data):
            x0 = left + i * slot + (slot - bar) / 2
            y0 = base - usable * value / peak if value else base - 1
            self.create_rectangle(x0, y0, x0 + bar, base, fill=p.primary, outline='')
            if value:
                self.create_text(x0 + bar / 2, y0 - 3, anchor='s', text=str(value), fill=p.text, font=(FONT, 9, 'bold'))
            if n <= 12 or i % 3 == 0:
                self.create_text(x0 + bar / 2, base + 4, anchor='n', text=label, fill=p.muted, font=(FONT, 8))
        self.create_line(left, base, w - right, base, fill=p.border)
