"""Shared Kivy widgets and helpers."""
import os

from kivy.animation import Animation
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty, ObjectProperty,
                             StringProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import i18n
from textshape import shape, has_rtl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, 'assets', 'icons')
FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')

PRIMARY = (0.082, 0.396, 0.753, 1)      # #1565C0
PRIMARY_DARK = (0.05, 0.17, 0.34, 1)
ACCENT = (1.0, 0.77, 0.0, 1)
BG = (0.957, 0.965, 0.973, 1)
CARD = (1, 1, 1, 1)
TEXT = (0.13, 0.17, 0.2, 1)
MUTED = (0.42, 0.47, 0.52, 1)
BTN = (0.90, 0.92, 0.95, 1)
DANGER = (0.80, 0.16, 0.16, 1)
ACTIVE = (0.80, 0.89, 0.98, 1)

_fonts_done = []


def register_fonts():
    if _fonts_done:
        return
    reg = os.path.join(FONT_DIR, 'Vazirmatn-Regular.ttf')
    bold = os.path.join(FONT_DIR, 'Vazirmatn-Bold.ttf')
    # Override Kivy's default font so every widget uses Vazirmatn (FA + Latin glyphs).
    LabelBase.register(name='Roboto', fn_regular=reg, fn_bold=bold, fn_italic=reg,
                       fn_bolditalic=bold)
    LabelBase.register(name='Vazirmatn', fn_regular=reg, fn_bold=bold)
    _fonts_done.append(1)


def icon_path(name):
    p = os.path.join(ICON_DIR, name + '.png')
    return p if os.path.exists(p) else os.path.join(ICON_DIR, 'help.png')


def pil_to_texture(img):
    img = img.convert('RGBA')
    tex = Texture.create(size=img.size, colorfmt='rgba')
    tex.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
    tex.flip_vertical()
    return tex


def halign():
    return 'right' if i18n.is_fa() else 'left'


class BgMixin:
    """Rounded background drawn behind a widget."""

    def init_bg(self, color, radius=dp(10), border=None):
        with self.canvas.before:
            self._bg_c = Color(*color)
            self._bg_r = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            if border:
                self._bd_c = Color(*border)
                self._bd_l = Line(rounded_rectangle=(self.x, self.y, self.width, self.height,
                                                     radius), width=dp(1))
        self._radius = radius
        self._border = border
        self.bind(pos=self._upd_bg, size=self._upd_bg)

    def _upd_bg(self, *a):
        self._bg_r.pos = self.pos
        self._bg_r.size = self.size
        if self._border:
            self._bd_l.rounded_rectangle = (self.x, self.y, self.width, self.height,
                                            self._radius)

    def set_bg(self, color):
        self._bg_c.rgba = color


class Panel(BoxLayout, BgMixin):
    def __init__(self, color=CARD, radius=dp(10), border=None, **kw):
        super().__init__(**kw)
        self.init_bg(color, radius, border)


class TLabel(Label):
    """Label that wraps to its width and aligns per language."""

    def __init__(self, **kw):
        kw.setdefault('color', TEXT)
        kw.setdefault('halign', halign())
        kw.setdefault('valign', 'middle')
        kw.setdefault('font_size', sp(15))
        super().__init__(**kw)
        self.bind(size=self._wrap)
        self._wrap()

    def _wrap(self, *a):
        self.text_size = (self.width, None if self.size_hint_y is None else self.height)


def wrap_logical(text, width, font_size, bold=False):
    """Wrap logical (unshaped) text to width px, then shape each line.

    Kivy wraps the already-reordered visual string, which breaks Persian
    sentences in the wrong place; wrapping first keeps word order right."""
    from kivy.core.text import Label as CoreLabel
    cl = CoreLabel(font_size=font_size, bold=bold)
    out = []
    for para in (text or '').split('\n'):
        line = ''
        for w in para.split(' '):
            cand = (line + ' ' + w) if line else w
            if not line or cl.get_extents(shape(cand))[0] <= width:
                line = cand
            else:
                out.append(line)
                line = w
        out.append(line)
    return '\n'.join(shape(x) for x in out)


