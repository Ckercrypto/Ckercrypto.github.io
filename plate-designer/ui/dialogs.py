"""Popups: symbol library, export, align, settings/calibration, tour, cells,
save-as, file browser."""
import os
import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import export
import i18n
import platform_io
import raster
from i18n import T, tr
from symbols import by_category
from textshape import shape
from ui.common import (BTN, MUTED, PRIMARY, TEXT, AutoLabel, BgMixin, Field, IconButton,
                       TButton, TextField, TLabel, disp, hrow, pil_to_texture, toast)
from ui.props import NumField, fmt

_SYM_TEX = {}


def make_popup(title, content, size_hint=(0.92, 0.9), auto_dismiss=True):
    return Popup(title=title, content=content, size_hint=size_hint,
                 auto_dismiss=auto_dismiss, background='', background_color=(1, 1, 1, 1),
                 title_color=PRIMARY, title_size=sp(19), separator_color=PRIMARY,
                 title_align='right' if i18n.is_fa() else 'left')


def sym_texture(sid):
    t = _SYM_TEX.get(sid)
    if t is None:
        t = pil_to_texture(raster.symbol_icon(sid, 120, color='#1b1b1b',
                                              bg=(255, 255, 255, 255)))
        _SYM_TEX[sid] = t
    return t


class SymbolCard(ButtonBehavior, BoxLayout, BgMixin):
    def __init__(self, sym, **kw):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(124),
                         padding=dp(4), spacing=dp(2), **kw)
        self.init_bg((1, 1, 1, 1), dp(10), border=(0.82, 0.85, 0.89, 1))
        self.sym = sym
        img = Image(texture=sym_texture(sym['id']), size_hint_y=None, height=dp(70),
                    fit_mode='contain')
        self.add_widget(img)
        name = shape(sym['fa']) if i18n.is_fa() else sym['en']
        lbl = Label(text=name, color=TEXT, font_size=sp(11.5), halign='center',
                    valign='top', max_lines=2, shorten=False)
        lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], s[1])))
        self.add_widget(lbl)
        self.bind(state=lambda *a: self.set_bg((0.85, 0.92, 1, 1) if self.state == 'down'
                                               else (1, 1, 1, 1)))


class SymbolLibrary:
    def __init__(self, editor):
        self.editor = editor
        root = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(4))
        self.size_f = NumField(T('symbol_size'), editor.last_symbol_size, lambda v: None,
                               step=1, minv=2, maxv=300, size_hint_x=None, width=dp(190))
        hintl = TLabel(text=T('tap_to_add'), color=MUTED, font_size=sp(14))
        root.add_widget(hrow(self.size_f, hintl, height=dp(74)))
        chips = BoxLayout(size_hint=(None, None), height=dp(42), spacing=dp(6))
        chips.bind(minimum_width=chips.setter('width'))
        csv = ScrollView(size_hint_y=None, height=dp(46), do_scroll_y=False, bar_width=dp(3))
        csv.add_widget(chips)
        root.add_widget(csv)
        self.sv = ScrollView(do_scroll_x=False, bar_width=dp(6))
        body = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=(0, 0, dp(6), dp(10)))
        body.bind(minimum_height=body.setter('height'))
        self.headers = {}
        self.grids = []
        for cid, en, fa, syms in by_category():
            hdr = TLabel(text=shape(fa) if i18n.is_fa() else en, size_hint_y=None,
                         height=dp(34), bold=True, color=PRIMARY, font_size=sp(16))
            self.headers[cid] = hdr
            body.add_widget(hdr)
            g = GridLayout(cols=4, size_hint_y=None, spacing=dp(6))
            g.bind(minimum_height=g.setter('height'))
            for s in syms:
                card = SymbolCard(s)
                card.bind(on_release=lambda w: self.pick(w.sym))
                g.add_widget(card)
            self.grids.append(g)
            body.add_widget(g)
            chip = TButton(text=shape(fa) if i18n.is_fa() else en, size_hint_x=None,
                           height=dp(40), font_size=sp(13))
            chip.texture_update()
            chip.width = chip.texture_size[0] + dp(24)
            chip.bind(on_release=lambda w, c=cid: self.sv.scroll_to(self.headers[c], padding=dp(4)))
            chips.add_widget(chip)
        self.sv.add_widget(body)
        root.add_widget(self.sv)
        close = TButton(text=T('close'))
        root.add_widget(close)
        self.popup = make_popup(T('symbols_title'), root, (0.96, 0.94))
        close.bind(on_release=lambda *a: self.popup.dismiss())
        self.sv.bind(width=self._cols)

    def _cols(self, *a):
        n = max(3, int(self.sv.width / dp(112)))
        for g in self.grids:
            g.cols = n

    def open(self):
        self.popup.open()

    def pick(self, sym):
        size = self.size_f.value() or 10
        self.editor.last_symbol_size = size
        self.editor.add_symbol(sym['id'], size)
        self.popup.dismiss()


