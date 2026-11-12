"""Industrial / electrical symbol library (pure Python).

Every symbol is built from primitives in a normalised box 0..1 x 0..1
(x right, y DOWN).  The same primitives are used by the raster renderer
(screen + PNG + PDF) and by the SVG writer, so they look identical
everywhere.  These are generic drawings made for this app; no trademarked
logo is reproduced.

Primitive tuples:
  ('L', pts)                    open polyline
  ('P', pts, fill)              closed polygon; fill: False | True(stroke colour) | '#rrggbb'
  ('C', cx, cy, r, fill)        circle
  ('E', cx, cy, rx, ry, fill)   ellipse
  ('A', cx, cy, r, a0, a1)      arc, degrees, 0 = +x, increasing clockwise (y down)
  ('R', x, y, w, h, fill)       rectangle
  ('RR', x, y, w, h, r, fill)   rounded rectangle
  ('T', text, cx, cy, size)     bold text centred on (cx, cy); size = em height in box units.
                                '{t}' is replaced with the element's editable text.
Optional trailing dict on any primitive: {'wf': width factor}
"""
import math

CATEGORIES = [
    ('earth', 'Earth & protection', 'ارت و حفاظت'),
    ('conn', 'Connections & phases', 'اتصال و فاز'),
    ('supply', 'Current & supply', 'جریان و تغذیه'),
    ('comp', 'Components', 'قطعات'),
    ('machine', 'Machines & meters', 'ماشین و اندازه‌گیر'),
    ('safety', 'Safety & warning', 'ایمنی و هشدار'),
    ('info', 'Info & compliance', 'اطلاعات و انطباق'),
]


def _sine(x0, x1, cy, amp, periods=1.0, n=48):
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + (x1 - x0) * t,
                    cy - amp * math.sin(2 * math.pi * periods * t)))
    return pts


def _polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _earth_lines(cx, top, y0, widths, step):
    prims = [('L', [(cx, top), (cx, y0)])]
    for i, w in enumerate(widths):
        y = y0 + i * step
        prims.append(('L', [(cx - w / 2, y), (cx + w / 2, y)]))
    return prims


def _vcoil(cx, y0, y1, turns, side):
    """Vertical coil of semicircle arcs; side=-1 bulges left, +1 right."""
    prims = []
    r = (y1 - y0) / (2 * turns)
    for i in range(turns):
        cy = y0 + r * (2 * i + 1)
        if side < 0:
            prims.append(('A', cx, cy, r, 90, 270))
        else:
            prims.append(('A', cx, cy, r, -90, 90))
    return prims


def _hcoil(x0, x1, cy, turns):
    prims = []
    r = (x1 - x0) / (2 * turns)
    for i in range(turns):
        cx = x0 + r * (2 * i + 1)
        prims.append(('A', cx, cy, r, 180, 360))
    return prims


def _bolt(x, y, s):
    """Lightning bolt polygon in a box at (x, y) size s."""
    pts = [(0.55, 0.0), (0.18, 0.55), (0.45, 0.55), (0.30, 1.0),
           (0.82, 0.40), (0.55, 0.40), (0.72, 0.0)]
    return [(x + px * s, y + py * s) for px, py in pts]


def _arrow_head(tip, direction_deg, length, half_angle=25):
    a1 = direction_deg + 180 - half_angle
    a2 = direction_deg + 180 + half_angle
    return [tip, _polar(tip[0], tip[1], length, a1),
            _polar(tip[0], tip[1], length, a2)]


def _zigzag():
    prims = []
    c = (0.5, 0.55)
    for base in (270, 30, 150):
        p1 = _polar(c[0], c[1], 0.24, base)
        p2 = _polar(p1[0], p1[1], 0.22, base + 60)
        prims.append(('L', [c, p1, p2]))
    prims.append(('C', c[0], c[1], 0.035, True))
    return prims


