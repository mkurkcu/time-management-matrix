#!/usr/bin/env python3
"""Eisenhower matrix desktop app. Python 3, standard library only."""
import csv
import json
import math
import os
import uuid
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

DATA = Path.home() / 'EisenhowerMatrix' / 'tasks.json'
COLORS = {'Q1': '#ef4444', 'Q2': '#3b82f6', 'Q3': '#f59e0b', 'Q4': '#94a3b8'}
TITLES = {'Q1': 'Q1 · Acil + Önemli', 'Q2': 'Q2 · Önemli',
          'Q3': 'Q3 · Acil', 'Q4': 'Q4 · Düşük öncelik'}


def quadrant(u, i):
    return ('Q1' if u >= 6 else 'Q2') if i >= 6 else ('Q3' if u >= 6 else 'Q4')


class App:
    def __init__(self, root):
        self.root = root
        root.title('Eisenhower Matrisi · PC')
        root.geometry('1150x770')
        root.minsize(870, 600)
        self.tasks = self.load()
        self.positions = []
        self.query = tk.StringVar()
        self.show_done = tk.BooleanVar(value=True)
        self.status = tk.StringVar()
        self.build()
        self.refresh()

    def load(self):
        try:
            data = json.loads(DATA.read_text(encoding='utf-8'))
            if not isinstance(data, list):
                raise ValueError('Beklenmeyen veri biçimi')
            for t in data:
                t.setdefault('id', uuid.uuid4().hex)
                t.setdefault('done', False)
                t.setdefault('note', '')
                t.setdefault('due', '')
            return data
        except FileNotFoundError:
            return []
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror('Veri okunamadı', f'{DATA}\n\n{exc}\n\nDosya değiştirilmedi.')
            return []

    def save(self):
        try:
            DATA.parent.mkdir(parents=True, exist_ok=True)
            temp = DATA.with_suffix('.tmp')
            temp.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, DATA)
        except OSError as exc:
            messagebox.showerror('Kaydetme hatası', str(exc))

    def build(self):
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill='x')
        ttk.Label(top, text='Eisenhower Matrisi', font=('Arial', 20, 'bold')).pack(side='left')
        ttk.Button(top, text='+ Aktivite ekle', command=self.edit_dialog).pack(side='right', padx=5)
        ttk.Button(top, text='CSV dışa aktar', command=self.export).pack(side='right', padx=5)
        ttk.Button(top, text='JSON yedeği', command=self.backup).pack(side='right', padx=5)

        bar = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        bar.pack(fill='x')
        ttk.Label(bar, text='Ara:').pack(side='left')
        ttk.Entry(bar, textvariable=self.query, width=34).pack(side='left', padx=7)
        self.query.trace_add('write', lambda *_: self.refresh())
        ttk.Checkbutton(bar, text='Tamamlananları göster', variable=self.show_done,
                        command=self.refresh).pack(side='left', padx=12)
        ttk.Label(bar, text='Puanlar 1–10; 6 ve üstü yüksek sayılır.').pack(side='right')

        pane = ttk.Panedwindow(self.root, orient='horizontal')
        pane.pack(fill='both', expand=True, padx=12, pady=(0, 7))
        matrix_frame = ttk.Frame(pane)
        list_frame = ttk.Frame(pane)
        pane.add(matrix_frame, weight=3)
        pane.add(list_frame, weight=2)
        self.canvas = tk.Canvas(matrix_frame, background='#f8fafc', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda _: self.draw())
        self.canvas.bind('<Button-1>', self.click_point)
        self.canvas.bind('<Motion>', self.hover_point)
        ttk.Label(list_frame, text='Aktiviteler · Q1 → Q2 → Q3 → Q4',
                  font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 6))
        columns = ('task', 'urgency', 'importance', 'due', 'state')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', selectmode='browse')
        self.tree.heading('#0', text='Kare')
        for key, title in zip(columns, ('Aktivite', 'Aciliyet', 'Önem', 'Son tarih', 'Durum')):
            self.tree.heading(key, text=title)
        self.tree.column('#0', width=46, stretch=False)
        self.tree.column('task', width=190, minwidth=100)
        self.tree.column('urgency', width=64, stretch=False)
        self.tree.column('importance', width=55, stretch=False)
        self.tree.column('due', width=86, stretch=False)
        self.tree.column('state', width=70, stretch=False)
        scroll = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.tree.bind('<Double-1>', self.open_selected)
        self.tree.bind('<Return>', self.open_selected)
        ttk.Label(self.root, textvariable=self.status, padding=(12, 0, 12, 8)).pack(fill='x')

    def visible(self):
        needle = self.query.get().strip().casefold()
        return [(n, t) for n, t in enumerate(self.tasks)
                if (self.show_done.get() or not t['done'])
                and (needle in t['name'].casefold() or needle in t.get('note', '').casefold())]

    def refresh(self):
        if not hasattr(self, 'tree'):
            return
        self.tree.delete(*self.tree.get_children())
        shown = sorted(self.visible(), key=lambda pair: (
            int(quadrant(pair[1]['urgency'], pair[1]['importance'])[1]),
            pair[1]['done'], pair[1].get('due') or '9999-99-99',
            -(pair[1]['urgency'] + pair[1]['importance'])))
        for _, t in shown:
            self.tree.insert('', 'end', iid=t['id'], text=quadrant(t['urgency'], t['importance']),
                             values=(t['name'], t['urgency'], t['importance'], t.get('due', ''),
                                     'Bitti' if t['done'] else 'Açık'))
        self.status.set(f'{len(self.tasks)} aktivite · {sum(not t["done"] for t in self.tasks)} açık · '
                        f'{len(shown)} görünür · Veri: {DATA}')
        self.draw()

    def draw(self):
        if not hasattr(self, 'canvas'):
            return
        c = self.canvas
        c.delete('all')
        self.positions.clear()
        w, h = c.winfo_width(), c.winfo_height()
        side = min(w - 95, h - 100)
        if side < 160:
            return
        left, top = (w - side) / 2 + 12, (h - side) / 2 - 10
        right, bottom = left + side, top + side
        middle_x, middle_y = (left + right) / 2, (top + bottom) / 2
        quadrants = [((left, top, middle_x, middle_y), 'Q1'),
                     ((middle_x, top, right, middle_y), 'Q2'),
                     ((left, middle_y, middle_x, bottom), 'Q3'),
                     ((middle_x, middle_y, right, bottom), 'Q4')]
        for box, q in quadrants:
            c.create_rectangle(*box, fill={'Q1':'#fff1f2','Q2':'#eff6ff',
                                            'Q3':'#fffbeb','Q4':'#f1f5f9'}[q], outline='#cbd5e1')
            x1, y1, x2, y2 = box
            c.create_text((x1+x2)/2, y1+20, text=TITLES[q], fill=COLORS[q],
                          font=('Arial', 11, 'bold'))
        c.create_rectangle(left, top, right, bottom, outline='#475569', width=2)
        c.create_text((left+right)/2, bottom+32, text='← ACİLİYET ARTAR (10 solda · 1 sağda)',
                      fill='#334155', font=('Arial', 10, 'bold'))
        c.create_text(left-29, (top+bottom)/2, text='ÖNEM ↑', angle=90,
                      fill='#334155', font=('Arial', 10, 'bold'))
        c.create_text(left, bottom+12, text='10', fill='#64748b')
        c.create_text(right, bottom+12, text='1', fill='#64748b')
        c.create_text(left-13, top, text='10', fill='#64748b')
        c.create_text(left-10, bottom, text='1', fill='#64748b')
        groups = {}
        for _, t in self.visible():
            groups.setdefault((t['urgency'], t['importance']), []).append(t)
        for (u, i), group in groups.items():
            x = right - (u - 1) / 9 * side
            y = bottom - (i - 1) / 9 * side
            q = quadrant(u, i)
            radius = 13 if len(group) > 1 else 11
            c.create_oval(x-radius, y-radius, x+radius, y+radius,
                          fill='#cbd5e1' if all(t['done'] for t in group) else COLORS[q],
                          outline='white', width=2)
            if len(group) > 1:
                c.create_text(x, y, text=str(len(group)), fill='#0f172a', font=('Arial', 9, 'bold'))
            self.positions.append((x, y, radius+8, group))

    def nearest(self, x, y):
        matches = [(math.hypot(x-px, y-py), group) for px, py, reach, group in self.positions
                   if math.hypot(x-px, y-py) <= reach]
        return min(matches, default=(None, None), key=lambda t: t[0])[1]

    def hover_point(self, event):
        group = self.nearest(event.x, event.y)
        self.canvas.configure(cursor='hand2' if group else '')

    def click_point(self, event):
        group = self.nearest(event.x, event.y)
        if not group:
            return
        if len(group) == 1:
            self.edit_dialog(group[0]['id'])
        else:
            self.choose_group(group)

    def choose_group(self, group):
        window = tk.Toplevel(self.root)
        window.title('Aynı puandaki aktiviteler')
        window.transient(self.root)
        window.grab_set()
        ttk.Label(window, text=f'{len(group)} aktivite aynı noktada', padding=12).pack()
        for task in group:
            ttk.Button(window, text=task['name'], command=lambda tid=task['id']:
                       (window.destroy(), self.edit_dialog(tid))).pack(fill='x', padx=12, pady=3)

    def open_selected(self, _=None):
        selection = self.tree.selection()
        if selection:
            self.edit_dialog(selection[0])

    def edit_dialog(self, task_id=None):
        task = next((t for t in self.tasks if t['id'] == task_id), None)
        win = tk.Toplevel(self.root)
        win.title('Aktiviteyi düzenle' if task else 'Aktivite ekle')
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        form = ttk.Frame(win, padding=18)
        form.pack(fill='both')
        name = tk.StringVar(value=task['name'] if task else '')
        urgency = tk.StringVar(value=str(task['urgency']) if task else '5')
        importance = tk.StringVar(value=str(task['importance']) if task else '5')
        due = tk.StringVar(value=task.get('due', '') if task else '')
        done = tk.BooleanVar(value=task['done'] if task else False)
        for row, (label, var) in enumerate((('Aktivite adı', name), ('Aciliyet (1–10)', urgency),
                                            ('Önem (1–10)', importance), ('Son tarih (YYYY-AA-GG, isteğe bağlı)', due))):
            ttk.Label(form, text=label).grid(row=row*2, column=0, sticky='w', pady=(7, 2))
            ttk.Entry(form, textvariable=var, width=42).grid(row=row*2+1, column=0, sticky='ew')
        ttk.Label(form, text='Not').grid(row=8, column=0, sticky='w', pady=(7, 2))
        note = tk.Text(form, width=42, height=4, wrap='word')
        note.grid(row=9, column=0)
        note.insert('1.0', task.get('note', '') if task else '')
        ttk.Checkbutton(form, text='Tamamlandı', variable=done).grid(row=10, column=0, sticky='w', pady=8)
        buttons = ttk.Frame(form)
        buttons.grid(row=11, column=0, sticky='ew', pady=8)

        def commit():
            title = name.get().strip()
            try:
                u, i = int(urgency.get()), int(importance.get())
                if not title or not (1 <= u <= 10 and 1 <= i <= 10):
                    raise ValueError('Ad gir ve iki puanı da 1–10 arasında seç.')
                deadline = due.get().strip()
                if deadline and date.fromisoformat(deadline).isoformat() != deadline:
                    raise ValueError('Son tarih YYYY-AA-GG biçiminde olmalı.')
            except ValueError as exc:
                messagebox.showerror('Girdiyi kontrol et', str(exc), parent=win)
                return
            fields = dict(name=title, urgency=u, importance=i, due=deadline,
                          note=note.get('1.0', 'end-1c').strip(), done=done.get())
            if task:
                task.update(fields)
            else:
                self.tasks.append(dict(id=uuid.uuid4().hex, **fields))
            self.save()
            self.refresh()
            win.destroy()

        ttk.Button(buttons, text='Kaydet', command=commit).pack(side='left')
        ttk.Button(buttons, text='Vazgeç', command=win.destroy).pack(side='left', padx=7)
        if task:
            def delete():
                if messagebox.askyesno('Sil', f'“{task["name"]}” silinsin mi?', parent=win):
                    self.tasks.remove(task)
                    self.save()
                    self.refresh()
                    win.destroy()
            ttk.Button(buttons, text='Sil', command=delete).pack(side='right')
        win.bind('<Escape>', lambda _: win.destroy())

    def backup(self):
        target = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')],
                                              initialfile='eisenhower_yedek.json')
        if target:
            try:
                Path(target).write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError as exc:
                messagebox.showerror('Yedek hatası', str(exc))

    def export(self):
        target = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')],
                                              initialfile='eisenhower_aktiviteler.csv')
        if target:
            try:
                with open(target, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Aktivite', 'Quadrant', 'Aciliyet', 'Önem', 'Son tarih', 'Tamamlandı', 'Not'])
                    for t in self.tasks:
                        writer.writerow([t['name'], quadrant(t['urgency'], t['importance']),
                                         t['urgency'], t['importance'], t.get('due', ''),
                                         'Evet' if t['done'] else 'Hayır', t.get('note', '')])
            except OSError as exc:
                messagebox.showerror('Dışa aktarma hatası', str(exc))


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