class AutoLabel(TLabel):
    """Wrapping label whose height follows its text.

    Pass ltext= (logical, unshaped) for Persian-safe wrapping."""

    def __init__(self, ltext=None, **kw):
        kw.setdefault('size_hint_y', None)
        self._ltext = ltext
        super().__init__(**kw)
        self.bind(texture_size=lambda *a: setattr(self, 'height', self.texture_size[1] + dp(6)))
        self.bind(width=lambda *a: self._rewrap())
        self._rewrap()

    def set_ltext(self, s):
        self._ltext = s
        self._rewrap()

    def _rewrap(self, *a):
        if self._ltext is None:
            return
        if has_rtl(self._ltext) and self.width > 20:
            self.text = wrap_logical(self._ltext, self.width - dp(4), self.font_size, self.bold)
        else:
            self.text = shape(self._ltext)


class IconButton(ButtonBehavior, BoxLayout, BgMixin):
    """Big touch-friendly button: icon above (or beside) a short label."""
    icon = StringProperty('')
    text = StringProperty('')
    hint = StringProperty('')
    active = BooleanProperty(False)
    bg_color = ListProperty(list(BTN))
    fg_color = ListProperty(list(TEXT))

    def __init__(self, icon='', text='', hint='', horizontal=False, primary=False,
                 icon_size=dp(28), font_size=sp(12), **kw):
        kw.setdefault('orientation', 'horizontal' if horizontal else 'vertical')
        kw.setdefault('padding', (dp(6), dp(4)))
        kw.setdefault('spacing', dp(2) if not horizontal else dp(10))
        super().__init__(**kw)
        if primary:
            self.bg_color = list(PRIMARY)
            self.fg_color = [1, 1, 1, 1]
        self.init_bg(self.bg_color, dp(10))
        self.icon, self.text, self.hint = icon, text, hint
        self._img = Image(source=icon_path(icon) if icon else '', color=self.fg_color,
                          size_hint=(None, None), size=(icon_size, icon_size),
                          fit_mode='contain')
        self._lbl = Label(text=text, color=self.fg_color, font_size=font_size,
                          halign='center' if not horizontal else halign(),
                          valign='middle', shorten=True, shorten_from='right')
        self._lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        if icon:
            if horizontal:
                self.add_widget(self._img)
            else:
                box = BoxLayout(size_hint_y=None, height=icon_size)
                box.add_widget(Widget())
                box.add_widget(self._img)
                box.add_widget(Widget())
                self.add_widget(box)
        if text:
            self.add_widget(self._lbl)
        if horizontal and i18n.is_fa() and icon and text:
            # icon on the right for RTL
            self.remove_widget(self._img)
            self.add_widget(self._img)
        self.bind(state=self._paint, active=self._paint, bg_color=self._paint)
        Window.bind(mouse_pos=self._hover)

    def set_text(self, t):
        self.text = t
        self._lbl.text = t

    def _paint(self, *a):
        c = list(self.bg_color)
        if self.active:
            c = list(ACTIVE) if self.bg_color != list(PRIMARY) else list(PRIMARY_DARK)
        if self.state == 'down':
            c = [max(0, v - 0.12) for v in c[:3]] + [1]
        self.set_bg(c)

    def _hover(self, win, pos):
        if not self.hint or not self.get_root_window():
            return
        if self.collide_point(*self.to_widget(*pos)):
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, 'show_hint'):
                app.show_hint(self.hint)

    def on_press(self):
        if self.hint:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, 'show_hint'):
                app.show_hint(self.hint)


class TButton(Button):
    def __init__(self, primary=False, **kw):
        kw.setdefault('background_normal', '')
        kw.setdefault('background_down', '')
        kw.setdefault('background_color', PRIMARY if primary else BTN)
        kw.setdefault('color', (1, 1, 1, 1) if primary else TEXT)
        kw.setdefault('font_size', sp(15))
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(48))
        super().__init__(**kw)
        self._base = kw['background_color']
        self.bind(state=self._st)

    def _st(self, *a):
        b = self._base
        self.background_color = ([max(0, v - 0.12) for v in b[:3]] + [1]
                                 if self.state == 'down' else b)


_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫', '01234567890123456789.')


