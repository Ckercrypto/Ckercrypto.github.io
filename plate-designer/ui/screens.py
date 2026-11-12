"""Screens: start, template wizard, open, editor."""
import base64
import io
import os
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import i18n
import platform_io
from i18n import T, tr
from model import SIZE_PRESETS, Document, History, make_element
from symbols import SYMBOLS
from templates import TEMPLATES, add_corner_holes, add_frame, defaults, get_template
from textshape import shape
from ui.canvas import PlateCanvas
from ui.common import (BG, MUTED, PRIMARY, TEXT, AutoLabel, Field, IconButton, Panel,
                       TButton, TextField, TLabel, disp, hrow, toast)
from ui import dialogs
from ui.props import NumField, PropertyPanel, fmt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def screen_bg(widget):
    from kivy.graphics import Color, Rectangle
    with widget.canvas.before:
        Color(*BG)
        r = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, p: setattr(r, 'pos', p), size=lambda w, s: setattr(r, 'size', s))


def top_bar(title, on_back=None, extra=()):
    bar = Panel(color=PRIMARY, radius=0, size_hint_y=None, height=dp(58),
                padding=(dp(6), dp(5)), spacing=dp(6))
    items = []
    if on_back:
        b = IconButton(icon='home', text='', size_hint_x=None, width=dp(52), primary=True,
                       icon_size=dp(28))
        b.bind(on_release=lambda *a: on_back())
        items.append(b)
    lbl = TLabel(text=title, color=(1, 1, 1, 1), bold=True, font_size=sp(18))
    items.append(lbl)
    items.extend(extra)
    if i18n.is_fa():
        items.reverse()
    for w in items:
        bar.add_widget(w)
    return bar


# ---------------------------------------------------------------------------
class StartScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        screen_bg(self)
        app = App.get_running_app()
        root = BoxLayout(orientation='vertical')
        sv = ScrollView(do_scroll_x=False)
        col = GridLayout(cols=1, size_hint_y=None, spacing=dp(12),
                         padding=(dp(18), dp(18), dp(18), dp(24)))
        col.bind(minimum_height=col.setter('height'))
        head = BoxLayout(size_hint_y=None, height=dp(96), spacing=dp(14))
        logo = Image(source=os.path.join(ROOT, 'assets', 'icon.png'), size_hint_x=None,
                     width=dp(84), fit_mode='contain')
        tbox = BoxLayout(orientation='vertical')
        tbox.add_widget(TLabel(text=T('app_title'), bold=True, font_size=sp(24),
                               color=(0.05, 0.17, 0.34, 1)))
        tbox.add_widget(TLabel(text=T('subtitle'), color=MUTED, font_size=sp(14)))
        ws = [logo, tbox]
        if i18n.is_fa():
            ws.reverse()
        for w in ws:
            head.add_widget(w)
        col.add_widget(head)
        items = [('new', 'new_blank', self.new_blank, True),
                 ('template', 'from_template', lambda: app.go('templates'), False),
                 ('open', 'open_saved', lambda: app.go('open'), False)]
        if os.path.exists(app.autosave_path):
            items.insert(0, ('save', 'continue_last', app.continue_last, False))
        for icon, key, cb, prim in items:
            b = IconButton(icon=icon, text=T(key), horizontal=True, primary=prim,
                           size_hint_y=None, height=dp(66), font_size=sp(18),
                           icon_size=dp(34), padding=(dp(16), dp(8)))
            b.bind(on_release=lambda w, c=cb: c())
            col.add_widget(b)
        # size presets right on the start screen (fewest taps)
        col.add_widget(TLabel(text=T('choose_size'), size_hint_y=None, height=dp(30),
                              color=MUTED, font_size=sp(14)))
        g = GridLayout(cols=3, size_hint_y=None, spacing=dp(8))
        g.bind(minimum_height=g.setter('height'))
        for name, w, h in SIZE_PRESETS:
            t = '%s\n%s×%s mm' % (name, w, h) if name == 'A6' else '%s mm' % name.replace('x', '×')
            b = TButton(text=t, height=dp(56), font_size=sp(15), halign='center')
            b.bind(on_release=lambda x, ww=w, hh=h: app.new_doc(Document(ww, hh)))
            g.add_widget(b)
        cb = TButton(text=T('custom'), height=dp(56), font_size=sp(15))
        cb.bind(on_release=lambda *a: self.custom_size())
        g.add_widget(cb)
        col.add_widget(g)
        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        sb = IconButton(icon='settings', text=T('settings'), horizontal=True,
                        font_size=sp(15))
        sb.bind(on_release=lambda *a: dialogs.settings_dialog(app))
        lb = IconButton(icon='lang', text=T('lang_toggle'), horizontal=True, font_size=sp(15))
        lb.bind(on_release=lambda *a: app.toggle_language())
        row.add_widget(sb)
        row.add_widget(lb)
        col.add_widget(row)
        sv.add_widget(col)
        root.add_widget(sv)
        self.add_widget(root)

    def new_blank(self):
        App.get_running_app().new_doc(Document(100, 60))

    def custom_size(self):
        app = App.get_running_app()
        root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(4))
        wf = NumField(T('width_mm'), 100, lambda v: None, step=1, minv=5, maxv=1000)
        hf = NumField(T('height_mm'), 60, lambda v: None, step=1, minv=5, maxv=1000)
        g = GridLayout(cols=2, size_hint_y=None, height=dp(74), spacing=dp(10))
        g.add_widget(wf)
        g.add_widget(hf)
        root.add_widget(g)
        root.add_widget(Widget())
        ok = TButton(text=T('create'), primary=True)
        root.add_widget(ok)
        pop = dialogs.make_popup(T('custom'), root, (0.9, 0.42))
        ok.bind(on_release=lambda *a: (pop.dismiss(),
                                       app.new_doc(Document(wf.value() or 100, hf.value() or 60))))
        pop.open()


