"""Document model for Trans Plate Designer (pure Python, no Kivy).

All coordinates are millimetres.  Origin = top-left corner of the plate,
x to the right, y downward.  Every element is a plain dict so it can be
serialised to JSON (.tplate files) without custom encoders.

Common element keys:
  id, type, x, y, w, h (mm), rot (degrees, clockwise about the box centre),
  stroke (hex colour or None), fill (hex colour or None), sw (stroke width mm)
"""
import copy
import datetime
import json
import math
import re
import uuid

FILE_EXT = '.tplate'
FORMAT_VERSION = 1

ELEMENT_TYPES = ('text', 'line', 'rect', 'ellipse', 'hole', 'table',
                 'frame', 'symbol', 'image')

BASE = dict(x=0.0, y=0.0, w=20.0, h=10.0, rot=0.0, stroke='#000000',
            fill=None, sw=0.3, locked=False)

TYPE_DEFAULTS = {
    'text': dict(w=40.0, h=8.0, text='Text', font_mm=4.0, bold=False,
                 align='center', stroke=None, color='#000000'),
    'line': dict(w=30.0, h=0.0, sw=0.4),
    'rect': dict(w=30.0, h=15.0, radius=0.0),
    'ellipse': dict(w=20.0, h=20.0),
    'hole': dict(w=4.0, h=4.0, sw=0.25, cross=True, fill=None),
    'table': dict(w=60.0, h=24.0, rows=3, cols=2, cells=None, font_mm=2.8,
                  bold=False, align='center', col_ratios=None,
                  header=False, header_fill='#e6e6e6', color='#000000',
                  sw=0.25),
    'frame': dict(w=96.0, h=56.0, radius=2.0, double=True, gap=1.0, sw=0.5),
    'symbol': dict(w=10.0, h=10.0, sym='earth', stext=None, sw=0.4,
                   keep_aspect=True),
    'image': dict(w=20.0, h=20.0, data=None, stroke=None, keep_aspect=True),
}

SIZE_PRESETS = [
    ('60x40', 60, 40), ('80x50', 80, 50), ('100x60', 100, 60),
    ('120x80', 120, 80), ('A6', 148, 105),
]


def new_id():
    return uuid.uuid4().hex[:10]


def make_element(etype, **kw):
    if etype not in ELEMENT_TYPES:
        raise ValueError('unknown element type %r' % etype)
    el = dict(BASE)
    el.update(copy.deepcopy(TYPE_DEFAULTS[etype]))
    el['type'] = etype
    el['id'] = new_id()
    el.update(kw)
    if etype == 'table':
        ensure_cells(el)
    if etype == 'hole':
        el['h'] = el['w']
    return el


def ensure_cells(el):
    rows, cols = int(el.get('rows', 1)), int(el.get('cols', 1))
    cells = el.get('cells') or []
    out = []
    for r in range(rows):
        row = list(cells[r]) if r < len(cells) else []
        row = (row + [''] * cols)[:cols]
        out.append([str(c) for c in row])
    el['cells'] = out
    cr = el.get('col_ratios')
    if cr and len(cr) != cols:
        el['col_ratios'] = None
    return el


def gregorian_to_jalali(gy, gm, gd):
    """Convert a Gregorian date to the Persian (Jalali / Solar Hijri) calendar."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
            + gd + g_d_m[gm - 1])
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def today_str(jalali=True):
    """Today's date; Persian calendar by default (e.g. 1405/08/22)."""
    d = datetime.date.today()
    if jalali:
        return '%04d/%02d/%02d' % gregorian_to_jalali(d.year, d.month, d.day)
    return d.strftime('%Y/%m/%d')


def next_serial(s):
    """Increment the last number found in s, keeping zero padding.

    'TR-0099' -> 'TR-0100', 'A9' -> 'A10', 'X' -> 'X1'."""
    s = s or ''
    m = list(re.finditer(r'\d+', s))
    if not m:
        return s + '1'
    last = m[-1]
    num = last.group()
    nxt = str(int(num) + 1).zfill(len(num))
    return s[:last.start()] + nxt + s[last.end():]