def latin_digits(s):
    return (s or '').translate(_FA_DIGITS)


class Field(TextInput):
    def __init__(self, **kw):
        kw.setdefault('multiline', False)
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(42))
        kw.setdefault('font_size', sp(16))
        kw.setdefault('padding', (dp(8), dp(10)))
        kw.setdefault('write_tab', False)
        super().__init__(**kw)


class TextField(Field):
    """TextInput that shows Persian joined and right-to-left.

    Kivy's TextInput has no shaping/bidi.  While the text contains RTL
    letters this field keeps the logical text in .ltext and displays the
    shaped string; typing appends and backspace removes from the end
    (cursor editing inside Persian text is not supported).  Pure Latin
    text behaves like a normal TextInput.  Always read .ltext."""

    def __init__(self, **kw):
        txt = kw.pop('text', '') or ''
        super().__init__(**kw)
        self._ltext = txt
        self._sync()

    @property
    def ltext(self):
        return self._ltext if self._rtl() else self.text

    def _rtl(self):
        return has_rtl(self._ltext)

    def _sync(self):
        if self._rtl():
            self.text = shape(self._ltext)
            self.halign = 'right'
            self.cursor = (0, 0) if '\n' not in self._ltext else (0, len(self._lines) - 1)
        else:
            self.text = self._ltext
            self.halign = 'left'
            self.cursor = (len(self._lines[-1]) if self._lines else 0, max(0, len(self._lines) - 1))

    def insert_text(self, substring, from_undo=False):
        if not self._rtl() and not has_rtl(substring):
            super().insert_text(substring, from_undo=from_undo)
            self._ltext = self.text
            return
        if not self._rtl():
            self._ltext = self.text
        if self.selection_text and len(self.selection_text) >= len(self.text):
            self._ltext = ''
        self._ltext += substring
        self._sync()

    def do_backspace(self, from_undo=False, mode='bkspc'):
        if not self._rtl():
            super().do_backspace(from_undo=from_undo, mode=mode)
            self._ltext = self.text
            return
        if self.selection_text and len(self.selection_text) >= len(self.text):
            self._ltext = ''
        else:
            self._ltext = self._ltext[:-1]
        self._sync()

    def delete_selection(self, from_undo=False):
        if not self._rtl():
            return super().delete_selection(from_undo=from_undo)
        if self.selection_text and len(self.selection_text) >= len(self.text):
            self._ltext = ''
            self.cancel_selection()
            self._sync()

    def set_ltext(self, s):
        self._ltext = s or ''
        self._sync()


def hrow(*widgets, height=dp(44), spacing=dp(6)):
    """Horizontal row whose children are mirrored in Persian (RTL)."""
    b = BoxLayout(size_hint_y=None, height=height, spacing=spacing)
    ws = list(widgets)
    if i18n.is_fa():
        ws.reverse()
    for w in ws:
        b.add_widget(w)
    return b


def labeled_field(label_key, value='', label_w=dp(150), **kw):
    lab = TLabel(text=i18n.T(label_key), size_hint_x=None, width=label_w)
    f = TextField(text=str(value), **kw)
    return hrow(lab, f), f


class Toast(Label):
    pass


def toast(root, text, duration=2.2):
    if root is None:
        return
    lbl = Label(text=shape(text), size_hint=(None, None), color=(1, 1, 1, 1),
                font_size=sp(15), padding=(dp(16), dp(10)))
    lbl.texture_update()
    lbl.size = (min(lbl.texture_size[0] + dp(10), root.width * 0.95),
                lbl.texture_size[1] + dp(6))
    lbl.pos = (root.center_x - lbl.width / 2, dp(110))
    with lbl.canvas.before:
        Color(0.1, 0.12, 0.15, 0.92)
        r = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(18)])
    lbl.bind(pos=lambda w, p: setattr(r, 'pos', p))
    root.add_widget(lbl)
    anim = Animation(opacity=1, duration=duration) + Animation(opacity=0, duration=0.4)
    anim.bind(on_complete=lambda *a: root.remove_widget(lbl))
    anim.start(lbl)
    return lbl


def disp(s):
    """Shape arbitrary user text for a Kivy label."""
    return shape(s) if has_rtl(s) else s