# ---------------------------------------------------------------------------
class TemplateScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        screen_bg(self)
        self.tid = None
        self.root_box = BoxLayout(orientation='vertical')
        self.add_widget(self.root_box)
        self.show_list()

    def show_list(self):
        app = App.get_running_app()
        self.tid = None
        self.root_box.clear_widgets()
        self.root_box.add_widget(top_bar(T('templates'), on_back=lambda: app.go('start')))
        sv = ScrollView(do_scroll_x=False)
        col = GridLayout(cols=1, size_hint_y=None, spacing=dp(10), padding=dp(14))
        col.bind(minimum_height=col.setter('height'))
        col.add_widget(AutoLabel(ltext=tr('tpl_hint'), color=MUTED, font_size=sp(14)))
        from ui.dialogs import sym_texture
        for t in TEMPLATES:
            row = Panel(color=(1, 1, 1, 1), size_hint_y=None, height=dp(78), padding=dp(8),
                        spacing=dp(12), border=(0.82, 0.85, 0.89, 1))
            img = Image(texture=sym_texture(t['icon']), size_hint_x=None, width=dp(60),
                        fit_mode='contain')
            lbl = TLabel(text=T(t['name']) + '\n' + '%s × %s mm' % t['size'],
                         font_size=sp(16))
            go = TButton(text=T('next'), primary=True, size_hint_x=None, width=dp(96),
                         height=dp(52), pos_hint={'center_y': .5})
            go.bind(on_release=lambda w, tid=t['id']: self.show_form(tid))
            ws = [img, lbl, go]
            if i18n.is_fa():
                ws.reverse()
            for w in ws:
                row.add_widget(w)
            col.add_widget(row)
        sv.add_widget(col)
        self.root_box.add_widget(sv)

    def show_form(self, tid):
        app = App.get_running_app()
        self.tid = tid
        tpl = get_template(tid)
        self.root_box.clear_widgets()
        self.root_box.add_widget(top_bar(T(tpl['name']), on_back=self.show_list))
        sv = ScrollView(do_scroll_x=False)
        col = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=dp(14))
        col.bind(minimum_height=col.setter('height'))
        col.add_widget(AutoLabel(ltext=tr('tpl_hint'), color=MUTED, font_size=sp(14)))
        self.fields = {}
        vals = defaults(tid)
        choices = {'kind': [('Transformer', 'ترانسفورماتور'), ('Stabilizer', 'استابلایزر')],
                   'phases': [('1', '1'), ('3', '3')],
                   'conn': [('Y', 'Y'), ('D', 'D'), ('Z', 'Z'), ('-', '-')]}
        for key, default in tpl['fields']:
            lab = TLabel(text=T('f_' + key), size_hint_x=None, width=dp(160), font_size=sp(14))
            if key in choices:
                box = BoxLayout(spacing=dp(6))
                self.fields[key] = {'value': vals[key], 'buttons': []}
                for val, fa in choices[key]:
                    b = TButton(text=shape(fa) if i18n.is_fa() else val, height=dp(44))
                    self.fields[key]['buttons'].append((b, val))
                    b.bind(on_release=lambda w, k=key, v=val: self._choose(k, v))
                    box.add_widget(b)
                self._choose(key, vals[key])
                col.add_widget(hrow(lab, box, height=dp(48)))
            else:
                f = TextField(text=str(default))
                self.fields[key] = f
                col.add_widget(hrow(lab, f, height=dp(48)))
        if not tpl['fields']:
            col.add_widget(AutoLabel(ltext=tr(tpl['name']), font_size=sp(16)))
        sv.add_widget(col)
        self.root_box.add_widget(sv)
        go = TButton(text=T('generate'), primary=True, height=dp(58), font_size=sp(18))
        go.bind(on_release=lambda *a: self.generate())
        bottom = BoxLayout(size_hint_y=None, height=dp(70), padding=dp(6))
        bottom.add_widget(go)
        self.root_box.add_widget(bottom)

    def _choose(self, key, val):
        fd = self.fields[key]
        fd['value'] = val
        for b, v in fd['buttons']:
            b._base = (0.8, 0.89, 0.98, 1) if v == val else (0.90, 0.92, 0.95, 1)
            b.background_color = b._base

    def values(self):
        out = {}
        for k, f in self.fields.items():
            out[k] = f['value'] if isinstance(f, dict) else f.ltext
        return out

    def generate(self):
        tpl = get_template(self.tid)
        doc = tpl['build'](self.values())
        App.get_running_app().new_doc(doc)


