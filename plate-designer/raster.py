"""Pillow raster backend: plate export images, editor view, symbol icons.

Pure Python + Pillow (works on desktop and on Android through the
python-for-android Pillow recipe).  The editor shows exactly what this
module draws, so the screen and the exported PNG/PDF always match.
"""
import base64
import io
import math

from PIL import Image, ImageDraw, ImageFont

import render
from model import el_center, rotate_pt
from symbols import SYMBOLS
from textshape import shape_line

_FONT_CACHE = {}
_BASIC = (ImageFont.Layout.BASIC if hasattr(ImageFont, 'Layout')
          else getattr(ImageFont, 'LAYOUT_BASIC', 0))
_IMG_CACHE = {}


def get_font(bold, px):
    px = max(1, int(round(px)))
    key = (bool(bold), px)
    f = _FONT_CACHE.get(key)
    if f is None:
        # BASIC layout: we shape/reorder Persian ourselves (arabic_reshaper +
        # python-bidi).  With libraqm Pillow would reorder a second time.
        f = ImageFont.truetype(render.FONT_BOLD if bold else render.FONT_REGULAR, px,
                               layout_engine=_BASIC)
        if len(_FONT_CACHE) > 200:
            _FONT_CACHE.clear()
        _FONT_CACHE[key] = f
    return f


def _decode_image(data):
    key = (len(data), hash(data))
    im = _IMG_CACHE.get(key)
    if im is None:
        im = Image.open(io.BytesIO(base64.b64decode(data))).convert('RGBA')
        if len(_IMG_CACHE) > 20:
            _IMG_CACHE.clear()
        _IMG_CACHE[key] = im
    return im


class Painter:
    """Draws mm-unit ops onto a Pillow image with uniform scale s (px/mm)."""

    def __init__(self, img, s, ox=0.0, oy=0.0):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.s = s
        self.ox = ox
        self.oy = oy

    def P(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def wpx(self, sw):
        return max(1, int(round(sw * self.s)))

    def draw(self, ops):
        for op in ops:
            k = op['k']
            if k == 'path':
                self.path(op)
            elif k == 'circle':
                self.circle(op)
            elif k == 'text':
                self.text(op)
            elif k == 'image':
                self.image(op)

    def path(self, op):
        pts = [self.P(x, y) for x, y in op['pts']]
        if len(pts) < 2:
            return
        if op.get('fill') and op['closed'] and len(pts) >= 3:
            self.d.polygon(pts, fill=op['fill'])
        st = op.get('stroke')
        if st and op.get('sw', 0) > 0:
            w = self.wpx(op['sw'])
            line = pts + [pts[0]] if op['closed'] else pts
            self.d.line(line, fill=st, width=w, joint='curve' if w > 2 else None)
            if not op['closed'] and w >= 3:
                r = w / 2.0
                for (px, py) in (pts[0], pts[-1]):
                    self.d.ellipse([px - r, py - r, px + r, py + r], fill=st)

    def circle(self, op):
        cx, cy = self.P(op['cx'], op['cy'])
        r = op['r'] * self.s
        if op.get('fill'):
            self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=op['fill'])
        st = op.get('stroke')
        if st and op.get('sw', 0) > 0:
            w = self.wpx(op['sw'])
            R = r + w / 2.0
            self.d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=st, width=w)

    def text(self, op):
        size_px = op['size'] * self.s
        if size_px < 2 or not op['text']:
            return
        font = get_font(op.get('bold'), size_px)
        lines = op['text'].split('\n')
        bls = render.text_baselines(op['y'], op['h'], op['size'], len(lines))
        align = op.get('align', 'center')
        if align == 'left':
            ax, anchor = op['x'], 'ls'
        elif align == 'right':
            ax, anchor = op['x'] + op['w'], 'rs'
        else:
            ax, anchor = op['x'] + op['w'] / 2.0, 'ms'
        rot = op.get('rot') or 0
        color = op.get('color') or '#000000'
        if not rot:
            for line, bl in zip(lines, bls):
                if line:
                    self.d.text(self.P(ax, bl), shape_line(line), font=font,
                                fill=color, anchor=anchor)
            return
        # rotated: draw on a square layer centred on the pivot, rotate, paste
        pvx, pvy = self.P(op['px'], op['py'])
        corners = [self.P(op['x'], op['y']), self.P(op['x'] + op['w'], op['y'] + op['h'])]
        R = 0
        for cx, cy in corners + [self.P(op['x'], op['y'] + op['h']),
                                 self.P(op['x'] + op['w'], op['y'])]:
            R = max(R, math.hypot(cx - pvx, cy - pvy))
        R = int(R + size_px * 2 + 4)
        layer = Image.new('RGBA', (2 * R, 2 * R), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for line, bl in zip(lines, bls):
            if line:
                px, py = self.P(ax, bl)
                ld.text((px - pvx + R, py - pvy + R), shape_line(line), font=font,
                        fill=color, anchor=anchor)
        layer = layer.rotate(-rot, resample=Image.BICUBIC)
        self.img.paste(layer, (int(round(pvx - R)), int(round(pvy - R))), layer)

    def image(self, op):
        try:
            src = _decode_image(op['data'])
        except Exception:
            return
        w = max(1, int(round(op['w'] * self.s)))
        h = max(1, int(round(op['h'] * self.s)))
        if w * h > 60_000_000:
            return
        im = src.resize((w, h), Image.LANCZOS)
        cx, cy = self.P(op['x'] + op['w'] / 2, op['y'] + op['h'] / 2)
        if op.get('rot'):
            im = im.rotate(-op['rot'], resample=Image.BICUBIC, expand=True)
        self.img.paste(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))), im)


