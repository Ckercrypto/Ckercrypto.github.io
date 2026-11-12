"""Ready-made plate templates (pure Python).  Each template has a form
(list of fields with defaults) and a build(data) -> Document function.
Everything generated is ordinary editable elements."""
from model import Document, make_element, today_str


def _t(doc, text, x, y, w, h, size, bold=False, align='center', color='#000000'):
    return doc.add(make_element('text', text=text, x=x, y=y, w=w, h=h, font_mm=size,
                                bold=bold, align=align, color=color))


def _sym(doc, sym, x, y, size, stext=None, sw=None, color='#000000'):
    from symbols import SYMBOLS
    a = SYMBOLS[sym].get('aspect', 1.0)
    w, h = (size, size / a) if a >= 1 else (size * a, size)
    el = make_element('symbol', sym=sym, x=x, y=y + (size - h) / 2, w=w, h=h, stroke=color)
    if stext:
        el['stext'] = stext
    if sw:
        el['sw'] = sw
    return doc.add(el)


def add_corner_holes(doc, d=3.5, inset=5.0):
    ids = []
    for cx in (inset, doc.w - inset):
        for cy in (inset, doc.h - inset):
            el = make_element('hole', x=cx - d / 2, y=cy - d / 2, w=d, h=d)
            doc.add(el)
            ids.append(el['id'])
    return ids


def add_frame(doc, inset=1.5, radius=2.0, double=True, sw=0.5):
    return doc.add(make_element('frame', x=inset, y=inset, w=doc.w - 2 * inset,
                                h=doc.h - 2 * inset, radius=radius, double=double, sw=sw))


CONN_SYMBOL = {'Y': 'star', 'y': 'star', 'Δ': 'delta', 'D': 'delta', 'd': 'delta',
               'Z': 'zigzag', 'z': 'zigzag'}


def build_transformer(data):
    g = lambda k: (data.get(k) or '').strip()
    kind = g('kind') or 'Transformer'
    doc = Document(120, 80, name='%s %s' % (g('brand_en') or 'plate', g('model')))
    doc.vars['serial'] = g('serial') or '0001'
    doc.vars['date'] = g('date') or today_str()
    add_frame(doc, 1.5, 2.5, True, 0.5)
    add_corner_holes(doc, 3.5, 5.0)
    # header
    _t(doc, g('brand_fa') or 'ترانس رضا', 10, 3.6, 100, 9, 6.2, True)
    is_stab = kind.lower().startswith('stab') or 'استاب' in kind
    title = ('VOLTAGE STABILIZER  -  استابلایزر' if is_stab
             else 'TRANSFORMER  -  ترانسفورماتور')
    _t(doc, (g('brand_en') or 'TRANS REZA').upper() + '   |   ' + title,
       10, 12.6, 100, 5, 2.7, True)
    doc.add(make_element('line', x=8, y=18.6, w=104, h=0, sw=0.4))
    phases = g('phases') or '1'
    cells = [
        ['Model / مدل', g('model'), 'Power / توان', '%s kVA' % g('kva') if g('kva') else ''],
        ['Input / ورودی', '%s V' % g('vin') if g('vin') else '',
         'Output / خروجی', '%s V' % g('vout') if g('vout') else ''],
        ['Freq. / فرکانس', '%s Hz' % g('hz') if g('hz') else '',
         'Current / جریان', '%s A' % g('amp') if g('amp') else ''],
        ['Phase / فاز', phases, 'Conn. / اتصال', g('conn')],
        ['Ins. / عایق', g('ins'), 'IP', g('ip')],
        ['S/N / سریال', '{serial}', 'Date / تاریخ', '{date}'],
    ]
    doc.add(make_element('table', x=8, y=20.5, w=104, h=40.5, rows=6, cols=4, cells=cells,
                         font_mm=2.75, col_ratios=[1.05, 1.0, 1.05, 1.0], sw=0.25))
    # symbol row
    syms = ['ac', 'phase3' if phases.strip() in ('3', '۳') else 'phase1']
    conn = g('conn')
    if conn and conn[0] in CONN_SYMBOL:
        syms.append(CONN_SYMBOL[conn[0]])
    syms += ['protective_earth', 'hv_warning', 'weee', 'manual']
    x = 9.0
    for s in syms:
        _sym(doc, s, x, 63.2, 7.6)
        x += 8.6
    _sym(doc, 'ip_badge', x + 0.2, 63.2, 8.6, stext='IP%s' % g('ip').replace('IP', '')
         if g('ip') else 'IP20')
    cx0 = x + 10.0
    _t(doc, 'Tel: ' + g('phone') if g('phone') else '', cx0, 62.6, 110.5 - cx0, 4.2, 2.6,
       True, 'right')
    _t(doc, g('address'), cx0, 66.8, 110.5 - cx0, 4.0, 2.3, False, 'right')
    _t(doc, 'Made in Iran - ساخت ایران', cx0, 70.8, 110.5 - cx0, 3.6, 2.0, False, 'right',
       '#333333')
    return doc


