"""Trans Plate Designer / طراح پلاک ترانس

Design printable nameplates for transformers and voltage stabilizers.
Kivy app for Android (buildozer) and Windows (PyInstaller)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Windowed (no console) Windows exe: give Kivy somewhere to write logs.
if getattr(sys, 'frozen', False):
    os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

from kivy.config import Config  # noqa: E402
from kivy.utils import platform  # noqa: E402

if platform not in ('android', 'ios'):
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
    if not os.environ.get('TPD_WINDOW_SIZE'):
        Config.set('graphics', 'width', '1280')
        Config.set('graphics', 'height', '800')
    else:
        w, h = os.environ['TPD_WINDOW_SIZE'].split('x')
        Config.set('graphics', 'width', w)
        Config.set('graphics', 'height', h)
Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.resources import resource_add_path  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.screenmanager import NoTransition, ScreenManager  # noqa: E402

resource_add_path(HERE)

import i18n  # noqa: E402
import platform_io  # noqa: E402
from model import Document, History  # noqa: E402
from ui.common import register_fonts, toast  # noqa: E402

register_fonts()

from ui import screens  # noqa: E402


class TransPlateApp(App):
    title = 'Trans Plate Designer - طراح پلاک ترانس'
    icon = os.path.join('assets', 'icon.png')

    def build(self):
        self.headless = bool(os.environ.get('TPD_HEADLESS'))
        self.dirs = platform_io.app_dirs(self.user_data_dir)
        self.autosave_path = os.path.join(self.user_data_dir, 'autosave.tplate')
        self.settings_path = os.path.join(self.user_data_dir, 'settings.json')
        self.settings = self.load_settings()
        i18n.set_lang(self.settings.get('lang', 'fa'))
        Window.clearcolor = (0.957, 0.965, 0.973, 1)
        Window.softinput_mode = 'below_target'
        Window.bind(on_keyboard=self._back_key)
        self.session = None
        self.new_session(Document(100, 60))
        self.root_float = FloatLayout()
        self.sm = None
        self.build_ui('start')
        platform_io.request_android_permissions()
        return self.root_float

    # ---- settings ------------------------------------------------------------
    def load_settings(self):
        d = {'lang': 'fa', 'snap': 1, 'corr_x': 100.0, 'corr_y': 100.0, 'dpi': 600,
             'recent': [], 'tour_done': False}
        try:
            with open(self.settings_path, encoding='utf-8') as f:
                d.update(json.load(f))
        except Exception:
            pass
        return d

    def save_settings(self):
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=1)
        except Exception as e:
            print('settings save failed', e)

    def corr(self):
        return (float(self.settings.get('corr_x', 100)) / 100.0,
                float(self.settings.get('corr_y', 100)) / 100.0)

    def add_recent(self, path):
        r = [p for p in self.settings.get('recent', []) if p != path]
        self.settings['recent'] = [path] + r[:14]
        self.save_settings()

    # ---- UI --------------------------------------------------------------------
    def build_ui(self, current='start'):
        self.root_float.clear_widgets()
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(screens.StartScreen(name='start'))
        sm.add_widget(screens.TemplateScreen(name='templates'))
        sm.add_widget(screens.OpenScreen(name='open'))
        self.editor = screens.EditorScreen(name='editor')
        sm.add_widget(self.editor)
        sm.current = current
        self.sm = sm
        self.root_float.add_widget(sm)

    def go(self, name):
        self.sm.current = name

    def toggle_language(self):
        lang = 'en' if i18n.is_fa() else 'fa'
        i18n.set_lang(lang)
        self.settings['lang'] = lang
        self.save_settings()
        cur = self.sm.current if self.sm else 'start'
        if cur == 'templates':
            cur = 'start'
        self.build_ui(cur)

    def show_hint(self, text):
        if self.sm and self.sm.current == 'editor':
            self.editor.show_hint(text)

    def toast(self, text):
        toast(self.root_float, text)

    # ---- documents -------------------------------------------------------------
    def new_session(self, doc, path=None):
        self.session = {'doc': doc, 'sel': [], 'history': History(doc),
                        'snap': float(self.settings.get('snap', 1)) if hasattr(self, 'settings')
                        else 1.0, 'multi': False, 'path': path, 'sym_size': 10}
        if self.session['snap'] == int(self.session['snap']):
            self.session['snap'] = int(self.session['snap'])

    def new_doc(self, doc, path=None):
        self.new_session(doc, path)
        try:
            doc.save(self.autosave_path)
        except Exception:
            pass
        self.go('editor')

    def open_file(self, path):
        try:
            doc = Document.load(path)
        except Exception as e:
            self.toast('Open failed: %s' % e)
            return
        if path != self.autosave_path:
            self.add_recent(path)
        self.new_doc(doc, path if path != self.autosave_path else None)

    def continue_last(self):
        self.open_file(self.autosave_path)

    def _back_key(self, win, key, *a):
        if key == 27:  # Android back / Esc
            if self.sm.current == 'editor':
                self.editor.go_home()
                return True
            if self.sm.current != 'start':
                self.go('start')
                return True
        return False

    def on_pause(self):
        try:
            self.session['doc'].save(self.autosave_path)
        except Exception:
            pass
        return True

    def on_stop(self):
        self.on_pause()


if __name__ == '__main__':
    TransPlateApp().run()
