"""Contextual property panel with exact numeric (mm) editing."""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import i18n
from i18n import T, tr
from model import ensure_cells
from symbols import SYMBOLS
from textshape import has_rtl, shape
from ui.common import (BTN, MUTED, PRIMARY, AutoLabel, Field, IconButton, Panel, TButton,
                       TextField, TLabel, hrow, latin_digits)

PALETTE = [None, '#000000', '#ffffff', '#c62828', '#1565c0', '#2e7d32', '#ffd200',
           '#ef6c00', '#616161', '#0d2b57']


def fmt(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ''
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return s if s != '-0' else '0'


class NumField(BoxLayout):
    def __init__(self, label, value, on_commit, step=1.0, minv=None, maxv=None,
                 integer=False, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(74))
        kw.setdefault('spacing', dp(2))
        super().__init__(**kw)
        self.on_commit = on_commit
        self.step, self.minv, self.maxv, self.integer = step, minv, maxv, integer
        self.add_widget(TLabel(text=label, size_hint_y=None, height=dp(22), font_size=sp(13),
                               color=MUTED))
        row = BoxLayout(spacing=dp(3))
        self.minus = TButton(text='-', size_hint=(None, None), width=dp(38), height=dp(44),
                             font_size=sp(20))
        self.plus = TButton(text='+', size_hint=(None, None), width=dp(38), height=dp(44),
                            font_size=sp(20))
        self.inp = Field(text=fmt(value), height=dp(44), halign='center',
                         input_type='number')
        self.minus.bind(on_release=lambda *a: self.bump(-1))
        self.plus.bind(on_release=lambda *a: self.bump(1))
        self.inp.bind(on_text_validate=lambda *a: self.commit())
        self.inp.bind(focus=lambda w, f: (not f) and self.commit())
        row.add_widget(self.minus)
        row.add_widget(self.inp)
        row.add_widget(self.plus)
        self.add_widget(row)
        self._last = fmt(value)

    def value(self):
        try:
            v = float(latin_digits(self.inp.text).replace(',', '.'))
        except ValueError:
            return None
        if self.integer:
            v = int(round(v))
        if self.minv is not None:
            v = max(self.minv, v)
        if self.maxv is not None:
            v = min(self.maxv, v)
        return v

    def bump(self, d):
        v = self.value()
        if v is None:
            v = 0
        st = self.step() if callable(self.step) else self.step
        self.inp.text = fmt(round(v + d * st, 3))
        self.commit()

    def commit(self):
        v = self.value()
        if v is None:
            self.inp.text = self._last
            return
        txt = fmt(v)
        self.inp.text = txt
        if txt != self._last:
            self._last = txt
            self.on_commit(v)

    def set_value(self, v):
        if not self.inp.focus:
            self._last = fmt(v)
            self.inp.text = self._last


class ColorRow(BoxLayout):
    def __init__(self, label, value, on_pick, allow_none=True, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(66))
        super().__init__(**kw)
        self.add_widget(TLabel(text=label, size_hint_y=None, height=dp(22), font_size=sp(13),
                               color=MUTED))
        row = BoxLayout(spacing=dp(3), size_hint_y=None, height=dp(40))
        for c in PALETTE:
            if c is None and not allow_none:
                continue
            if c is None:
                b = TButton(text='×', font_size=sp(18), height=dp(40))
            else:
                rgb = tuple(int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5)) + (1,)
                b = TButton(text='', background_color=rgb if c != '#ffffff' else (0.99, 0.99, 0.99, 1),
                            height=dp(40))
                if c == '#ffffff':
                    from kivy.graphics import Color as _C, Line as _L
                    with b.canvas.after:
                        _C(0.6, 0.63, 0.67, 1)
                        ln = _L(rectangle=(0, 0, 1, 1), width=dp(1))
                    b.bind(pos=lambda w, *_a, l=ln: setattr(l, 'rectangle', (w.x + 1, w.y + 1, w.width - 2, w.height - 2)),
                           size=lambda w, *_a, l=ln: setattr(l, 'rectangle', (w.x + 1, w.y + 1, w.width - 2, w.height - 2)))
            if (value or None) == c:
                b.text = '•' if c is not None else '[×]'
                b.color = (1, 1, 1, 1) if c not in ('#ffffff', '#ffd200', None) else (0, 0, 0, 1)
            b.bind(on_release=lambda w, cc=c: on_pick(cc))
            row.add_widget(b)
        self.add_widget(row)