def _fan():
    prims = [('C', 0.5, 0.5, 0.46, False), ('C', 0.5, 0.5, 0.07, True)]
    for k in range(3):
        a0 = k * 120 - 90
        pts = [_polar(0.5, 0.5, 0.08, a0 - 25)]
        for j in range(9):
            t = j / 8
            r = 0.08 + 0.32 * t
            pts.append(_polar(0.5, 0.5, r, a0 - 25 + 35 * t))
        for j in range(9):
            t = 1 - j / 8
            r = 0.08 + 0.32 * t
            pts.append(_polar(0.5, 0.5, r, a0 + 25 * t))
        prims.append(('P', pts, True))
    return prims


def _phase_arrow():
    prims = []
    pts = [_polar(0.5, 0.5, 0.36, a) for a in range(150, 391, 8)]
    prims.append(('L', pts))
    end = pts[-1]
    prims.append(('P', _arrow_head(end, 30 + 90, 0.18), True))
    prims.append(('C', 0.5, 0.5, 0.05, True))
    return prims


def _weee():
    return [
        ('P', [(0.30, 0.25), (0.70, 0.25), (0.65, 0.78), (0.35, 0.78)], False),
        ('L', [(0.24, 0.20), (0.76, 0.20)]),
        ('L', [(0.43, 0.20), (0.43, 0.14), (0.57, 0.14), (0.57, 0.20)]),
        ('C', 0.40, 0.83, 0.04, False),
        ('C', 0.60, 0.83, 0.04, False),
        ('L', [(0.16, 0.10), (0.84, 0.88)]),
        ('L', [(0.84, 0.10), (0.16, 0.88)]),
        ('R', 0.22, 0.92, 0.56, 0.06, True),
    ]


def _manual():
    return [
        ('P', [(0.5, 0.30), (0.12, 0.22), (0.12, 0.80), (0.5, 0.88)], False),
        ('P', [(0.5, 0.30), (0.88, 0.22), (0.88, 0.80), (0.5, 0.88)], False),
        ('L', [(0.20, 0.40), (0.42, 0.44)]),
        ('L', [(0.20, 0.52), (0.42, 0.56)]),
        ('L', [(0.20, 0.64), (0.42, 0.68)]),
        ('C', 0.69, 0.38, 0.035, True),
        ('L', [(0.69, 0.47), (0.69, 0.70)], {'wf': 1.6}),
    ]


def _thermal():
    return [
        ('L', [(0.42, 0.62), (0.42, 0.14)]),
        ('A', 0.5, 0.14, 0.08, 180, 360),
        ('L', [(0.58, 0.14), (0.58, 0.62)]),
        ('C', 0.5, 0.75, 0.15, True),
        ('L', [(0.5, 0.30), (0.5, 0.70)], {'wf': 2.0}),
        ('L', [(0.62, 0.25), (0.72, 0.25)]),
        ('L', [(0.62, 0.38), (0.72, 0.38)]),
        ('L', [(0.62, 0.51), (0.72, 0.51)]),
        ('T', 't°', 0.20, 0.30, 0.26),
    ]


def _regulator():
    return [
        ('R', 0.1, 0.1, 0.8, 0.8, False),
        ('L', [(0.1, 0.9), (0.9, 0.1)]),
        ('L', _sine(0.18, 0.46, 0.30, 0.07)),
        ('L', _sine(0.54, 0.82, 0.70, 0.07)),
    ]


S = {}


def _add(sid, cat, en, fa, prims, aspect=1.0, stext=None):
    S[sid] = dict(id=sid, cat=cat, en=en, fa=fa, prims=prims,
                  aspect=aspect, stext=stext)


# ---- earth & protection -------------------------------------------------
_add('earth', 'earth', 'Earth / ground', 'ارت (زمین)',
     _earth_lines(0.5, 0.08, 0.50, [0.70, 0.46, 0.22], 0.15))
_add('protective_earth', 'earth', 'Protective earth (PE)', 'ارت حفاظتی',
     [('C', 0.5, 0.5, 0.45, False)] +
     _earth_lines(0.5, 0.17, 0.48, [0.50, 0.33, 0.16], 0.12))
_add('chassis', 'earth', 'Chassis / frame', 'اتصال بدنه',
     [('L', [(0.5, 0.12), (0.5, 0.50)]), ('L', [(0.12, 0.50), (0.88, 0.50)]),
      ('L', [(0.22, 0.50), (0.10, 0.74)]), ('L', [(0.50, 0.50), (0.38, 0.74)]),
      ('L', [(0.78, 0.50), (0.66, 0.74)])])