# ---------------------------------------------------------------------------
def render_plate(doc, dpi=600, extra_vars=None, corr=(1.0, 1.0), background='#ffffff'):
    """Render the plate at 1:1 physical size for the given dpi.

    Pixel size = round(mm / 25.4 * dpi * correction)."""
    s = dpi / 25.4
    W = max(1, int(round(doc.w * s)))
    H = max(1, int(round(doc.h * s)))
    img = Image.new('RGB', (W, H), background)
    p = Painter(img, s)
    p.path({'pts': render.plate_outline(doc), 'closed': True, 'fill': doc.bg,
            'stroke': None, 'sw': 0})
    p.draw(render.compile_doc(doc, extra_vars))
    cx, cy = corr
    if abs(cx - 1) > 1e-6 or abs(cy - 1) > 1e-6:
        img = img.resize((max(1, int(round(doc.w * s * cx))),
                          max(1, int(round(doc.h * s * cy)))), Image.LANCZOS)
    return img


def symbol_icon(sym_id, px=96, color='#1b1b1b', bg=(255, 255, 255, 0), pad=0.12):
    """Small preview image of a library symbol."""
    sym = SYMBOLS[sym_id]
    ss = 3
    size = px * ss
    img = Image.new('RGBA', (size, size), bg)
    a = sym.get('aspect', 1.0)
    inner = 1 - 2 * pad
    if a >= 1:
        w, h = inner, inner / a
    else:
        w, h = inner * a, inner
    e = {'type': 'symbol', 'sym': sym_id, 'x': (1 - w) / 2, 'y': (1 - h) / 2, 'w': w,
         'h': h, 'rot': 0, 'stroke': color, 'sw': 0.045 * min(w, h) / 0.76,
         'stext': None}
    Painter(img, size).draw(render.compile_symbol(e))
    return img.resize((px, px), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Editor view
SEL_COLOR = '#1e88e5'
GRID_MM = (206, 228, 242)
GRID_5 = (170, 205, 230)
GRID_CM = (120, 170, 210)


def handle_positions(e, zoom, ox, oy, ui=1.0):
    """Handles of a selected element in view px: list of (name, x, y)."""
    def V(x, y):
        return ox + x * zoom, oy + y * zoom
    if e['type'] == 'line':
        return [('p1',) + V(e['x'], e['y']), ('p2',) + V(e['x'] + e['w'], e['y'] + e['h'])]
    x, y, w, h = e['x'], e['y'], e['w'], e['h']
    cx, cy = el_center(e)
    rot = e.get('rot', 0) or 0
    pts = {'nw': (x, y), 'n': (x + w / 2, y), 'ne': (x + w, y), 'e': (x + w, y + h / 2),
           'se': (x + w, y + h), 's': (x + w / 2, y + h), 'sw': (x, y + h),
           'w': (x, y + h / 2)}
    out = []
    small = w * zoom < 40 * ui or h * zoom < 40 * ui
    for name, (px, py) in pts.items():
        if small and len(name) == 1:
            continue
        if e['type'] == 'hole' and len(name) == 1:
            continue
        rx, ry = rotate_pt(px, py, cx, cy, rot)
        out.append((name,) + V(rx, ry))
    # rotation handle above the top edge
    off = 30 * ui / zoom
    rx, ry = rotate_pt(x + w / 2, y - off, cx, cy, rot)
    if e['type'] != 'hole':
        out.append(('rot',) + V(rx, ry))
    return out


def _nice_steps(zoom):
    """(minor, mid, major, label) tick steps in mm for the ruler."""
    if zoom >= 4:
        return 1, 5, 10, 10
    if zoom >= 1.6:
        return 2, 10, 10, 20
    if zoom >= 0.7:
        return 5, 10, 50, 50
    return 10, 50, 100, 100


def render_view(doc, W, H, zoom, ox, oy, sel=(), grid=True, ruler=24, ss=1,
                ui=1.0, show_handles=True, workspace='#d5d9df'):
    """Render the editor view.  zoom = px per mm; (ox, oy) = view px of plate origin."""
    W, H = max(1, int(W)), max(1, int(H))
    big = Image.new('RGB', (W * ss, H * ss), workspace)
    p = Painter(big, zoom * ss, ox * ss, oy * ss)
    d = p.d
    # shadow + plate
    sh = 3 * ss
    p.ox += sh
    p.oy += sh
    p.path({'pts': render.plate_outline(doc), 'closed': True, 'fill': '#aab0b8',
            'stroke': None, 'sw': 0})
    p.ox -= sh
    p.oy -= sh
    p.path({'pts': render.plate_outline(doc), 'closed': True, 'fill': doc.bg,
            'stroke': None, 'sw': 0})
    # graph-paper grid
    if grid:
        x0, y0 = ox, oy
        x1, y1 = ox + doc.w * zoom, oy + doc.h * zoom
        steps = []
        if zoom >= 3.5:
            steps.append((1, GRID_MM))
        if zoom >= 1.2:
            steps.append((5, GRID_5))
        steps.append((10, GRID_CM))
        for step, col in steps:
            n = int(doc.w // step)
            for i in range(1, n + 1):
                mm = i * step
                if mm >= doc.w - 1e-6:
                    break
                if step < 10 and mm % 10 == 0:
                    continue
                if step == 1 and mm % 5 == 0 and zoom >= 1.2:
                    continue
                gx = int(round(x0 + mm * zoom)) * ss
                d.line([(gx, y0 * ss), (gx, y1 * ss)], fill=col, width=ss)
            n = int(doc.h // step)
            for i in range(1, n + 1):
                mm = i * step
                if mm >= doc.h - 1e-6:
                    break
                if step < 10 and mm % 10 == 0:
                    continue
                if step == 1 and mm % 5 == 0 and zoom >= 1.2:
                    continue
                gy = int(round(y0 + mm * zoom)) * ss
                d.line([(x0 * ss, gy), (x1 * ss, gy)], fill=col, width=ss)
    p.draw(render.compile_doc(doc))
    # plate edge
    p.path({'pts': render.plate_outline(doc), 'closed': True, 'fill': None,
            'stroke': '#5f6b78', 'sw': 1.0 / zoom})
    img = big.reduce(ss) if ss > 1 else big
    d = ImageDraw.Draw(img)

    # selection
    sel_els = [e for e in doc.elements if e['id'] in set(sel)]
    for e in sel_els:
        if e['type'] == 'line':
            pts = [(ox + e['x'] * zoom, oy + e['y'] * zoom),
                   (ox + (e['x'] + e['w']) * zoom, oy + (e['y'] + e['h']) * zoom)]
            d.line(pts, fill=SEL_COLOR, width=max(1, int(ui)))
        else:
            from model import element_corners
            cs = [(ox + x * zoom, oy + y * zoom) for x, y in element_corners(e)]
            d.line(cs + [cs[0]], fill=SEL_COLOR, width=max(1, int(1.5 * ui)))
    if show_handles and len(sel_els) == 1:
        e = sel_els[0]
        hs = handle_positions(e, zoom, ox, oy, ui)
        r = 6 * ui
        for name, hx, hy in hs:
            if name == 'rot':
                top = [hh for hh in hs if hh[0] == 'n']
                cx, cy = el_center(e)
                tx, ty = rotate_pt(e['x'] + e['w'] / 2, e['y'], cx, cy, e.get('rot', 0))
                d.line([(ox + tx * zoom, oy + ty * zoom), (hx, hy)], fill=SEL_COLOR,
                       width=max(1, int(ui)))
                d.ellipse([hx - r * 1.2, hy - r * 1.2, hx + r * 1.2, hy + r * 1.2],
                          fill='#ffffff', outline=SEL_COLOR, width=max(2, int(2 * ui)))
            else:
                d.rectangle([hx - r, hy - r, hx + r, hy + r], fill='#ffffff',
                            outline=SEL_COLOR, width=max(2, int(2 * ui)))

    # rulers
    if ruler:
        R = int(ruler)
        rb = '#f3f4f6'
        d.rectangle([0, 0, W, R], fill=rb)
        d.rectangle([0, 0, R, H], fill=rb)
        d.line([(0, R), (W, R)], fill='#9aa3ad')
        d.line([(R, 0), (R, H)], fill='#9aa3ad')
        font = get_font(False, max(8, R * 0.42))
        minor, mid, major, lab = _nice_steps(zoom)
        # selection extent bands
        if sel_els:
            b = doc.bbox([e['id'] for e in sel_els])
            if b:
                d.rectangle([max(R, ox + b[0] * zoom), 0, max(R, ox + b[2] * zoom), R],
                            fill='#cfe3f7')
                d.rectangle([0, max(R, oy + b[1] * zoom), R, max(R, oy + b[3] * zoom)],
                            fill='#cfe3f7')
        # top ruler
        mm_start = int(math.floor((R - ox) / zoom / minor)) * minor
        mm_end = int(math.ceil((W - ox) / zoom))
        mm = mm_start
        while mm <= mm_end:
            vx = ox + mm * zoom
            if vx >= R:
                if mm % major == 0:
                    L = R * 0.75
                elif mm % mid == 0:
                    L = R * 0.45
                else:
                    L = R * 0.25
                d.line([(vx, R - L), (vx, R)], fill='#4a5561' if mm % major == 0 else '#7b8794')
                if mm % lab == 0:
                    d.text((vx + 2, 1), str(mm), font=font, fill='#2f3a45', anchor='la')
            mm += minor
        mm_start = int(math.floor((R - oy) / zoom / minor)) * minor
        mm_end = int(math.ceil((H - oy) / zoom))
        mm = mm_start
        while mm <= mm_end:
            vy = oy + mm * zoom
            if vy >= R:
                if mm % major == 0:
                    L = R * 0.75
                elif mm % mid == 0:
                    L = R * 0.45
                else:
                    L = R * 0.25
                d.line([(R - L, vy), (R, vy)], fill='#4a5561' if mm % major == 0 else '#7b8794')
                if mm % lab == 0:
                    d.text((2, vy + 1), str(mm), font=font, fill='#2f3a45', anchor='la')
            mm += minor
        d.rectangle([0, 0, R, R], fill='#e3e6ea')
        d.text((R / 2, R / 2), 'mm', font=get_font(False, max(7, R * 0.36)),
               fill='#55606b', anchor='mm')
    return img