class Document:
    def __init__(self, w=100.0, h=60.0, name='', bg='#ffffff', radius=0.0):
        self.w = float(w)
        self.h = float(h)
        self.name = name
        self.bg = bg
        self.radius = float(radius)
        self.elements = []
        self.vars = {'serial': '0001', 'date': today_str()}

    # ---- serialisation -------------------------------------------------
    def to_dict(self):
        return {
            'app': 'TransPlateDesigner', 'version': FORMAT_VERSION,
            'w': self.w, 'h': self.h, 'name': self.name, 'bg': self.bg,
            'radius': self.radius, 'vars': dict(self.vars),
            'elements': copy.deepcopy(self.elements),
        }

    @classmethod
    def from_dict(cls, d):
        doc = cls(d.get('w', 100), d.get('h', 60), d.get('name', ''),
                  d.get('bg', '#ffffff'), d.get('radius', 0.0))
        doc.vars.update(d.get('vars', {}))
        for e in d.get('elements', []):
            t = e.get('type')
            if t not in ELEMENT_TYPES:
                continue
            el = make_element(t)
            el.update(e)
            if t == 'table':
                ensure_cells(el)
            doc.elements.append(el)
        return doc

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=1)

    @classmethod
    def from_json(cls, s):
        return cls.from_dict(json.loads(s))

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path):
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())

    def copy(self):
        return Document.from_dict(self.to_dict())

    # ---- text variables -------------------------------------------------
    def resolve(self, s, extra=None):
        if not s or '{' not in s:
            return s or ''
        v = dict(self.vars)
        if extra:
            v.update(extra)
        for k, val in v.items():
            s = s.replace('{%s}' % k, str(val))
        return s

    def increment_serial(self):
        self.vars['serial'] = next_serial(self.vars.get('serial', '0'))
        return self.vars['serial']

    # ---- element management -------------------------------------------
    def add(self, el):
        self.elements.append(el)
        return el

    def add_new(self, etype, center=True, **kw):
        el = make_element(etype, **kw)
        if center and 'x' not in kw and 'y' not in kw:
            el['x'] = round(self.w / 2 - el['w'] / 2, 2)
            el['y'] = round(self.h / 2 - el['h'] / 2, 2)
        return self.add(el)

    def get(self, eid):
        for e in self.elements:
            if e['id'] == eid:
                return e
        return None

    def index(self, eid):
        for i, e in enumerate(self.elements):
            if e['id'] == eid:
                return i
        return -1

    def remove(self, ids):
        ids = set(ids)
        self.elements = [e for e in self.elements if e['id'] not in ids]

    def duplicate(self, ids, offset=3.0):
        new = []
        for eid in ids:
            e = self.get(eid)
            if e is None:
                continue
            c = copy.deepcopy(e)
            c['id'] = new_id()
            c['x'] += offset
            c['y'] += offset
            self.elements.append(c)
            new.append(c['id'])
        return new

    def bring_front(self, ids):
        sel = [e for e in self.elements if e['id'] in ids]
        rest = [e for e in self.elements if e['id'] not in ids]
        self.elements = rest + sel

    def send_back(self, ids):
        sel = [e for e in self.elements if e['id'] in ids]
        rest = [e for e in self.elements if e['id'] not in ids]
        self.elements = sel + rest

    def move_layer(self, eid, delta):
        i = self.index(eid)
        j = max(0, min(len(self.elements) - 1, i + delta))
        if i < 0 or i == j:
            return
        e = self.elements.pop(i)
        self.elements.insert(j, e)

    def resize_plate(self, w, h, scale_content=False):
        w, h = float(w), float(h)
        if scale_content and self.w > 0 and self.h > 0:
            sx, sy = w / self.w, h / self.h
            for e in self.elements:
                e['x'] *= sx
                e['y'] *= sy
                e['w'] *= sx
                e['h'] *= sy
                s = min(sx, sy)
                if e['type'] == 'hole':
                    e['w'] = e['h'] = min(e['w'], e['h'])
                if 'font_mm' in e:
                    e['font_mm'] = round(e['font_mm'] * s, 2)
        self.w, self.h = w, h

    # ---- geometry helpers ----------------------------------------------
    def bbox(self, ids):
        boxes = [element_aabb(e) for e in self.elements if e['id'] in ids]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    def align(self, ids, mode):
        """mode: left/hcenter/right/top/vcenter/bottom/center_plate."""
        ids = list(ids)
        if not ids:
            return
        if len(ids) == 1 or mode == 'center_plate':
            ref = (0.0, 0.0, self.w, self.h)
        else:
            ref = self.bbox(ids)
        for eid in ids:
            e = self.get(eid)
            b = element_aabb(e)
            dx = dy = 0.0
            if mode == 'left':
                dx = ref[0] - b[0]
            elif mode == 'right':
                dx = ref[2] - b[2]
            elif mode == 'hcenter':
                dx = (ref[0] + ref[2]) / 2 - (b[0] + b[2]) / 2
            elif mode == 'top':
                dy = ref[1] - b[1]
            elif mode == 'bottom':
                dy = ref[3] - b[3]
            elif mode == 'vcenter':
                dy = (ref[1] + ref[3]) / 2 - (b[1] + b[3]) / 2
            elif mode == 'center_plate':
                dx = self.w / 2 - (b[0] + b[2]) / 2
                dy = self.h / 2 - (b[1] + b[3]) / 2
            e['x'] = round(e['x'] + dx, 3)
            e['y'] = round(e['y'] + dy, 3)

    def hit_test(self, x, y, tol=0.8):
        for e in reversed(self.elements):
            if element_contains(e, x, y, tol):
                return e
        return None