# ---------------------------------------------------------------------------
class OpenScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        screen_bg(self)
        self.box = BoxLayout(orientation='vertical')
        self.add_widget(self.box)

    def on_pre_enter(self, *a):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        br = IconButton(icon='open', text=T('browse'), horizontal=True, primary=True,
                        size_hint_x=None, width=dp(150), font_size=sp(14))
        br.bind(on_release=lambda *a: self.browse())
        self.box.add_widget(top_bar(T('open_saved'), on_back=lambda: app.go('start'),
                                    extra=[br]))
        sv = ScrollView(do_scroll_x=False)
        col = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=dp(14))
        col.bind(minimum_height=col.setter('height'))
        files = []
        seen = set()
        for p in app.settings.get('recent', []):
            if os.path.exists(p) and p not in seen:
                files.append(p)
                seen.add(p)
        pd = app.dirs['projects']
        others = sorted((os.path.join(pd, f) for f in os.listdir(pd) if f.endswith('.tplate')),
                        key=lambda p: -os.path.getmtime(p))
        for p in others:
            if p not in seen:
                files.append(p)
                seen.add(p)
        if not files:
            col.add_widget(AutoLabel(ltext=tr('no_files'), color=MUTED))
        else:
            col.add_widget(TLabel(text=T('recent'), size_hint_y=None, height=dp(28),
                                  color=MUTED, font_size=sp(14)))
        for p in files:
            name = os.path.splitext(os.path.basename(p))[0]
            when = time.strftime('%Y/%m/%d %H:%M', time.localtime(os.path.getmtime(p)))
            b = IconButton(icon='plate', text='%s   ·   %s' % (disp(name), when), horizontal=True,
                           size_hint_y=None, height=dp(60), font_size=sp(15))
            b.bind(on_release=lambda w, pp=p: app.open_file(pp))
            col.add_widget(b)
        sv.add_widget(col)
        self.box.add_widget(sv)

    def browse(self):
        app = App.get_running_app()
        if platform_io.IS_ANDROID:
            platform_io.android_pick_file('*/*', app.open_file)
        else:
            dialogs.file_browser(T('open'), ['*.tplate', '*.json'], app.dirs['projects'],
                                 app.open_file)