def build_warning(data):
    g = lambda k: (data.get(k) or '').strip()
    doc = Document(80, 50, name='warning-label', radius=3.0)
    doc.bg = '#ffffff'
    doc.add(make_element('rect', x=1.2, y=1.2, w=77.6, h=47.6, radius=2.2, sw=1.2,
                         stroke='#000000', fill='#FFD200'))
    _sym(doc, 'hv_warning', 4.5, 7.5, 24)
    _t(doc, g('title_fa') or 'خطر برق فشار قوی', 30, 6, 47, 12, 5.0, True)
    _t(doc, g('title_en') or 'DANGER - HIGH VOLTAGE', 30, 17.5, 47, 8, 3.4, True)
    doc.add(make_element('line', x=31, y=26.5, w=45, h=0, sw=0.5))
    _t(doc, g('voltage') or '400 V', 30, 28, 47, 10, 6.0, True, color='#c40000')
    _t(doc, g('brand_fa') or 'ترانس رضا', 4, 40, 72, 6, 3.0, True)
    return doc


def build_terminal(data):
    doc = Document(100, 16, name='terminal-strip', radius=1.5)
    doc.add(make_element('table', x=1, y=1, w=98, h=14, rows=1, cols=5,
                         cells=[['L1', 'L2', 'L3', 'N', 'PE    ']],
                         font_mm=6.0, bold=True, sw=0.5))
    _sym(doc, 'protective_earth', 91.0, 5.0, 6.0)
    return doc


def build_stabilizer(data):
    g = lambda k: (data.get(k) or '').strip()
    doc = Document(100, 60, name='stabilizer-%s' % g('model'))
    doc.vars['serial'] = g('serial') or '0001'
    add_frame(doc, 1.5, 2.0, False, 0.6)
    add_corner_holes(doc, 3.2, 4.5)
    _t(doc, g('brand_fa') or 'ترانس رضا', 9, 3.5, 82, 8, 5.4, True)
    _t(doc, 'استابلایزر ولتاژ  -  VOLTAGE STABILIZER', 9, 11.2, 82, 4.6, 2.8, True)
    rows = [
        ['Model / مدل', g('model')],
        ['Power / توان', ('%s kVA' % g('kva')) if g('kva') else ''],
        ['Input / ورودی', ('%s V' % g('vin_range')) if g('vin_range') else ''],
        ['Output / خروجی', ('%s V' % g('vout')) if g('vout') else ''],
        ['S/N / سریال', '{serial}'],
    ]
    doc.add(make_element('table', x=9, y=17, w=62, h=31, rows=5, cols=2, cells=rows,
                         font_mm=2.8, col_ratios=[1.0, 1.0], sw=0.25))
    _sym(doc, 'regulator', 76, 18, 14)
    _sym(doc, 'ac', 76, 34, 6.5)
    _sym(doc, 'protective_earth', 84, 34, 6.5)
    _t(doc, ('Tel: ' + g('phone')) if g('phone') else '', 9, 49.5, 82, 5, 2.6, True)
    return doc


TEMPLATES = [
    {'id': 'transformer', 'name': 'tpl_transformer', 'size': (120, 80), 'icon': 'transformer',
     'build': build_transformer,
     'fields': [
         ('kind', 'Transformer'), ('brand_fa', 'ترانس رضا'), ('brand_en', 'Trans Reza'),
         ('model', 'TR-5000'), ('kva', '5'), ('vin', '220'), ('vout', '220'), ('hz', '50'),
         ('amp', '22.7'), ('phases', '1'), ('conn', 'Y'), ('ins', 'F'), ('ip', 'IP20'),
         ('serial', '0001'), ('date', today_str()), ('phone', ''), ('address', 'Mashhad / مشهد'),
     ]},
    {'id': 'warning', 'name': 'tpl_warning', 'size': (80, 50), 'icon': 'hv_warning',
     'build': build_warning,
     'fields': [('title_fa', 'خطر برق فشار قوی'), ('title_en', 'DANGER - HIGH VOLTAGE'),
                ('voltage', '400 V'), ('brand_fa', 'ترانس رضا')]},
    {'id': 'terminal', 'name': 'tpl_terminal', 'size': (100, 16), 'icon': 'label_l1',
     'build': build_terminal, 'fields': []},
    {'id': 'stabilizer', 'name': 'tpl_stabilizer', 'size': (100, 60), 'icon': 'regulator',
     'build': build_stabilizer,
     'fields': [('brand_fa', 'ترانس رضا'), ('model', 'ST-3000'), ('kva', '3'),
                ('vin_range', '140-260'), ('vout', '220'), ('serial', '0001'), ('phone', '')]},
]


def get_template(tid):
    for t in TEMPLATES:
        if t['id'] == tid:
            return t
    return None


def defaults(tid):
    return dict(get_template(tid)['fields'])