# ---- geometry (rotation about element centre) ---------------------------

def el_center(e):
    return e['x'] + e['w'] / 2.0, e['y'] + e['h'] / 2.0


def rotate_pt(px, py, cx, cy, deg):
    if not deg:
        return px, py
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    dx, dy = px - cx, py - cy
    return cx + dx * c - dy * s, cy + dx * s + dy * c


def element_corners(e):
    x, y, w, h = e['x'], e['y'], e['w'], e['h']
    cx, cy = el_center(e)
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if e['type'] == 'line':
        return [(x, y), (x + w, y + h)]
    return [rotate_pt(px, py, cx, cy, e.get('rot', 0)) for px, py in pts]


def element_aabb(e):
    pts = element_corners(e)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def to_local(e, px, py):
    cx, cy = el_center(e)
    return rotate_pt(px, py, cx, cy, -e.get('rot', 0))


def element_contains(e, px, py, tol=0.8):
    if e['type'] == 'line':
        x1, y1 = e['x'], e['y']
        x2, y2 = x1 + e['w'], y1 + e['h']
        return seg_dist(px, py, x1, y1, x2, y2) <= max(tol, e.get('sw', 0.3))
    lx, ly = to_local(e, px, py)
    return (e['x'] - tol <= lx <= e['x'] + e['w'] + tol and
            e['y'] - tol <= ly <= e['y'] + e['h'] + tol)


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    if L == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def snap(v, step):
    if not step:
        return v
    return round(round(v / step) * step, 4)


class History:
    """Snapshot based undo/redo."""

    def __init__(self, doc, limit=100):
        self.limit = limit
        self.stack = [doc.to_json()]
        self.pos = 0

    def push(self, doc):
        s = doc.to_json()
        if s == self.stack[self.pos]:
            return False
        del self.stack[self.pos + 1:]
        self.stack.append(s)
        if len(self.stack) > self.limit:
            self.stack.pop(0)
        self.pos = len(self.stack) - 1
        return True

    def can_undo(self):
        return self.pos > 0

    def can_redo(self):
        return self.pos < len(self.stack) - 1

    def undo(self):
        if not self.can_undo():
            return None
        self.pos -= 1
        return Document.from_json(self.stack[self.pos])

    def redo(self):
        if not self.can_redo():
            return None
        self.pos += 1
        return Document.from_json(self.stack[self.pos])
