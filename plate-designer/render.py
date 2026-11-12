"""Compile a Document into backend-neutral drawing ops (mm units).

Ops (dicts):
  {'k':'path','pts':[(x,y)..],'closed':bool,'stroke':c|None,'sw':mm,'fill':c|None}
  {'k':'circle','cx','cy','r','stroke','sw','fill'}
  {'k':'text','text','x','y','w','h','size','bold','color','align','rot','px','py'}
      box (x,y,w,h) is unrotated; the box is rotated by rot degrees about (px,py)
  {'k':'image','data'(b64 png),'x','y','w','h','rot'}

Backends: raster.py (Pillow: screen, PNG, PDF) and svgwriter.py.
"""
import math
import os

from model import el_center, rotate_pt
from symbols import SYMBOLS

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(HERE, 'assets', 'fonts', 'Vazirmatn-Regular.ttf')
FONT_BOLD = os.path.join(HERE, 'assets', 'fonts', 'Vazirmatn-Bold.ttf')

# Vazirmatn vertical metrics (fraction of em) used to place baselines the
# same way in every backend.
ASCENT = 0.74
DESCENT = 0.24
LINE_PITCH = 1.25


def arc_pts(cx, cy, rx, ry, a0, a1, n=None):
    if n is None:
        n = max(8, int(abs(a1 - a0) / 6))
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def ellipse_pts(cx, cy, rx, ry, n=72):
    return arc_pts(cx, cy, rx, ry, 0, 360, n)[:-1]