def align_dialog(editor):
    g = GridLayout(cols=2, spacing=dp(8), padding=dp(4), size_hint_y=None)
    g.bind(minimum_height=g.setter('height'))
    pop = None
    for mode in ('left', 'right', 'hcenter', 'top', 'vcenter', 'bottom', 'center_plate'):
        b = IconButton(icon='a_' + mode, text=T('a_' + mode), horizontal=True,
                       size_hint_y=None, height=dp(56), font_size=sp(15))
        b.bind(on_release=lambda w, m=mode: (editor.align(m), pop.dismiss()))
        g.add_widget(b)
    sv = ScrollView()
    sv.add_widget(g)
    pop = make_popup(T('t_align'), sv, (0.9, 0.6))
    pop.open()
    return pop


def cells_dialog(editor, el):
    rows, cols = int(el['rows']), int(el['cols'])
    root = BoxLayout(orientation='vertical', spacing=dp(8))
    g = GridLayout(cols=cols, spacing=dp(4), size_hint=(None, None))
    g.bind(minimum_height=g.setter('height'))
    cw = dp(140)
    g.width = cw * cols + dp(4) * cols
    fields = []
    for r in range(rows):
        row = []
        for c in range(cols):
            f = TextField(text=el['cells'][r][c], size_hint_x=None, width=cw)
            g.add_widget(f)
            row.append(f)
        fields.append(row)
    sv = ScrollView()
    sv.add_widget(g)
    root.add_widget(sv)
    root.add_widget(AutoLabel(ltext=tr('p_vars_hint'), color=MUTED, font_size=sp(13)))
    ok = TButton(text=T('ok'), primary=True)
    root.add_widget(ok)
    pop = make_popup(T('cells_title'), root, (0.96, 0.85))

    def save(*a):
        el['cells'] = [[f.ltext for f in row] for row in fields]
        editor.commit()
        pop.dismiss()
    ok.bind(on_release=save)
    pop.open()
    return pop


def save_dialog(editor):
    root = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(4))
    app = App.get_running_app()
    name = editor.file_path and os.path.splitext(os.path.basename(editor.file_path))[0] or \
        export.safe_name(editor.doc.name, 'plate')
    row, f = labeled_field_local('file_name', name)
    root.add_widget(row)
    root.add_widget(AutoLabel(ltext=(app.dirs['projects']), color=MUTED, font_size=sp(12)))
    root.add_widget(Widget())
    ok = TButton(text=T('t_save'), primary=True)
    root.add_widget(ok)
    pop = make_popup(T('save_as'), root, (0.9, 0.5))

    def save(*a):
        fn = export.safe_name(f.ltext, 'plate') + '.tplate'
        path = os.path.join(app.dirs['projects'], fn)
        editor.save_to(path)
        pop.dismiss()
    ok.bind(on_release=save)
    f.bind(on_text_validate=save)
    pop.open()
    return pop


def labeled_field_local(key, value):
    lab = TLabel(text=T(key), size_hint_x=None, width=dp(120))
    f = TextField(text=value)
    return hrow(lab, f, height=dp(46)), f