class PropertyPanel(Panel):
    def __init__(self, editor, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', dp(8))
        super().__init__(**kw)
        self.editor = editor
        self.sv = ScrollView(do_scroll_x=False, bar_width=dp(6))
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6),
                               padding=(dp(6), 0, dp(14), 0))
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.sv.add_widget(self.grid)
        self.add_widget(self.sv)
        self.nums = {}
        self.text_input = None

    # helpers --------------------------------------------------------------
    def _el(self):
        ed = self.editor
        if len(ed.sel) == 1:
            return ed.doc.get(ed.sel[0])
        return None

    def _set(self, key, val, el=None):
        e = el or self._el()
        if e is None:
            return
        e[key] = val
        self.editor.commit()

    def pair(self, a, b):
        g = GridLayout(cols=2, size_hint_y=None, height=dp(74), spacing=dp(8))
        if i18n.is_fa():
            a, b = b, a
        g.add_widget(a)
        g.add_widget(b)
        return g

    def num(self, key, label, value, cb, **kw):
        nf = NumField(T(label), value, cb, **kw)
        self.nums[key] = nf
        return nf

    def title(self, text):
        self.grid.add_widget(TLabel(text=text, size_hint_y=None, height=dp(30), bold=True,
                                    font_size=sp(17), color=PRIMARY))

    def toggle(self, label, value, cb):
        b = TButton(text=('• ' if value else '') + T(label), height=dp(44),
                    background_color=(0.8, 0.89, 0.98, 1) if value else BTN)
        b.bind(on_release=lambda *a: cb(not value))
        return b

    # build ---------------------------------------------------------------
    def rebuild(self, *a):
        self.grid.clear_widgets()
        self.nums = {}
        self.text_input = None
        ed = self.editor
        snapstep = lambda: ed.snap_step or 0.5  # noqa: E731
        if not ed.sel:
            return self.build_plate()
        if len(ed.sel) > 1:
            self.title('%d ×' % len(ed.sel))
            self.grid.add_widget(AutoLabel(ltext=tr('h_align'), color=MUTED, font_size=sp(13)))
            return
        e = self._el()
        if e is None:
            return
        t = e['type']
        name = {'text': 't_text', 'line': 't_line', 'rect': 't_rect', 'ellipse': 't_ellipse',
                'hole': 't_hole', 'table': 't_table', 'frame': 't_frame', 'symbol': 't_symbol',
                'image': 't_image'}[t]
        title = T(name)
        if t == 'symbol' and e.get('sym') in SYMBOLS:
            s = SYMBOLS[e['sym']]
            title = shape(s['fa']) if i18n.is_fa() else s['en']
        self.title(title)

        def setnum(key):
            def cb(v):
                el = self._el()
                if el is None:
                    return
                if key == 'w' and el.get('keep_aspect') and el['w'] > 0:
                    el['h'] = round(el['h'] * v / el['w'], 3)
                elif key == 'h' and el.get('keep_aspect') and el['h'] > 0:
                    el['w'] = round(el['w'] * v / el['h'], 3)
                if el['type'] == 'hole' and key in ('w', 'h'):
                    cx, cy = el['x'] + el['w'] / 2, el['y'] + el['h'] / 2
                    el['w'] = el['h'] = v
                    el['x'], el['y'] = round(cx - v / 2, 3), round(cy - v / 2, 3)
                else:
                    el[key] = v
                self.editor.commit()
                self.refresh_values()
            return cb

        if t == 'text':
            self.grid.add_widget(TLabel(text=T('p_text'), size_hint_y=None, height=dp(22),
                                        font_size=sp(13), color=MUTED))
            ti = TextField(text=e.get('text', ''), multiline=True, height=dp(84))
            self.preview = AutoLabel(ltext='', color=MUTED, font_size=sp(14))
            self.text_input = ti

            def upd_prev(*a):
                txt = ti.ltext
                self.preview.set_ltext((i18n.tr('p_preview') + '  ' + txt) if has_rtl(txt) else '')
            ti.bind(text=upd_prev)
            upd_prev()

            def commit_text(*a):
                el = self._el()
                if el is not None and el.get('text') != ti.ltext:
                    el['text'] = ti.ltext
                    self.editor.commit()
            ti.bind(focus=lambda w, f: (not f) and commit_text())
            ti.bind(text=lambda *a: self._live_text(ti))
            self.grid.add_widget(ti)
            self.grid.add_widget(self.preview)
            self.grid.add_widget(AutoLabel(ltext=tr('p_vars_hint'), color=MUTED, font_size=sp(12)))
            size = self.num('font_mm', 'p_size', e.get('font_mm', 4), setnum('font_mm'),
                            step=0.5, minv=0.5)
            bold = self.toggle('p_bold', e.get('bold'), lambda v: self._set('bold', v) or
                               self.rebuild())
            boldbox = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(74))
            boldbox.add_widget(Widget(size_hint_y=None, height=dp(24)))
            boldbox.add_widget(bold)
            self.grid.add_widget(self.pair(size, boldbox))
            self.grid.add_widget(self.align_row(e))
            self.grid.add_widget(ColorRow(T('p_color'), e.get('color', '#000000'),
                                          lambda c: self._set('color', c or '#000000') or
                                          self.rebuild(), allow_none=False))
            self.grid.add_widget(ColorRow(T('p_fill'), e.get('fill'),
                                          lambda c: self._set('fill', c) or self.rebuild()))

        # geometry
        if t == 'line':
            self.grid.add_widget(self.pair(
                self.num('x', 'p_x', e['x'], setnum('x'), step=snapstep),
                self.num('y', 'p_y', e['y'], setnum('y'), step=snapstep)))
            self.grid.add_widget(self.pair(
                self.num('w', 'p_w', e['w'], setnum('w'), step=snapstep),
                self.num('h', 'p_h', e['h'], setnum('h'), step=snapstep)))
        elif t == 'hole':
            self.grid.add_widget(self.pair(
                self.num('x', 'p_x', e['x'], setnum('x'), step=snapstep),
                self.num('y', 'p_y', e['y'], setnum('y'), step=snapstep)))
            self.grid.add_widget(self.pair(
                self.num('w', 'p_diam', e['w'], setnum('w'), step=0.5, minv=0.5),
                self.toggle('p_cross', e.get('cross', True),
                            lambda v: self._set('cross', v) or self.rebuild())))
        else:
            self.grid.add_widget(self.pair(
                self.num('x', 'p_x', e['x'], setnum('x'), step=snapstep),
                self.num('y', 'p_y', e['y'], setnum('y'), step=snapstep)))
            self.grid.add_widget(self.pair(
                self.num('w', 'p_w', e['w'], setnum('w'), step=snapstep, minv=0.2),
                self.num('h', 'p_h', e['h'], setnum('h'), step=snapstep, minv=0.2)))
            self.grid.add_widget(self.pair(
                self.num('rot', 'p_rot', e.get('rot', 0), setnum('rot'), step=15),
                self.num('sw', 'p_sw', e.get('sw', 0.3), setnum('sw'), step=0.1, minv=0)))

        if t in ('rect', 'frame'):
            self.grid.add_widget(self.pair(
                self.num('radius', 'p_radius', e.get('radius', 0), setnum('radius'), step=0.5,
                         minv=0),
                self.num('gap', 'p_gap', e.get('gap', 1), setnum('gap'), step=0.25, minv=0)
                if t == 'frame' else Widget()))
            if t == 'frame':
                self.grid.add_widget(self.toggle('p_double', e.get('double'),
                                                 lambda v: self._set('double', v) or
                                                 self.rebuild()))
        if t == 'line' or t == 'hole':
            self.grid.add_widget(self.pair(
                self.num('sw', 'p_sw', e.get('sw', 0.3), setnum('sw'), step=0.1, minv=0.05),
                Widget()))
        if t == 'table':
            def setrc(key):
                def cb(v):
                    el = self._el()
                    el[key] = int(v)
                    if key == 'cols':
                        el['col_ratios'] = None
                    ensure_cells(el)
                    self.editor.commit()
                return cb
            self.grid.add_widget(self.pair(
                self.num('rows', 'p_rows', e['rows'], setrc('rows'), step=1, minv=1, maxv=40,
                         integer=True),
                self.num('cols', 'p_cols', e['cols'], setrc('cols'), step=1, minv=1, maxv=20,
                         integer=True)))
            size = self.num('font_mm', 'p_size', e.get('font_mm', 2.8), setnum('font_mm'),
                            step=0.25, minv=0.5)
            hb = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(74))
            hb.add_widget(Widget(size_hint_y=None, height=dp(24)))
            hb.add_widget(self.toggle('p_header', e.get('header'),
                                      lambda v: self._set('header', v) or self.rebuild()))
            self.grid.add_widget(self.pair(size, hb))
            self.grid.add_widget(self.align_row(e))
            cb = TButton(text=T('p_cells'), primary=True)
            cb.bind(on_release=lambda *a: self.editor.edit_cells())
            self.grid.add_widget(cb)
        if t == 'symbol':
            sym = SYMBOLS.get(e.get('sym'), {})
            if sym.get('stext') is not None:
                self.grid.add_widget(TLabel(text=T('p_stext'), size_hint_y=None, height=dp(22),
                                            font_size=sp(13), color=MUTED))
                f = TextField(text=e.get('stext') or sym['stext'])
                f.bind(focus=lambda w, fo: (not fo) and self._set('stext', w.ltext))
                f.bind(on_text_validate=lambda w: self._set('stext', w.ltext))
                self.grid.add_widget(f)
        if t in ('rect', 'ellipse', 'frame', 'symbol', 'line', 'hole', 'table', 'image'):
            self.grid.add_widget(ColorRow(T('p_stroke'), e.get('stroke'),
                                          lambda c: self._set('stroke', c) or self.rebuild(),
                                          allow_none=t not in ('symbol', 'line', 'hole')))
        if t in ('rect', 'ellipse', 'frame', 'table', 'hole'):
            self.grid.add_widget(ColorRow(T('p_fill'), e.get('fill'),
                                          lambda c: self._set('fill', c) or self.rebuild()))
        self.grid.add_widget(Widget(size_hint_y=None, height=dp(20)))

    def _live_text(self, ti):
        el = self._el()
        if el is not None and el.get('type') == 'text':
            el['text'] = ti.ltext
            self.editor.canvas_w.redraw()

    def align_row(self, e):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4))
        items = [('left', 'a_left'), ('center', 'a_hcenter'), ('right', 'a_right')]
        for val, icon in items:
            b = IconButton(icon=icon, text='', icon_size=dp(24))
            b.active = e.get('align', 'center') == val
            b._paint()
            b.bind(on_release=lambda w, v=val: self._set('align', v) or self.rebuild())
            row.add_widget(b)
        return row

    def build_plate(self):
        ed = self.editor
        doc = ed.doc
        self.title(T('p_plate') + '  %s × %s mm' % (fmt(doc.w), fmt(doc.h)))
        self.grid.add_widget(AutoLabel(ltext=tr('p_nothing'), color=MUTED, font_size=sp(13)))
        self._pw = NumField(T('p_w'), doc.w, lambda v: None, step=1, minv=5, maxv=1000)
        self._ph = NumField(T('p_h'), doc.h, lambda v: None, step=1, minv=5, maxv=1000)
        self.grid.add_widget(self.pair(self._pw, self._ph))
        self._scale = False
        sc = TButton(text=T('p_scale_content'))

        def tog(*a):
            self._scale = not self._scale
            sc.text = ('• ' if self._scale else '') + T('p_scale_content')
        sc.bind(on_release=tog)
        ap = TButton(text=T('p_apply'), primary=True)
        ap.bind(on_release=lambda *a: ed.resize_plate(self._pw.value(), self._ph.value(),
                                                     self._scale))
        self.grid.add_widget(hrow(sc, ap, height=dp(48)))

        def setr(v):
            doc.radius = v
            ed.commit()
        self.grid.add_widget(self.pair(NumField(T('p_radius'), doc.radius, setr, step=0.5, minv=0),
                                       Widget()))

        def setbg(c):
            doc.bg = c or '#ffffff'
            ed.commit()
            self.rebuild()
        self.grid.add_widget(ColorRow(T('p_bg'), doc.bg, setbg, allow_none=False))
        for key, lab in (('serial', 'p_serial'), ('date', 'p_date')):
            self.grid.add_widget(TLabel(text=shape(i18n.tr(lab)), size_hint_y=None,
                                        height=dp(22), font_size=sp(13), color=MUTED))
            f = TextField(text=str(doc.vars.get(key, '')))

            def setv(w, k=key):
                if doc.vars.get(k) != w.ltext:
                    doc.vars[k] = w.ltext
                    ed.commit()
            f.bind(focus=lambda w, fo, s=setv: (not fo) and s(w))
            f.bind(on_text_validate=setv)
            self.grid.add_widget(f)
        self.grid.add_widget(Widget(size_hint_y=None, height=dp(20)))

    def refresh_values(self):
        e = self._el()
        if e is None:
            if not self.editor.sel and hasattr(self, '_pw'):
                pass
            return
        for k, nf in self.nums.items():
            if k in e:
                nf.set_value(e[k])