# ---------------------------------------------------------------------------
INSERT_TOOLS = [('text', 't_text', 'h_text'), ('line', 't_line', 'h_line'),
                ('rect', 't_rect', 'h_rect'), ('rrect', 't_rrect', 'h_rrect'),
                ('ellipse', 't_ellipse', 'h_ellipse'), ('hole', 't_hole', 'h_hole'),
                ('holes4', 't_holes4', 'h_holes4'), ('table', 't_table', 'h_table'),
                ('frame', 't_frame', 'h_frame'), ('symbol', 't_symbol', 'h_symbol'),
                ('image', 't_image', 'h_image')]
EDIT_TOOLS = [('dup', 't_dup', 'h_dup'), ('delete', 't_delete', 'h_delete'),
              ('front', 't_front', 'h_front'), ('back', 't_back', 'h_back'),
              ('align', 't_align', 'h_align'), ('multi', 't_multi', 'h_multi'),
              ('snap', 't_snap', 'h_snap'), ('fit', 't_fit', 'h_fit'),
              ('plate', 't_plate', 'h_plate'), ('serial', 't_serial', 'h_serial')]
SNAPS = [0, 0.5, 1, 5]


class EditorScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        screen_bg(self)
        self.app = App.get_running_app()
        self.canvas_w = PlateCanvas(self)
        self.props = PropertyPanel(self)
        self.hint = TLabel(text=T('h_canvas'), size_hint_y=None, height=dp(26),
                           font_size=sp(12.5), color=MUTED, shorten=True,
                           shorten_from='left' if i18n.is_fa() else 'right')
        self.tool_buttons = {}
        self.portrait = None
        self._live = Clock.create_trigger(lambda dt: self.props.refresh_values(), 0.05)
        self._autosave = Clock.create_trigger(self.autosave, 1.5)
        Window.bind(size=self._on_window)
        Window.bind(on_keyboard=self._on_key)

    # session state lives on the app so a language switch keeps it
    @property
    def s(self):
        return self.app.session

    @property
    def doc(self):
        return self.s['doc']

    @property
    def sel(self):
        return self.s['sel']

    @property
    def snap_step(self):
        return self.s['snap']

    @property
    def multi(self):
        return self.s['multi']

    @property
    def show_grid(self):
        return True

    @property
    def file_path(self):
        return self.s.get('path')

    @property
    def last_symbol_size(self):
        return self.s.get('sym_size', 10)

    @last_symbol_size.setter
    def last_symbol_size(self, v):
        self.s['sym_size'] = v

    def on_pre_enter(self, *a):
        self.build_layout(force=True)
        self.canvas_w.fitted = False
        Clock.schedule_once(lambda dt: self.canvas_w.fit(), 0)

    def on_enter(self, *a):
        if not self.app.settings.get('tour_done') and not self.app.headless:
            Clock.schedule_once(lambda dt: dialogs.tour_dialog(self.app), 0.4)

    def _on_window(self, *a):
        if self.manager and self.manager.current == self.name:
            self.build_layout()

    def _on_key(self, win, key, scancode, codepoint, modifiers):
        if not self.manager or self.manager.current != self.name:
            return False
        focused = any(getattr(w, 'focus', False) for w in self.walk() if hasattr(w, 'focus'))
        if focused:
            return False
        ctrl = 'ctrl' in modifiers or 'meta' in modifiers
        if ctrl and codepoint == 'z':
            self.redo() if 'shift' in modifiers else self.undo()
            return True
        if ctrl and codepoint == 'y':
            self.redo()
            return True
        if ctrl and codepoint == 's':
            dialogs.save_dialog(self)
            return True
        if ctrl and codepoint == 'd':
            self.duplicate()
            return True
        if key in (127, 8) and self.sel:  # delete / backspace
            self.delete()
            return True
        arrows = {273: (0, -1), 274: (0, 1), 276: (-1, 0), 275: (1, 0)}
        if key in arrows and self.sel:
            st = self.snap_step or 0.1
            if 'shift' in modifiers:
                st *= 10
            dx, dy = arrows[key]
            for i in self.sel:
                e = self.doc.get(i)
                e['x'] = round(e['x'] + dx * st, 3)
                e['y'] = round(e['y'] + dy * st, 3)
            self.commit()
            return True
        return False

    # ---- layout ------------------------------------------------------------
    def tool_button(self, icon, label, hint, cb, width=dp(74)):
        b = IconButton(icon=icon, text=T(label), hint=T(hint), size_hint=(None, None),
                       width=width, height=dp(70), icon_size=dp(28), font_size=sp(11.5))
        b.bind(on_release=lambda w: cb())
        self.tool_buttons[icon] = b
        return b

    def build_layout(self, force=False):
        portrait = Window.width < Window.height or Window.width < dp(720)
        if portrait == self.portrait and not force:
            return
        self.portrait = portrait
        self.clear_widgets()
        for w in (self.canvas_w, self.props, self.hint):
            if w.parent:
                w.parent.remove_widget(w)
        self.tool_buttons = {}
        root = BoxLayout(orientation='vertical')
        # top bar
        def tb(icon, cb, hint):
            b = IconButton(icon=icon, text='', hint=T(hint), size_hint_x=None, width=dp(50),
                           primary=True, icon_size=dp(26))
            b.bind(on_release=lambda w: cb())
            return b
        self.undo_b = tb('undo', self.undo, 'h_undo')
        self.redo_b = tb('redo', self.redo, 'h_redo')
        extra = [self.undo_b, self.redo_b, tb('save', lambda: dialogs.save_dialog(self), 'h_save')]
        if not portrait:
            extra += [tb('lang', self.app.toggle_language, 't_lang'),
                      tb('help', lambda: dialogs.tour_dialog(self.app), 't_help'),
                      tb('settings', lambda: dialogs.settings_dialog(self.app), 'settings')]
        else:
            extra += [tb('settings', lambda: dialogs.settings_dialog(self.app), 'settings')]
        exp = IconButton(icon='export', text=T('t_export'), hint=T('h_export'), horizontal=True,
                         size_hint_x=None, width=dp(118) if not portrait else dp(104),
                         font_size=sp(14), icon_size=dp(24))
        exp.bg_color = [1.0, 0.77, 0.0, 1]
        exp._paint()
        exp.bind(on_release=lambda w: dialogs.ExportDialog(self).open())
        extra.append(exp)
        title = disp(self.doc.name) if self.doc.name else T('app_title')
        if portrait:
            title = ''  # no room next to the action buttons on a phone
        root.add_widget(top_bar(title, on_back=self.go_home, extra=extra))
        tools = [(i, l, h, (lambda ii=i: self.insert(ii))) for i, l, h in INSERT_TOOLS]
        edits = [(i, l, h, (lambda ii=i: self.edit_action(ii))) for i, l, h in EDIT_TOOLS]
        if portrait:
            self.canvas_w.size_hint = (1, 1)
            root.add_widget(self.canvas_w)
            hb = Panel(color=(0.93, 0.94, 0.96, 1), radius=0, size_hint_y=None, height=dp(26),
                       padding=(dp(8), 0))
            hb.add_widget(self.hint)
            root.add_widget(hb)
            self.props.size_hint = (1, None)
            self.props.height = max(dp(200), Window.height * 0.36)
            root.add_widget(self.props)
            bar = BoxLayout(size_hint=(None, None), height=dp(78), spacing=dp(4),
                            padding=(dp(4), dp(4)))
            bar.bind(minimum_width=bar.setter('width'))
            for i, l, h, cb in tools + edits:
                bar.add_widget(self.tool_button(i, l, h, cb, width=dp(72)))
            sv = ScrollView(size_hint_y=None, height=dp(82), do_scroll_y=False, bar_width=dp(3))
            sv.add_widget(bar)
            tb_panel = Panel(color=(1, 1, 1, 1), radius=0, size_hint_y=None, height=dp(82))
            tb_panel.add_widget(sv)
            root.add_widget(tb_panel)
        else:
            mid = BoxLayout()
            side = Panel(color=(1, 1, 1, 1), radius=0, size_hint_x=None, width=dp(168),
                         padding=dp(4))
            g = GridLayout(cols=2, size_hint_y=None, spacing=dp(4), padding=dp(2))
            g.bind(minimum_height=g.setter('height'))
            for i, l, h, cb in tools:
                g.add_widget(self.tool_button(i, l, h, cb, width=dp(76)))
            if len(tools) % 2:
                g.add_widget(Widget(size_hint=(None, None), height=dp(70), width=dp(76)))
            for i, l, h, cb in edits:
                g.add_widget(self.tool_button(i, l, h, cb, width=dp(76)))
            sv = ScrollView(do_scroll_x=False, bar_width=dp(4))
            sv.add_widget(g)
            side.add_widget(sv)
            self.props.size_hint = (None, 1)
            self.props.width = dp(330)
            self.canvas_w.size_hint = (1, 1)
            ws = [side, self.canvas_w, self.props]
            if i18n.is_fa():
                ws.reverse()
            for w in ws:
                mid.add_widget(w)
            root.add_widget(mid)
            hb = Panel(color=(0.93, 0.94, 0.96, 1), radius=0, size_hint_y=None, height=dp(28),
                       padding=(dp(10), 0))
            hb.add_widget(self.hint)
            root.add_widget(hb)
        self.add_widget(root)
        self.update_tool_states()
        self.props.rebuild()
        self.canvas_w.redraw()

    def update_tool_states(self):
        tb = self.tool_buttons
        if 'snap' in tb:
            st = self.snap_step
            tb['snap'].set_text(T('t_snap') + ' ' + (fmt(st) if st else T('snap_off')))
        if 'multi' in tb:
            tb['multi'].active = self.multi
            tb['multi']._paint()
        has = bool(self.sel)
        for k in ('dup', 'delete', 'front', 'back', 'align'):
            if k in tb:
                tb[k].opacity = 1 if has else 0.45
        h = self.s['history']
        if hasattr(self, 'undo_b'):
            self.undo_b.opacity = 1 if h.can_undo() else 0.45
            self.redo_b.opacity = 1 if h.can_redo() else 0.45

    # ---- model operations ----------------------------------------------------
    def set_selection(self, ids):
        self.s['sel'] = list(ids)
        self.props.rebuild()
        self.update_tool_states()
        self.canvas_w.redraw()

    def live_update(self):
        self.canvas_w.redraw()
        self._live()

    def commit(self):
        h = self.s['history']
        h.push(self.doc)
        self.canvas_w.redraw()
        self.props.refresh_values()
        self.update_tool_states()
        self._autosave()

    def autosave(self, *a):
        try:
            self.doc.save(self.app.autosave_path)
            if self.file_path:
                self.doc.save(self.file_path)
        except Exception as e:
            print('autosave failed', e)

    def replace_doc(self, doc):
        self.s['doc'] = doc
        self.s['sel'] = [i for i in self.sel if doc.get(i)]
        self.props.rebuild()
        self.canvas_w.redraw()
        self.update_tool_states()
        self._autosave()

    def undo(self):
        d = self.s['history'].undo()
        if d is not None:
            self.replace_doc(d)

    def redo(self):
        d = self.s['history'].redo()
        if d is not None:
            self.replace_doc(d)

    def show_hint(self, text):
        self.hint.text = text

    def insert(self, kind):
        doc = self.doc
        el = None
        if kind == 'text':
            el = doc.add_new('text', text='ترانس رضا' if i18n.is_fa() else 'Trans Reza')
        elif kind == 'line':
            el = doc.add_new('line', w=min(40.0, doc.w * 0.6))
            el['y'] = round(doc.h / 2, 2)
        elif kind == 'rect':
            el = doc.add_new('rect')
        elif kind == 'rrect':
            el = doc.add_new('rect', radius=2.0)
        elif kind == 'ellipse':
            el = doc.add_new('ellipse')
        elif kind == 'hole':
            el = doc.add_new('hole')
        elif kind == 'holes4':
            ids = add_corner_holes(doc, 3.5, min(5.0, doc.w / 6, doc.h / 6))
            self.commit()
            self.set_selection(ids)
            return
        elif kind == 'table':
            el = doc.add_new('table', w=min(60.0, doc.w * 0.8), h=min(24.0, doc.h * 0.5),
                             cells=[['Model', ''], ['Power', ''], ['S/N', '{serial}']])
        elif kind == 'frame':
            el = add_frame(doc, 1.5, 2.0, True, 0.5)
        elif kind == 'symbol':
            dialogs.SymbolLibrary(self).open()
            return
        elif kind == 'image':
            return self.import_image()
        if el is not None:
            self.commit()
            self.set_selection([el['id']])

    def add_symbol(self, sid, size):
        sym = SYMBOLS[sid]
        a = sym.get('aspect', 1.0)
        w, h = (size, size / a) if a >= 1 else (size * a, size)
        el = self.doc.add_new('symbol', sym=sid, w=w, h=h)
        if sym.get('stext'):
            el['stext'] = sym['stext']
        self.commit()
        self.set_selection([el['id']])
        return el

    def import_image(self):
        def got(path):
            try:
                from PIL import Image as PI
                im = PI.open(path)
                im.thumbnail((1400, 1400))
                im = im.convert('RGBA')
                buf = io.BytesIO()
                im.save(buf, 'PNG', optimize=True)
                data = base64.b64encode(buf.getvalue()).decode('ascii')
                w = min(30.0, self.doc.w * 0.5)
                h = w * im.height / float(im.width)
                el = self.doc.add_new('image', data=data, w=round(w, 2), h=round(h, 2))
                self.commit()
                self.set_selection([el['id']])
            except Exception as e:
                toast(self.app.root, 'Image error: %s' % e)
        if platform_io.IS_ANDROID:
            platform_io.android_pick_file('image/*', got)
        else:
            dialogs.file_browser(T('t_image'), ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG'],
                                 os.path.expanduser('~'), got)

    def edit_action(self, kind):
        doc = self.doc
        if kind == 'dup' and self.sel:
            self.duplicate()
        elif kind == 'delete' and self.sel:
            self.delete()
        elif kind == 'front' and self.sel:
            doc.bring_front(self.sel)
            self.commit()
        elif kind == 'back' and self.sel:
            doc.send_back(self.sel)
            self.commit()
        elif kind == 'align' and self.sel:
            dialogs.align_dialog(self)
        elif kind == 'multi':
            self.s['multi'] = not self.multi
            self.update_tool_states()
        elif kind == 'snap':
            i = SNAPS.index(self.snap_step) if self.snap_step in SNAPS else 0
            self.s['snap'] = SNAPS[(i + 1) % len(SNAPS)]
            self.update_tool_states()
            self.props.rebuild()
        elif kind == 'fit':
            self.canvas_w.fit()
        elif kind == 'plate':
            self.set_selection([])
        elif kind == 'serial':
            self.next_serial()

    def duplicate(self):
        ids = self.doc.duplicate(self.sel)
        self.commit()
        self.set_selection(ids)

    def delete(self):
        self.doc.remove(self.sel)
        self.s['sel'] = []
        self.commit()
        self.set_selection([])

    def align(self, mode):
        self.doc.align(self.sel, mode)
        self.commit()

    def next_serial(self, silent=False):
        s = self.doc.increment_serial()
        self.commit()
        if not self.sel:
            self.props.rebuild()
        if not silent:
            toast(self.app.root, '%s: %s' % (i18n.tr('serial_now'), s))

    def resize_plate(self, w, h, scale):
        if not w or not h:
            return
        self.doc.resize_plate(w, h, scale)
        self.commit()
        self.props.rebuild()
        self.canvas_w.fit()

    def edit_cells(self):
        e = self.doc.get(self.sel[0]) if len(self.sel) == 1 else None
        if e is not None and e['type'] == 'table':
            dialogs.cells_dialog(self, e)

    def focus_text(self):
        ti = self.props.text_input
        if ti is not None:
            ti.focus = True
        elif len(self.sel) == 1 and self.doc.get(self.sel[0])['type'] == 'table':
            self.edit_cells()

    def save_to(self, path):
        self.doc.name = self.doc.name or os.path.splitext(os.path.basename(path))[0]
        self.doc.save(path)
        self.s['path'] = path
        self.app.add_recent(path)
        toast(self.app.root, i18n.tr('saved_ok'))

    def go_home(self):
        self.autosave()
        self.app.go('start')