class ExportDialog:
    FORMATS = [('pdf', 'e_pdf', 'pdf'), ('tiled', 'e_tiled', 'tile'), ('png', 'e_png', 'png'),
               ('svg', 'e_svg', 'svg'), ('calib', 'e_calib', 'calib')]

    def __init__(self, editor):
        self.editor = editor
        self.app = App.get_running_app()
        st = self.app.settings
        self.fmt = st.get('last_format', 'pdf')
        self.dpi = int(st.get('dpi', 600))
        self.vary = False
        self.inc_after = bool(st.get('inc_after', False))
        root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(4))
        sv = ScrollView(do_scroll_x=False)
        self.body = GridLayout(cols=1, size_hint_y=None, spacing=dp(8),
                               padding=(dp(4), 0, dp(14), 0))
        self.body.bind(minimum_height=self.body.setter('height'))
        sv.add_widget(self.body)
        root.add_widget(sv)
        self.status = AutoLabel(text='', color=MUTED, font_size=sp(14))
        root.add_widget(self.status)
        self.go = TButton(text=T('e_go'), primary=True, height=dp(54), font_size=sp(17))
        self.go.bind(on_release=self.run)
        root.add_widget(self.go)
        self.popup = make_popup(T('export_title'), root, (0.94, 0.94))
        self.build()

    def build(self):
        b = self.body
        b.clear_widgets()
        g = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        g.bind(minimum_height=g.setter('height'))
        for key, lab, icon in self.FORMATS:
            btn = IconButton(icon=icon, text=T(lab), horizontal=True, size_hint_y=None,
                             height=dp(54), font_size=sp(15))
            btn.active = (key == self.fmt)
            btn._paint()
            btn.bind(on_release=lambda w, k=key: self.set_fmt(k))
            g.add_widget(btn)
        b.add_widget(g)
        if self.fmt in ('pdf', 'tiled', 'png'):
            b.add_widget(TLabel(text=T('e_dpi'), size_hint_y=None, height=dp(26),
                                color=MUTED, font_size=sp(13)))
            row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
            for d in (300, 600, 1200):
                t = TButton(text=str(d), background_color=(0.8, 0.89, 0.98, 1)
                            if d == self.dpi else BTN)
                t.bind(on_release=lambda w, dd=d: self.set_dpi(dd))
                row.add_widget(t)
            b.add_widget(row)
        if self.fmt == 'tiled':
            st = self.app.settings
            doc = self.editor.doc
            self.copies = NumField(T('e_copies'), st.get('copies', 0) or 0, lambda v: self.info(),
                                   step=1, minv=0, maxv=500, integer=True)
            self.spacing = NumField(T('e_spacing'), st.get('spacing', 3), lambda v: self.info(),
                                    step=0.5, minv=0, maxv=50)
            gg = GridLayout(cols=2, size_hint_y=None, height=dp(74), spacing=dp(8))
            for w in ((self.spacing, self.copies) if i18n.is_fa() else (self.copies, self.spacing)):
                gg.add_widget(w)
            b.add_widget(gg)
            vb = TButton(text=('• ' if self.vary else '') + T('e_vary'))
            vb.bind(on_release=lambda *a: self.toggle_vary())
            b.add_widget(vb)
            self.fit_lbl = AutoLabel(text='', color=TEXT, font_size=sp(14))
            b.add_widget(self.fit_lbl)
            self.info()
        if self.fmt in ('pdf', 'tiled', 'png'):
            ib = TButton(text=('• ' if self.inc_after else '') + T('e_inc_after'))
            ib.bind(on_release=lambda *a: self.toggle_inc())
            b.add_widget(ib)
        if self.fmt != 'calib':
            cx, cy = self.app.corr()
            b.add_widget(AutoLabel(ltext=tr('e_corr', x=fmt(cx * 100), y=fmt(cy * 100)),
                                   color=MUTED, font_size=sp(13)))
        else:
            b.add_widget(AutoLabel(ltext=tr('calib_help'), color=TEXT, font_size=sp(14)))

    def info(self):
        if self.fmt != 'tiled':
            return
        doc = self.editor.doc
        cx, cy = self.app.corr()
        sp_ = self.spacing.value() or 0
        c0, r0 = export.tile_layout(doc.w * cx, doc.h * cy, sp_)
        c1, r1 = export.tile_layout(doc.h * cy, doc.w * cx, sp_)
        n = max(c0 * r0, c1 * r1)
        self.fit_lbl.set_ltext(tr('e_fit', n=n))

    def set_fmt(self, k):
        self.fmt = k
        self.build()

    def set_dpi(self, d):
        self.dpi = d
        self.build()

    def toggle_vary(self):
        self.vary = not self.vary
        self.build()

    def toggle_inc(self):
        self.inc_after = not self.inc_after
        self.build()

    def open(self):
        self.popup.open()

    def run(self, *a):
        app = self.app
        doc = self.editor.doc.copy()
        fmt_ = self.fmt
        st = app.settings
        st['last_format'] = fmt_
        st['dpi'] = self.dpi
        st['inc_after'] = self.inc_after
        opts = {}
        if fmt_ == 'tiled':
            opts['copies'] = int(self.copies.value() or 0)
            opts['spacing'] = float(self.spacing.value() or 0)
            st['copies'] = opts['copies']
            st['spacing'] = opts['spacing']
        app.save_settings()
        base = export.safe_name(doc.name or 'plate')
        if '{serial}' in doc.to_json():
            base += '_' + export.safe_name(str(doc.vars.get('serial', '')), '')
        ext = {'pdf': '.pdf', 'tiled': '_A4.pdf', 'png': '_%ddpi.png' % self.dpi,
               'svg': '.svg', 'calib': '.pdf'}[fmt_]
        if fmt_ == 'calib':
            base = 'printer_calibration'
        path = os.path.join(app.dirs['exports'], base + ext)
        corr = app.corr()
        self.go.disabled = True
        self.status.set_ltext('… ' + base + ext)

        def work():
            try:
                res = None
                if fmt_ == 'pdf':
                    export.export_pdf(doc, path, self.dpi, corr)
                elif fmt_ == 'png':
                    export.export_png(doc, path, self.dpi, corr)
                elif fmt_ == 'svg':
                    export.export_svg(doc, path, corr)
                elif fmt_ == 'calib':
                    export.export_calibration_pdf(path)
                else:
                    res = export.export_tiled_pdf(doc, path, opts['copies'] or None,
                                                  opts['spacing'], dpi=self.dpi, corr=corr,
                                                  vary_serial=self.vary)
                Clock.schedule_once(lambda dt: self.done(path, res, None), 0)
            except Exception as e:
                traceback.print_exc()
                err = str(e)
                Clock.schedule_once(lambda dt: self.done(path, None, err), 0)
        threading.Thread(target=work, daemon=True).start()

    def done(self, path, res, err):
        self.go.disabled = False
        if err:
            self.status.set_ltext(tr('e_fail') + ' ' + err)
            return
        ed = self.editor
        if self.fmt in ('pdf', 'png', 'tiled'):
            if res and res.get('next_serial'):
                ed.doc.vars['serial'] = res['next_serial']
                ed.commit()
            elif self.inc_after:
                ed.next_serial(silent=True)
        uri, where = platform_io.publish(path)
        self.popup.dismiss()
        result_dialog(path, uri, where)