_add('functional_earth', 'earth', 'Functional earth', 'ارت عملیاتی',
     _earth_lines(0.5, 0.06, 0.40, [0.50, 0.32, 0.14], 0.12) +
     [('A', 0.5, 0.40, 0.40, 0, 180)])
_add('class1', 'earth', 'Class I', 'کلاس I',
     [('C', 0.5, 0.42, 0.34, False)] +
     _earth_lines(0.5, 0.17, 0.40, [0.36, 0.24, 0.12], 0.09) +
     [('T', 'CLASS I', 0.5, 0.90, 0.17)])
_add('class2', 'earth', 'Double insulation (Class II)', 'عایق دوبل (کلاس II)',
     [('R', 0.08, 0.08, 0.84, 0.84, False), ('R', 0.28, 0.28, 0.44, 0.44, False)])

# ---- connections & phases -----------------------------------------------
_add('star', 'conn', 'Star (Y) connection', 'اتصال ستاره (Y)',
     [('L', [(0.5, 0.55), _polar(0.5, 0.55, 0.45, 270)]),
      ('L', [(0.5, 0.55), _polar(0.5, 0.55, 0.45, 30)]),
      ('L', [(0.5, 0.55), _polar(0.5, 0.55, 0.45, 150)]),
      ('C', 0.5, 0.55, 0.04, True)])
_add('delta', 'conn', 'Delta (D) connection', 'اتصال مثلث (D)',
     [('P', [(0.5, 0.10), (0.93, 0.86), (0.07, 0.86)], False)])
_add('zigzag', 'conn', 'Zig-zag (Z) connection', 'اتصال زیگزاگ (Z)', _zigzag())
_add('phase1', 'conn', 'Single phase', 'تک‌فاز',
     [('T', '1', 0.27, 0.52, 0.62), ('L', _sine(0.45, 0.92, 0.5, 0.13))])
_add('phase3', 'conn', 'Three phase', 'سه‌فاز',
     [('T', '3', 0.27, 0.52, 0.62), ('L', _sine(0.45, 0.92, 0.5, 0.13))])
for _lab in ('L1', 'L2', 'L3', 'N', 'PE'):
    _add('label_' + _lab.lower(), 'conn', 'Terminal %s' % _lab, 'ترمینال %s' % _lab,
         [('T', _lab, 0.5, 0.5, 0.62 if len(_lab) > 1 else 0.75)])
_add('phase_arrow', 'conn', 'Phase sequence / angle', 'توالی فاز / زاویه', _phase_arrow())

# ---- current & supply ---------------------------------------------------
_add('ac', 'supply', 'AC (~)', 'جریان متناوب (AC)', [('L', _sine(0.08, 0.92, 0.5, 0.2))])
_add('dc', 'supply', 'DC', 'جریان مستقیم (DC)',
     [('L', [(0.08, 0.40), (0.92, 0.40)]),
      ('L', [(0.08, 0.60), (0.30, 0.60)]), ('L', [(0.39, 0.60), (0.61, 0.60)]),
      ('L', [(0.70, 0.60), (0.92, 0.60)])])
_add('acdc', 'supply', 'AC/DC', 'AC/DC',
     [('L', _sine(0.08, 0.92, 0.30, 0.13)),
      ('L', [(0.08, 0.60), (0.92, 0.60)]),
      ('L', [(0.08, 0.78), (0.30, 0.78)]), ('L', [(0.39, 0.78), (0.61, 0.78)]),
      ('L', [(0.70, 0.78), (0.92, 0.78)])])
_add('hz', 'supply', 'Frequency (Hz)', 'فرکانس (Hz)',
     [('T', '{t}', 0.5, 0.36, 0.40), ('L', _sine(0.15, 0.85, 0.78, 0.10))],
     aspect=1.2, stext='50Hz')
_add('input', 'supply', 'Input', 'ورودی',
     [('L', [(0.06, 0.5), (0.70, 0.5)]),
      ('P', _arrow_head((0.78, 0.5), 0, 0.22), True),
      ('L', [(0.86, 0.15), (0.86, 0.85)], {'wf': 1.8})])