def rrect_pts(x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pts = []
    pts += arc_pts(x + w - r, y + r, r, r, -90, 0, 8)
    pts += arc_pts(x + w - r, y + h - r, r, r, 0, 90, 8)
    pts += arc_pts(x + r, y + h - r, r, r, 90, 180, 8)
    pts += arc_pts(x + r, y + r, r, r, 180, 270, 8)
    return pts


def _rot(pts, e):
    rot = e.get('rot', 0) or 0
    if not rot:
        return [(float(x), float(y)) for x, y in pts]
    cx, cy = el_center(e)
    return [rotate_pt(x, y, cx, cy, rot) for x, y in pts]


def _path(pts, closed, stroke, sw, fill=None):
    return {'k': 'path', 'pts': pts, 'closed': closed, 'stroke': stroke,
            'sw': sw, 'fill': fill}


def _text(e, text, x, y, w, h, size, bold, color, align):
    cx, cy = el_center(e)
    return {'k': 'text', 'text': text, 'x': x, 'y': y, 'w': w, 'h': h,
            'size': size, 'bold': bold, 'color': color, 'align': align,
            'rot': e.get('rot', 0) or 0, 'px': cx, 'py': cy}


def text_baselines(y, h, size, nlines):
    """Baselines (mm) for nlines of text vertically centred in box y..y+h."""
    block = (nlines - 1) * size * LINE_PITCH + size * (ASCENT + DESCENT)
    top = y + (h - block) / 2.0
    return [top + size * ASCENT + i * size * LINE_PITCH for i in range(nlines)]


def compile_element(e, doc, extra_vars=None):
    t = e['type']
    ops = []
    st = e.get('stroke')
    sw = float(e.get('sw', 0.3) or 0)
    fill = e.get('fill')
    x, y, w, h = e['x'], e['y'], e['w'], e['h']

    if t == 'text':
        txt = doc.resolve(e.get('text', ''), extra_vars)
        if fill:
            ops.append(_path(_rot(rrect_pts(x, y, w, h, 0), e), True, None, 0, fill))
        ops.append(_text(e, txt, x, y, w, h, e.get('font_mm', 4), e.get('bold'),
                         e.get('color', '#000000'), e.get('align', 'center')))
    elif t == 'line':
        ops.append(_path([(x, y), (x + w, y + h)], False, st or '#000000', sw))
    elif t in ('rect', 'frame'):
        r = e.get('radius', 0) or 0
        ops.append(_path(_rot(rrect_pts(x, y, w, h, r), e), True, st if st else None,
                         sw, fill))
        if t == 'frame' and e.get('double'):
            g = (e.get('gap', 1.0) or 1.0) + sw
            ops.append(_path(_rot(rrect_pts(x + g, y + g, w - 2 * g, h - 2 * g,
                                            max(0, r - g)), e), True, st, sw * 0.6))
    elif t == 'ellipse':
        if abs(w - h) < 1e-6:
            ops.append({'k': 'circle', 'cx': x + w / 2, 'cy': y + h / 2, 'r': w / 2,
                        'stroke': st, 'sw': sw, 'fill': fill})
        else:
            ops.append(_path(_rot(ellipse_pts(x + w / 2, y + h / 2, w / 2, h / 2), e),
                             True, st, sw, fill))
    elif t == 'hole':
        cx, cy, r = x + w / 2, y + h / 2, w / 2
        ops.append({'k': 'circle', 'cx': cx, 'cy': cy, 'r': r, 'stroke': st or '#000000',
                    'sw': sw, 'fill': fill})
        if e.get('cross', True):
            c = r * 0.6
            ops.append(_path([(cx - c, cy), (cx + c, cy)], False, st or '#000000', sw * 0.7))
            ops.append(_path([(cx, cy - c), (cx, cy + c)], False, st or '#000000', sw * 0.7))
    elif t == 'table':
        ops += compile_table(e, doc, extra_vars)
    elif t == 'symbol':
        ops += compile_symbol(e)
    elif t == 'image':
        if e.get('data'):
            ops.append({'k': 'image', 'data': e['data'], 'x': x, 'y': y, 'w': w,
                        'h': h, 'rot': e.get('rot', 0) or 0})
        else:
            ops.append(_path(_rot(rrect_pts(x, y, w, h, 0), e), True, '#999999', 0.2))
        if st:
            ops.append(_path(_rot(rrect_pts(x, y, w, h, 0), e), True, st, sw))
    return ops


def col_edges(e):
    cols = int(e.get('cols', 1))
    cr = e.get('col_ratios') or [1.0] * cols
    tot = float(sum(cr)) or 1.0
    xs = [e['x']]
    for r in cr:
        xs.append(xs[-1] + e['w'] * r / tot)
    return xs


def compile_table(e, doc, extra_vars=None):
    ops = []
    rows, cols = int(e.get('rows', 1)), int(e.get('cols', 1))
    x, y, w, h = e['x'], e['y'], e['w'], e['h']
    st = e.get('stroke')
    sw = float(e.get('sw', 0.25) or 0)
    rh = h / rows
    xs = col_edges(e)
    if e.get('fill'):
        ops.append(_path(_rot(rrect_pts(x, y, w, h, 0), e), True, None, 0, e['fill']))
    if e.get('header') and e.get('header_fill'):
        ops.append(_path(_rot(rrect_pts(x, y, w, rh, 0), e), True, None, 0,
                         e['header_fill']))
    cells = e.get('cells') or []
    for r in range(rows):
        for c in range(cols):
            try:
                txt = cells[r][c]
            except (IndexError, TypeError):
                txt = ''
            if not txt:
                continue
            txt = doc.resolve(txt, extra_vars)
            bold = bool(e.get('bold')) or (e.get('header') and r == 0)
            pad = min(1.0, (xs[c + 1] - xs[c]) * 0.08)
            ops.append(_text(e, txt, xs[c] + pad, y + r * rh, xs[c + 1] - xs[c] - 2 * pad,
                             rh, e.get('font_mm', 2.8), bold, e.get('color', '#000000'),
                             e.get('align', 'center')))
    if st and sw > 0:
        ops.append(_path(_rot(rrect_pts(x, y, w, h, 0), e), True, st, sw))
        for r in range(1, rows):
            yy = y + r * rh
            ops.append(_path(_rot([(x, yy), (x + w, yy)], e), False, st, sw))
        for c in range(1, cols):
            ops.append(_path(_rot([(xs[c], y), (xs[c], y + h)], e), False, st, sw))
    return ops


def compile_symbol(e):
    sym = SYMBOLS.get(e.get('sym'))
    x, y, w, h = e['x'], e['y'], e['w'], e['h']
    col = e.get('stroke') or '#000000'
    sw = float(e.get('sw', 0.4) or 0.4)
    if sym is None:
        return [_path(_rot(rrect_pts(x, y, w, h, 0), e), True, '#ff0000', sw)]
    ops = []

    def P(px, py):
        return (x + px * w, y + py * h)

    def fillspec(f):
        if f is True:
            return col
        if isinstance(f, str):
            return f
        return None

    for prim in sym['prims']:
        opts = prim[-1] if isinstance(prim[-1], dict) else {}
        if opts:
            prim = prim[:-1]
        psw = sw * opts.get('wf', 1.0)
        k = prim[0]
        if k == 'L':
            ops.append(_path(_rot([P(*p) for p in prim[1]], e), False, col, psw))
        elif k == 'P':
            f = fillspec(prim[2])
            ops.append(_path(_rot([P(*p) for p in prim[1]], e), True,
                             None if f else col, psw, f))
        elif k in ('C', 'E'):
            if k == 'C':
                cx, cy, rx, ry, f = prim[1], prim[2], prim[3], prim[3], prim[4]
            else:
                cx, cy, rx, ry, f = prim[1:6]
            f = fillspec(f)
            ccx, ccy = P(cx, cy)
            rxm, rym = rx * w, ry * h
            if abs(rxm - rym) < 1e-6:
                c2 = _rot([(ccx, ccy)], e)[0]
                ops.append({'k': 'circle', 'cx': c2[0], 'cy': c2[1], 'r': rxm,
                            'stroke': None if f else col, 'sw': psw, 'fill': f})
            else:
                ops.append(_path(_rot(ellipse_pts(ccx, ccy, rxm, rym), e), True,
                                 None if f else col, psw, f))
        elif k == 'A':
            cx, cy, r, a0, a1 = prim[1:6]
            ccx, ccy = P(cx, cy)
            ops.append(_path(_rot(arc_pts(ccx, ccy, r * w, r * h, a0, a1), e), False,
                             col, psw))
        elif k in ('R', 'RR'):
            if k == 'R':
                rx_, ry_, rw, rh, f = prim[1:6]
                rr = 0
            else:
                rx_, ry_, rw, rh, rr, f = prim[1:7]
            f = fillspec(f)
            pts = rrect_pts(x + rx_ * w, y + ry_ * h, rw * w, rh * h, rr * min(w, h))
            ops.append(_path(_rot(pts, e), True, None if f else col, psw, f))
        elif k == 'T':
            txt, cx, cy, size = prim[1:5]
            if '{t}' in txt:
                txt = txt.replace('{t}', e.get('stext') or sym.get('stext') or '')
            size_mm = size * h
            bw = w * 1.6
            ccx, ccy = P(cx, cy)
            # centre the glyph block (cap height) on cy
            box_h = size_mm * (ASCENT + DESCENT)
            ops.append(_text(e, txt, ccx - bw / 2, ccy - box_h / 2 + size_mm * 0.08,
                             bw, box_h, size_mm, True, col, 'center'))
    return ops


def compile_doc(doc, extra_vars=None):
    ops = []
    for e in doc.elements:
        ops += compile_element(e, doc, extra_vars)
    return ops


def plate_outline(doc):
    return rrect_pts(0, 0, doc.w, doc.h, doc.radius)