def result_dialog(path, uri, where):
    root = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(6))
    root.add_widget(AutoLabel(ltext=tr('e_saved'), color=PRIMARY, bold=True, font_size=sp(17)))
    root.add_widget(AutoLabel(ltext=(where), color=TEXT, font_size=sp(14)))
    root.add_widget(Widget())
    btns = []
    if platform_io.IS_ANDROID:
        sh = TButton(text=T('e_share'), primary=True)
        sh.bind(on_release=lambda *a: platform_io.share(uri or path))
        btns.append(sh)
    else:
        of = TButton(text=T('e_open_folder'), primary=True)
        of.bind(on_release=lambda *a: platform_io.open_folder(os.path.dirname(path)))
        btns.append(of)
    cl = TButton(text=T('close'))
    btns.append(cl)
    root.add_widget(hrow(*btns, height=dp(50)))
    pop = make_popup(T('export_title'), root, (0.9, 0.45))
    cl.bind(on_release=lambda *a: pop.dismiss())
    pop.open()
    return pop


def settings_dialog(app, on_lang=None):
    st = app.settings
    root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(4))
    sv = ScrollView(do_scroll_x=False)
    body = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=(dp(4), 0, dp(14), 0))
    body.bind(minimum_height=body.setter('height'))
    sv.add_widget(body)
    root.add_widget(sv)
    pop = make_popup(T('settings'), root, (0.94, 0.94))
    lb = TButton(text=shape(tr('language') + ': ' + tr('lang_toggle')))

    def switch_lang(*a):
        pop.dismiss()
        app.toggle_language()
    lb.bind(on_release=switch_lang)
    body.add_widget(lb)
    body.add_widget(TLabel(text=T('snap_default'), size_hint_y=None, height=dp(26),
                           color=MUTED, font_size=sp(13)))
    row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
    btns = []
    for v in (0, 0.5, 1, 5):
        b = TButton(text=T('snap_off') if v == 0 else fmt(v))
        b.background_color = (0.8, 0.89, 0.98, 1) if float(st.get('snap', 1)) == v else BTN
        btns.append((b, v))
        row.add_widget(b)

    def set_snap(v):
        st['snap'] = v
        app.save_settings()
        for b, vv in btns:
            b.background_color = (0.8, 0.89, 0.98, 1) if vv == v else BTN
    for b, v in btns:
        b.bind(on_release=lambda w, vv=v: set_snap(vv))
    body.add_widget(row)
    body.add_widget(TLabel(text=T('calib_title'), size_hint_y=None, height=dp(34), bold=True,
                           color=PRIMARY, font_size=sp(17)))
    body.add_widget(AutoLabel(ltext=tr('calib_help'), color=TEXT, font_size=sp(14)))
    cal = TButton(text=T('e_calib'), primary=True)
    body.add_widget(cal)
    mx = NumField(T('calib_meas_x'), 100, lambda v: None, step=0.5, minv=50, maxv=150)
    my = NumField(T('calib_meas_y'), 100, lambda v: None, step=0.5, minv=50, maxv=150)
    g = GridLayout(cols=2, size_hint_y=None, height=dp(74), spacing=dp(8))
    for w in ((my, mx) if i18n.is_fa() else (mx, my)):
        g.add_widget(w)
    body.add_widget(g)
    comp = TButton(text=T('calib_compute'))
    body.add_widget(comp)

    def set_cx(v):
        st['corr_x'] = v
        app.save_settings()

    def set_cy(v):
        st['corr_y'] = v
        app.save_settings()
    cx = NumField(T('calib_corr_x'), st.get('corr_x', 100), set_cx, step=0.1, minv=50, maxv=150)
    cy = NumField(T('calib_corr_y'), st.get('corr_y', 100), set_cy, step=0.1, minv=50, maxv=150)
    g2 = GridLayout(cols=2, size_hint_y=None, height=dp(74), spacing=dp(8))
    for w in ((cy, cx) if i18n.is_fa() else (cx, cy)):
        g2.add_widget(w)
    body.add_widget(g2)
    rs = TButton(text=T('calib_reset'))
    body.add_widget(rs)

    def compute(*a):
        fx = round(export.factor_from_measure(mx.value() or 100) * 100, 2)
        fy = round(export.factor_from_measure(my.value() or 100) * 100, 2)
        cx.inp.text, cy.inp.text = fmt(fx), fmt(fy)
        cx.commit()
        cy.commit()

    def reset(*a):
        cx.inp.text = cy.inp.text = '100'
        cx.commit()
        cy.commit()
    comp.bind(on_release=compute)
    rs.bind(on_release=reset)

    def calib(*a):
        path = os.path.join(app.dirs['exports'], 'printer_calibration.pdf')
        export.export_calibration_pdf(path)
        uri, where = platform_io.publish(path)
        result_dialog(path, uri, where)
    cal.bind(on_release=calib)
    close = TButton(text=T('close'))
    close.bind(on_release=lambda *a: pop.dismiss())
    root.add_widget(close)
    pop.open()
    return pop