_add('output', 'supply', 'Output', 'خروجی',
     [('L', [(0.14, 0.15), (0.14, 0.85)], {'wf': 1.8}),
      ('L', [(0.22, 0.5), (0.86, 0.5)]),
      ('P', _arrow_head((0.94, 0.5), 0, 0.22), True)])
_add('regulator', 'supply', 'AC regulator / stabilizer', 'تثبیت‌کننده ولتاژ', _regulator())

# ---- components ---------------------------------------------------------
_add('transformer', 'comp', 'Transformer (two coils)', 'ترانسفورماتور (دو سیم‌پیچ)',
     _vcoil(0.38, 0.18, 0.82, 4, -1) + _vcoil(0.62, 0.18, 0.82, 4, +1) +
     [('L', [(0.47, 0.12), (0.47, 0.88)]), ('L', [(0.53, 0.12), (0.53, 0.88)]),
      ('L', [(0.06, 0.18), (0.38, 0.18)]), ('L', [(0.06, 0.82), (0.38, 0.82)]),
      ('L', [(0.62, 0.18), (0.94, 0.18)]), ('L', [(0.62, 0.82), (0.94, 0.82)])])
_add('transformer_iec', 'comp', 'Transformer (IEC circles)', 'ترانسفورماتور (دایره‌ای)',
     [('C', 0.36, 0.5, 0.27, False), ('C', 0.64, 0.5, 0.27, False),
      ('L', [(0.0, 0.5), (0.09, 0.5)]), ('L', [(0.91, 0.5), (1.0, 0.5)])])
_add('autotransformer', 'comp', 'Autotransformer', 'اتوترانسفورماتور',
     _vcoil(0.45, 0.14, 0.86, 5, +1) +
     [('L', [(0.12, 0.14), (0.45, 0.14)]), ('L', [(0.12, 0.86), (0.45, 0.86)]),
      ('L', [(0.88, 0.80), (0.62, 0.36)]),
      ('P', _arrow_head((0.58, 0.30), 240, 0.13), True),
      ('L', [(0.88, 0.80), (0.94, 0.80)])])
_add('inductor', 'comp', 'Coil / inductor', 'سیم‌پیچ / سلف',
     [('L', [(0.02, 0.6), (0.14, 0.6)])] + _hcoil(0.14, 0.86, 0.6, 4) +
     [('L', [(0.86, 0.6), (0.98, 0.6)])])
_add('capacitor', 'comp', 'Capacitor', 'خازن',
     [('L', [(0.04, 0.5), (0.43, 0.5)]), ('L', [(0.57, 0.5), (0.96, 0.5)]),
      ('L', [(0.43, 0.18), (0.43, 0.82)], {'wf': 1.8}),
      ('L', [(0.57, 0.18), (0.57, 0.82)], {'wf': 1.8})])
_add('resistor', 'comp', 'Resistor', 'مقاومت',
     [('L', [(0.02, 0.5), (0.2, 0.5)]), ('R', 0.2, 0.36, 0.6, 0.28, False),
      ('L', [(0.8, 0.5), (0.98, 0.5)])])
_add('fuse', 'comp', 'Fuse', 'فیوز',
     [('R', 0.2, 0.36, 0.6, 0.28, False), ('L', [(0.02, 0.5), (0.98, 0.5)])])
_add('switch', 'comp', 'Switch', 'کلید',
     [('L', [(0.04, 0.6), (0.3, 0.6)]), ('L', [(0.3, 0.6), (0.72, 0.3)]),
      ('L', [(0.74, 0.6), (0.96, 0.6)]), ('C', 0.3, 0.6, 0.03, True)])
_add('breaker', 'comp', 'Circuit breaker', 'کلید مینیاتوری / بریکر',
     [('L', [(0.04, 0.6), (0.3, 0.6)]), ('L', [(0.3, 0.6), (0.72, 0.3)]),
      ('L', [(0.74, 0.6), (0.96, 0.6)]),
      ('L', [(0.68, 0.54), (0.80, 0.66)]), ('L', [(0.80, 0.54), (0.68, 0.66)])])
