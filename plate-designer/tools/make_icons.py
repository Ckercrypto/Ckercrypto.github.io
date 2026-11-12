"""Generate UI icons (white, tinted in Kivy), app icon and presplash with Pillow.

Run from the project folder:  python tools/make_icons.py
Icons are drawn from the same primitives as the symbol library."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw  # noqa: E402

import raster  # noqa: E402
import symbols  # noqa: E402
from textshape import shape  # noqa: E402

ICONS = {
    'select': [('P', [(0.28, 0.1), (0.28, 0.8), (0.44, 0.64), (0.56, 0.9), (0.66, 0.85),
                      (0.54, 0.6), (0.76, 0.6)], False)],
    'text': [('T', 'T', 0.5, 0.52, 0.85)],
    'line': [('L', [(0.15, 0.85), (0.85, 0.15)], {'wf': 1.2})],
    'rect': [('R', 0.12, 0.25, 0.76, 0.5, False)],
    'rrect': [('RR', 0.12, 0.25, 0.76, 0.5, 0.2, False)],
    'ellipse': [('C', 0.5, 0.5, 0.36, False)],
    'hole': [('C', 0.5, 0.5, 0.3, False), ('L', [(0.32, 0.5), (0.68, 0.5)]),
             ('L', [(0.5, 0.32), (0.5, 0.68)])],
    'holes4': [('RR', 0.08, 0.18, 0.84, 0.64, 0.08, False)] +
              [('C', x, y, 0.07, False) for x in (0.22, 0.78) for y in (0.32, 0.68)],
    'table': [('R', 0.1, 0.18, 0.8, 0.64, False), ('L', [(0.1, 0.39), (0.9, 0.39)]),
              ('L', [(0.1, 0.6), (0.9, 0.6)]), ('L', [(0.42, 0.18), (0.42, 0.82)])],
    'frame': [('RR', 0.08, 0.18, 0.84, 0.64, 0.1, False),
              ('RR', 0.17, 0.27, 0.66, 0.46, 0.05, False)],
    'symbol': [('P', [(0.55, 0.06), (0.22, 0.55), (0.46, 0.55), (0.34, 0.94), (0.78, 0.42),
                      (0.54, 0.42), (0.7, 0.06)], True)],
    'image': [('R', 0.1, 0.18, 0.8, 0.64, False), ('C', 0.68, 0.36, 0.07, True),
              ('P', [(0.14, 0.78), (0.4, 0.44), (0.6, 0.78)], True),
              ('P', [(0.46, 0.78), (0.64, 0.56), (0.86, 0.78)], True)],
    'dup': [('R', 0.12, 0.12, 0.5, 0.5, False), ('R', 0.38, 0.38, 0.5, 0.5, False)],
    'delete': [('P', [(0.24, 0.3), (0.76, 0.3), (0.7, 0.9), (0.3, 0.9)], False),
               ('L', [(0.16, 0.24), (0.84, 0.24)]),
               ('L', [(0.4, 0.24), (0.42, 0.12), (0.58, 0.12), (0.6, 0.24)]),
               ('L', [(0.42, 0.42), (0.43, 0.78)]), ('L', [(0.58, 0.42), (0.57, 0.78)])],
    'front': [('R', 0.1, 0.1, 0.5, 0.5, False), ('R', 0.38, 0.38, 0.52, 0.52, True)],
    'back': [('R', 0.1, 0.1, 0.5, 0.5, True), ('R', 0.38, 0.38, 0.52, 0.52, False)],
    'align': [('L', [(0.14, 0.08), (0.14, 0.92)]), ('R', 0.24, 0.2, 0.6, 0.2, True),
              ('R', 0.24, 0.56, 0.38, 0.2, True)],
    'snap': [('C', x, y, 0.045, True) for x in (0.2, 0.5, 0.8) for y in (0.2, 0.5, 0.8)] +
            [('R', 0.2, 0.2, 0.3, 0.3, False, {'wf': 1.3})],
    'fit': [('L', [(0.1, 0.32), (0.1, 0.1), (0.32, 0.1)]), ('L', [(0.68, 0.1), (0.9, 0.1), (0.9, 0.32)]),
            ('L', [(0.9, 0.68), (0.9, 0.9), (0.68, 0.9)]), ('L', [(0.32, 0.9), (0.1, 0.9), (0.1, 0.68)]),
            ('R', 0.3, 0.36, 0.4, 0.28, False)],
    'plate': [('RR', 0.06, 0.2, 0.88, 0.6, 0.1, False), ('C', 0.18, 0.32, 0.05, False),
              ('C', 0.82, 0.68, 0.05, False), ('L', [(0.3, 0.42), (0.7, 0.42)]),
              ('L', [(0.3, 0.58), (0.62, 0.58)])],
    'serial': [('T', '#+1', 0.5, 0.52, 0.5)],
    'multi': [('R', 0.08, 0.1, 0.42, 0.42, False), ('R', 0.5, 0.48, 0.42, 0.42, False),
              ('L', [(0.16, 0.32), (0.26, 0.42), (0.42, 0.2)])],
    'undo': [('A', 0.52, 0.56, 0.3, 180, 450), ('P', [(0.08, 0.5), (0.36, 0.5), (0.22, 0.72)], True)],
    'redo': [('A', 0.48, 0.56, 0.3, 90, 360), ('P', [(0.92, 0.5), (0.64, 0.5), (0.78, 0.72)], True)],
    'save': [('P', [(0.12, 0.12), (0.74, 0.12), (0.88, 0.26), (0.88, 0.88), (0.12, 0.88)], False),
             ('R', 0.28, 0.12, 0.38, 0.22, False), ('R', 0.26, 0.54, 0.48, 0.34, False)],
    'export': [('L', [(0.2, 0.52), (0.2, 0.88), (0.8, 0.88), (0.8, 0.52)]),
               ('L', [(0.5, 0.66), (0.5, 0.14)]), ('P', [(0.5, 0.06), (0.32, 0.28), (0.68, 0.28)], True)],
    'lang': [('T', 'A', 0.28, 0.42, 0.55), ('T', 'ف', 0.72, 0.62, 0.6),
             ('L', [(0.5, 0.1), (0.5, 0.9)])],
    'help': [('C', 0.5, 0.5, 0.42, False), ('T', '?', 0.5, 0.52, 0.55)],
    'home': [('P', [(0.5, 0.1), (0.9, 0.46), (0.78, 0.46), (0.78, 0.88), (0.22, 0.88),
                    (0.22, 0.46), (0.1, 0.46)], False), ('R', 0.42, 0.62, 0.16, 0.26, False)],
    'new': [('P', [(0.2, 0.08), (0.62, 0.08), (0.8, 0.26), (0.8, 0.92), (0.2, 0.92)], False),
            ('L', [(0.5, 0.38), (0.5, 0.74)], {'wf': 1.3}), ('L', [(0.32, 0.56), (0.68, 0.56)], {'wf': 1.3})],
    'template': [('P', [(0.2, 0.08), (0.8, 0.08), (0.8, 0.92), (0.2, 0.92)], False),
                 ('L', [(0.32, 0.26), (0.68, 0.26)]), ('R', 0.32, 0.38, 0.36, 0.22, False),
                 ('L', [(0.32, 0.72), (0.68, 0.72)]), ('L', [(0.32, 0.82), (0.56, 0.82)])],
    'open': [('P', [(0.08, 0.22), (0.38, 0.22), (0.46, 0.32), (0.92, 0.32), (0.92, 0.84),
                    (0.08, 0.84)], False), ('L', [(0.08, 0.44), (0.92, 0.44)])],
    'settings': [('C', 0.5, 0.5, 0.26, False), ('C', 0.5, 0.5, 0.1, False)] +
                [('L', [symbols._polar(0.5, 0.5, 0.27, a), symbols._polar(0.5, 0.5, 0.42, a)],
                  {'wf': 2.4}) for a in range(0, 360, 45)],
    'calib': [('R', 0.06, 0.32, 0.88, 0.36, False)] +
             [('L', [(0.14 + i * 0.09, 0.32), (0.14 + i * 0.09, 0.32 + (0.18 if i % 2 == 0 else 0.1))])
              for i in range(9)],
    'share': [('C', 0.74, 0.22, 0.1, False), ('C', 0.26, 0.5, 0.1, False), ('C', 0.74, 0.78, 0.1, False),
              ('L', [(0.35, 0.45), (0.65, 0.27)]), ('L', [(0.35, 0.55), (0.65, 0.73)])],
    'close': [('L', [(0.2, 0.2), (0.8, 0.8)]), ('L', [(0.8, 0.2), (0.2, 0.8)])],
    'a_left': [('L', [(0.12, 0.08), (0.12, 0.92)]), ('R', 0.2, 0.2, 0.66, 0.2, True), ('R', 0.2, 0.58, 0.4, 0.2, True)],
    'a_hcenter': [('L', [(0.5, 0.08), (0.5, 0.92)]), ('R', 0.17, 0.2, 0.66, 0.2, True), ('R', 0.3, 0.58, 0.4, 0.2, True)],
    'a_right': [('L', [(0.88, 0.08), (0.88, 0.92)]), ('R', 0.14, 0.2, 0.66, 0.2, True), ('R', 0.4, 0.58, 0.4, 0.2, True)],
    'a_top': [('L', [(0.08, 0.12), (0.92, 0.12)]), ('R', 0.2, 0.2, 0.2, 0.66, True), ('R', 0.58, 0.2, 0.2, 0.4, True)],
    'a_vcenter': [('L', [(0.08, 0.5), (0.92, 0.5)]), ('R', 0.2, 0.17, 0.2, 0.66, True), ('R', 0.58, 0.3, 0.2, 0.4, True)],
    'a_bottom': [('L', [(0.08, 0.88), (0.92, 0.88)]), ('R', 0.2, 0.14, 0.2, 0.66, True), ('R', 0.58, 0.4, 0.2, 0.4, True)],
    'a_center_plate': [('RR', 0.06, 0.16, 0.88, 0.68, 0.08, False), ('R', 0.36, 0.38, 0.28, 0.24, True),
                       ('L', [(0.5, 0.16), (0.5, 0.3)]), ('L', [(0.5, 0.7), (0.5, 0.84)])],
    'bold': [('T', 'B', 0.5, 0.52, 0.8)],
    'pdf': [('P', [(0.2, 0.08), (0.62, 0.08), (0.8, 0.26), (0.8, 0.92), (0.2, 0.92)], False),
            ('T', 'PDF', 0.5, 0.6, 0.26)],
    'png': [('R', 0.1, 0.18, 0.8, 0.64, False), ('T', 'PNG', 0.5, 0.52, 0.28)],
    'svg': [('R', 0.1, 0.18, 0.8, 0.64, False), ('T', 'SVG', 0.5, 0.52, 0.28)],
    'tile': [('R', 0.18, 0.06, 0.64, 0.88, False)] +
            [('R', x, y, 0.22, 0.18, True) for x in (0.25, 0.53) for y in (0.14, 0.38, 0.62)],
}


def make_icons(out_dir, px=96):
    os.makedirs(out_dir, exist_ok=True)
    for name, prims in ICONS.items():
        symbols.SYMBOLS['_icon'] = dict(id='_icon', cat='x', en='', fa='', prims=prims,
                                        aspect=1.0, stext=None)
        im = raster.symbol_icon('_icon', px, color='#ffffff', pad=0.06)
        im.save(os.path.join(out_dir, name + '.png'))
    symbols.SYMBOLS.pop('_icon', None)


def app_icon(path, size=512):
    ss = 2
    S = size * ss
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.2), fill='#1565C0')
    m = S * 0.14
    d.rounded_rectangle([m, S * 0.24, S - m, S * 0.76], radius=int(S * 0.05), fill='#ECEFF1',
                        outline='#0D2B57', width=int(S * 0.022))
    for x in (m + S * 0.07, S - m - S * 0.07):
        for y in (S * 0.31, S * 0.69):
            r = S * 0.028
            d.ellipse([x - r, y - r, x + r, y + r], outline='#0D2B57', width=int(S * 0.012))
    bolt = symbols._bolt(0.33, 0.28, 0.44)
    d.polygon([(x * S, y * S) for x, y in bolt], fill='#FFC400', outline='#0D2B57')
    d.line([(x * S, y * S) for x, y in bolt + [bolt[0]]], fill='#0D2B57', width=int(S * 0.012))
    im = im.resize((size, size), Image.LANCZOS)
    im.save(path)
    return im


def presplash(path, icon):
    W, H = 1080, 1080
    im = Image.new('RGB', (W, H), '#ffffff')
    ic = icon.resize((420, 420), Image.LANCZOS)
    im.paste(ic, ((W - 420) // 2, 200), ic)
    d = ImageDraw.Draw(im)
    d.text((W / 2, 720), shape('طراح پلاک ترانس'), font=raster.get_font(True, 74),
           fill='#0D2B57', anchor='mm')
    d.text((W / 2, 820), 'Trans Plate Designer', font=raster.get_font(False, 52),
           fill='#37474F', anchor='mm')
    im.save(path)


if __name__ == '__main__':
    make_icons(os.path.join(ROOT, 'assets', 'icons'))
    ic = app_icon(os.path.join(ROOT, 'assets', 'icon.png'))
    presplash(os.path.join(ROOT, 'assets', 'presplash.png'), ic)
    # Windows .ico for PyInstaller
    ic.save(os.path.join(ROOT, 'assets', 'icon.ico'), sizes=[(16, 16), (32, 32), (48, 48),
                                                            (64, 64), (128, 128), (256, 256)])
    print('icons written')