def tour_dialog(app, on_done=None):
    tips = ['tour1', 'tour2', 'tour3', 'tour4']
    icons = ['symbol', 'select', 'fit', 'export']
    state = {'i': 0}
    root = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(8))
    img = Image(source=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets',
                                    'icons', icons[0] + '.png'),
                color=PRIMARY, size_hint_y=None, height=dp(64), fit_mode='contain')
    lbl = AutoLabel(ltext=tr(tips[0]), font_size=sp(17), halign='center')
    step = TLabel(text='1 / 4', size_hint_y=None, height=dp(24), halign='center', color=MUTED)
    nxt = TButton(text=T('next'), primary=True)
    skip = TButton(text=T('close'))
    root.add_widget(img)
    root.add_widget(lbl)
    root.add_widget(Widget())
    root.add_widget(step)
    root.add_widget(hrow(skip, nxt, height=dp(50)))
    pop = make_popup(T('tour_title'), root, (0.9, 0.55), auto_dismiss=False)

    def finish(*a):
        app.settings['tour_done'] = True
        app.save_settings()
        pop.dismiss()
        if on_done:
            on_done()

    def go(*a):
        state['i'] += 1
        if state['i'] >= len(tips):
            return finish()
        i = state['i']
        lbl.set_ltext(tr(tips[i]))
        img.source = img.source.rsplit('/', 1)[0] + '/' + icons[i] + '.png'
        step.text = '%d / 4' % (i + 1)
        if i == len(tips) - 1:
            nxt.text = T('done')
    nxt.bind(on_release=go)
    skip.bind(on_release=finish)
    pop.open()
    return pop


def file_browser(title, filters, start_dir, on_pick):
    """Desktop file chooser (Android uses the system picker instead)."""
    from kivy.uix.filechooser import FileChooserListView
    root = BoxLayout(orientation='vertical', spacing=dp(6))
    fc = FileChooserListView(path=start_dir if os.path.isdir(start_dir) else
                             os.path.expanduser('~'), filters=filters)
    root.add_widget(fc)
    ok = TButton(text=T('open'), primary=True)
    root.add_widget(ok)
    pop = make_popup(title, root, (0.95, 0.95))

    def pick(*a):
        if fc.selection:
            pop.dismiss()
            on_pick(fc.selection[0])
    ok.bind(on_release=pick)
    fc.bind(on_submit=lambda *a: pick())
    pop.open()
    return pop