_add('contactor_coil', 'comp', 'Contactor / relay coil', 'بوبین کنتاکتور',
     [('L', [(0.5, 0.02), (0.5, 0.3)]), ('R', 0.22, 0.3, 0.56, 0.4, False),
      ('L', [(0.5, 0.7), (0.5, 0.98)]), ('L', [(0.22, 0.7), (0.78, 0.3)])])
_add('lamp', 'comp', 'Lamp / indicator', 'لامپ / چراغ',
     [('C', 0.5, 0.5, 0.36, False), ('L', [(0.245, 0.245), (0.755, 0.755)]),
      ('L', [(0.755, 0.245), (0.245, 0.755)]),
      ('L', [(0.0, 0.5), (0.14, 0.5)]), ('L', [(0.86, 0.5), (1.0, 0.5)])])

# ---- machines & meters --------------------------------------------------
for _sid, _letter, _en, _fa in (
        ('motor', 'M', 'Motor', 'موتور'), ('generator', 'G', 'Generator', 'ژنراتور'),
        ('voltmeter', 'V', 'Voltmeter', 'ولت‌متر'), ('ammeter', 'A', 'Ammeter', 'آمپرمتر')):
    _p = [('C', 0.5, 0.5, 0.44, False), ('T', _letter, 0.5, 0.47, 0.5)]
    if _sid in ('motor', 'generator'):
        _p.append(('L', _sine(0.38, 0.62, 0.76, 0.05)))
    _add(_sid, 'machine', _en, _fa, _p)
_add('fan', 'machine', 'Fan / cooling', 'فن / خنک‌کننده', _fan())
_add('thermal', 'machine', 'Thermal protection', 'حفاظت حرارتی', _thermal())

# ---- safety & warning ---------------------------------------------------
_add('hv_warning', 'safety', 'High voltage warning', 'هشدار ولتاژ بالا',
     [('P', [(0.5, 0.05), (0.97, 0.9), (0.03, 0.9)], '#FFD200'),
      ('P', [(0.5, 0.05), (0.97, 0.9), (0.03, 0.9)], False, {'wf': 1.6}),
      ('P', _bolt(0.30, 0.32, 0.46), True)], aspect=1.1)
_add('bolt', 'safety', 'Lightning bolt', 'صاعقه / برق', [('P', _bolt(0.1, 0.04, 0.9), True)])
_add('warning', 'safety', 'General warning (!)', 'هشدار عمومی',
     [('P', [(0.5, 0.05), (0.97, 0.9), (0.03, 0.9)], '#FFD200'),
      ('P', [(0.5, 0.05), (0.97, 0.9), (0.03, 0.9)], False, {'wf': 1.6}),
      ('L', [(0.5, 0.36), (0.5, 0.64)], {'wf': 2.6}),
      ('C', 0.5, 0.76, 0.045, True)], aspect=1.1)
_add('power', 'safety', 'Power on/off', 'روشن / خاموش',
     [('A', 0.5, 0.55, 0.36, -60, 240), ('L', [(0.5, 0.08), (0.5, 0.5)])])

# ---- info & compliance --------------------------------------------------
_add('ip_badge', 'info', 'IP rating badge', 'نشان درجه حفاظت IP',
     [('RR', 0.04, 0.12, 0.92, 0.76, 0.14, False), ('T', '{t}', 0.5, 0.5, 0.42)],
     aspect=1.6, stext='IP54')
_add('conformity', 'info', 'Conformity mark (generic)', 'نشان انطباق (عمومی)',
     [('RR', 0.06, 0.06, 0.88, 0.88, 0.12, False),
      ('L', [(0.25, 0.52), (0.43, 0.70), (0.76, 0.30)], {'wf': 2.0})])
_add('weee', 'info', 'WEEE crossed bin', 'سطل خط‌خورده (WEEE)', _weee(), aspect=0.8)
_add('manual', 'info', 'Read the manual', 'دفترچه راهنما را بخوانید', _manual())

SYMBOLS = S


def by_category():
    out = []
    for cid, en, fa in CATEGORIES:
        out.append((cid, en, fa, [s for s in SYMBOLS.values() if s['cat'] == cid]))
    return out
