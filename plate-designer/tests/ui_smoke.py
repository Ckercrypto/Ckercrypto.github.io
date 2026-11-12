"""Headless end-to-end UI smoke test (needs an X server / Xvfb).

  Xvfb :99 -screen 0 1400x2500x24 &
  DISPLAY=:99 TPD_HEADLESS=1 python tests/ui_smoke.py OUTDIR [desktop|phone]

Drives the real app: start screen, new plate, every symbol, symbol library,
template wizard, property edits, touch move/resize/rotate, undo/redo,
exports (through the export dialog), language toggle; saves screenshots."""
import os
import sys
import tempfile
import traceback

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
MODE = sys.argv[2] if len(sys.argv) > 2 else 'desktop'
os.makedirs(OUT, exist_ok=True)
os.environ.setdefault('TPD_HEADLESS', '1')
if MODE == 'phone':
    os.environ['TPD_WINDOW_SIZE'] = '1080x2400'
    os.environ.setdefault('KIVY_METRICS_DENSITY', '2.75')
else:
    os.environ['TPD_WINDOW_SIZE'] = '1360x820'
HOME = tempfile.mkdtemp(prefix='tpd_home_')
os.environ['HOME'] = HOME  # isolate Documents/TransPlate + kivy config
os.environ['KIVY_HOME'] = os.path.join(HOME, '.kivy')
os.makedirs(os.path.join(HOME, '.config'), exist_ok=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import main  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.tests.common import UnitTestTouch  # noqa: E402

import export  # noqa: E402
from symbols import SYMBOLS  # noqa: E402

app = main.TransPlateApp()
results = []
errors = []


def shot(name):
    p = os.path.join(OUT, '%s_%s.png' % (MODE, name))
    # draw the current frame into the back buffer first (glReadPixels reads it)
    Window.dispatch('on_draw')
    Window.screenshot(name=p)
    # Window.screenshot appends a counter: find and rename
    base, ext = os.path.splitext(p)
    for f in sorted(os.listdir(OUT)):
        full = os.path.join(OUT, f)
        if f.startswith(os.path.basename(base)) and f != os.path.basename(p) and f.endswith(ext):
            os.replace(full, p)
    results.append(p)


def ed():
    return app.editor


def touch_drag(x0, y0, x1, y1, steps=6):
    t = UnitTestTouch(x0, y0)
    t.touch_down()
    for i in range(1, steps + 1):
        t.touch_move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
    t.touch_up()


def mm_to_win(cv, x, y):
    vx = cv.ox + x * cv.zoom
    vy = cv.oy + y * cv.zoom
    return cv.x + vx, cv.top - vy


def close_popups():
    from kivy.uix.modalview import ModalView
    for w in list(Window.children):
        if isinstance(w, ModalView):
            w.dismiss(animation=False)


steps = []


def step(delay=0.5):
    def deco(fn):
        steps.append((fn, delay))
        return fn
    return deco


@step(1.0)
def s_start():
    shot('01_start_fa')


@step()
def s_new():
    app.new_doc(main.Document(100, 60))


@step(0.8)
def s_tour():
    shot('02_tour')
    close_popups()
    app.settings['tour_done'] = True


@step()
def s_all_symbols():
    e = ed()
    x = y = 2.0
    for sid in SYMBOLS:
        el = e.add_symbol(sid, 8)
        el['x'], el['y'] = x, y
        x += 9.5
        if x > 92:
            x, y = 2.0, y + 9.5
    e.commit()
    assert len(e.doc.elements) == len(SYMBOLS)
    e.set_selection([e.doc.elements[0]['id']])


@step(1.0)
def s_shot_symbols_on_plate():
    shot('03_editor_all_symbols')


@step()
def s_touch_move():
    e = ed()
    cv = e.canvas_w
    el = e.doc.elements[0]
    x0, y0 = el['x'], el['y']
    wx, wy = mm_to_win(cv, el['x'] + el['w'] / 2, el['y'] + el['h'] / 2)
    touch_drag(wx, wy, wx + cv.zoom * 5, wy - cv.zoom * 3)
    assert abs(el['x'] - (x0 + 5)) < 0.6 and abs(el['y'] - (y0 + 3)) < 0.6, (el['x'], el['y'])
    # resize via SE handle
    import raster
    hs = {n: (hx, hy) for n, hx, hy in raster.handle_positions(el, cv.zoom, cv.ox, cv.oy, cv.ui())}
    hx, hy = hs['se']
    w0 = el['w']
    touch_drag(cv.x + hx, cv.top - hy, cv.x + hx + cv.zoom * 4, cv.top - hy - cv.zoom * 4)
    assert el['w'] > w0 + 2, (w0, el['w'])
    # rotate
    hx, hy = hs['rot'] if 'rot' in hs else (None, None)
    hs = {n: (hx, hy) for n, hx, hy in raster.handle_positions(el, cv.zoom, cv.ox, cv.oy, cv.ui())}
    rx, ry = hs['rot']
    cx, cy = mm_to_win(cv, el['x'] + el['w'] / 2, el['y'] + el['h'] / 2)
    touch_drag(cv.x + rx, cv.top - ry, cx + 200, cy)
    assert abs(el['rot'] - 90) < 1, el['rot']
    e.undo()
    assert abs(e.doc.elements[0].get('rot', 0)) < 1e-6
    e.redo()
    assert abs(e.doc.elements[0]['rot'] - 90) < 1
    results.append('touch move/resize/rotate + undo/redo OK')


@step()
def s_edit_ops():
    e = ed()
    n = len(e.doc.elements)
    e.set_selection([e.doc.elements[-1]['id']])
    e.edit_action('dup')
    assert len(e.doc.elements) == n + 1
    e.edit_action('delete')
    assert len(e.doc.elements) == n
    e.set_selection([e.doc.elements[0]['id']])
    e.align('center_plate')
    e.edit_action('front')
    e.edit_action('back')
    e.edit_action('snap')
    e.edit_action('snap')
    for k in ('text', 'line', 'rect', 'rrect', 'ellipse', 'hole', 'holes4', 'table', 'frame'):
        e.insert(k)
    # numeric property edit on the selected frame
    nf = e.props.nums.get('x')
    nf.inp.text = '7.5'
    nf.commit()
    assert abs(e.doc.get(e.sel[0])['x'] - 7.5) < 1e-6
    e.next_serial(silent=True)
    assert e.doc.vars['serial'] == '0002'
    results.append('insert tools / dup / delete / align / layers / snap / numeric edit / serial OK')


@step()
def s_textfield():
    from ui.common import TextField
    from textshape import shape
    f = TextField(text='')
    for ch in 'ترانس':
        f.insert_text(ch)
    f.insert_text(' 5kVA')
    f.do_backspace()
    assert f.ltext == 'ترانس 5kV', f.ltext
    assert f.text == shape('ترانس 5kV'), f.text
    g = TextField(text='TR-50')
    g.insert_text('0')
    assert g.ltext == 'TR-500'
    results.append('Persian TextField typing/backspace OK')


@step(0.6)
def s_library():
    from ui.dialogs import SymbolLibrary
    e = ed()
    e.set_selection([])
    lib = SymbolLibrary(e)
    lib.open()
    app._lib = lib


@step(1.0)
def s_library_shot():
    shot('04_symbol_library')
    app._lib.pick(SYMBOLS['hv_warning'])


@step()
def s_wizard():
    app.go('templates')


@step(0.6)
def s_wizard_list():
    shot('05_templates')
    ts = app.sm.get_screen('templates')
    ts.show_form('transformer')


@step(0.6)
def s_wizard_form():
    ts = app.sm.get_screen('templates')
    vals = {'model': 'TR-10K', 'kva': '10', 'vin': '380', 'vout': '220', 'hz': '50',
            'amp': '45.5', 'ins': 'F', 'ip': 'IP21', 'serial': 'TR-1405-0007',
            'date': '1405/08/22', 'phone': '051-3800 0000', 'address': 'مشهد، بازار برق'}
    for k, v in vals.items():
        ts.fields[k].set_ltext(v)
    ts._choose('phases', '3')
    ts._choose('conn', 'D')
    shot('06_wizard_form')
    ts.generate()


@step(1.2)
def s_editor_template():
    shot('07_editor_template')
    e = ed()
    tbl = [x for x in e.doc.elements if x['type'] == 'table'][0]
    e.set_selection([tbl['id']])


@step(0.8)
def s_export_files():
    shot('08_editor_table_selected')
    e = ed()
    doc = e.doc
    p = os.path.join(OUT, MODE + '_transformer_1to1.pdf')
    export.export_pdf(doc, p, 600)
    export.export_png(doc, os.path.join(OUT, MODE + '_transformer_600dpi.png'), 600)
    export.export_svg(doc, os.path.join(OUT, MODE + '_transformer.svg'))
    info = export.export_tiled_pdf(doc, os.path.join(OUT, MODE + '_transformer_A4.pdf'),
                                   copies=8, spacing=3, dpi=300, vary_serial=True)
    results.append('tiled info %r' % info)
    from ui.dialogs import ExportDialog
    d = ExportDialog(e)
    d.set_fmt('tiled')
    d.open()
    app._dlg = d


@step(0.8)
def s_export_dialog():
    shot('09_export_dialog')
    d = app._dlg
    d.set_fmt('png')
    d.set_dpi(300)
    d.run()


@step(2.5)
def s_after_export():
    shot('10_export_result')
    close_popups()
    files = os.listdir(app.dirs['exports'])
    results.append('dialog export files: %r' % files)
    assert any(f.endswith('.png') for f in files), files


@step(0.6)
def s_settings():
    from ui.dialogs import settings_dialog
    settings_dialog(app)


@step(0.8)
def s_settings_shot():
    shot('11_settings_calibration')
    close_popups()
    from ui.dialogs import save_dialog
    save_dialog(ed())


@step(0.6)
def s_save():
    e = ed()
    e.save_to(os.path.join(app.dirs['projects'], 'test_plate.tplate'))
    close_popups()
    assert os.path.exists(os.path.join(app.dirs['projects'], 'test_plate.tplate'))
    app.toggle_language()


@step(1.0)
def s_english():
    shot('12_editor_english')
    app.go('open')


@step(0.8)
def s_open():
    shot('13_open_screen')
    app.open_file(os.path.join(app.dirs['projects'], 'test_plate.tplate'))


@step(0.8)
def s_reopened():
    assert any(e['type'] == 'table' for e in ed().doc.elements)
    app.go('start')


@step(0.8)
def s_start_en():
    shot('14_start_en')


def run_steps(i=0):
    if i >= len(steps):
        with open(os.path.join(OUT, MODE + '_results.txt'), 'w') as f:
            f.write('\n'.join(map(str, results)) + '\n')
            f.write('ERRORS:\n' + '\n'.join(errors) + '\n')
        print('\n'.join(map(str, results)))
        print('ERRORS:', len(errors))
        for e in errors:
            print(e)
        app.stop()
        return
    fn, delay = steps[i]
    try:
        fn()
        print('step ok', fn.__name__, flush=True)
    except Exception:
        errors.append('%s: %s' % (fn.__name__, traceback.format_exc()))
        print('step FAILED', fn.__name__, traceback.format_exc(), flush=True)
    Clock.schedule_once(lambda dt: run_steps(i + 1), delay)


Clock.schedule_once(lambda dt: run_steps(0), 1.5)
app.run()
