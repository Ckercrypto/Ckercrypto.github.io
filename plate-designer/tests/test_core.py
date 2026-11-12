"""Unit tests for the Kivy-independent core.  Run:  python -m pytest -q tests
(or python tests/test_core.py)."""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from PIL import Image  # noqa: E402

import export  # noqa: E402
from model import Document, History, make_element, next_serial  # noqa: E402
from symbols import SYMBOLS, CATEGORIES  # noqa: E402
from templates import TEMPLATES, defaults  # noqa: E402
from textshape import shape  # noqa: E402

OUT = os.environ.get('TPD_TEST_OUT') or tempfile.mkdtemp(prefix='tpd_')
PT = 72.0 / 25.4


def mediaboxes(path):
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        return [tuple(float(v) for v in p.mediabox) for p in r.pages]
    except ImportError:
        data = open(path, 'rb').read().decode('latin-1')
        return [tuple(float(v) for v in m.split())
                for m in re.findall(r'/MediaBox \[([^\]]+)\]', data)]


def all_symbols_doc():
    doc = Document(100, 60)
    x = y = 1
    for sid in SYMBOLS:
        doc.add(make_element('symbol', sym=sid, x=x, y=y, w=8, h=8))
        x += 9
        if x > 90:
            x, y = 1, y + 9
    return doc


def test_symbols_complete():
    need = ['earth', 'protective_earth', 'chassis', 'functional_earth', 'star', 'delta',
            'zigzag', 'ac', 'dc', 'acdc', 'phase1', 'phase3', 'label_l1', 'label_l2',
            'label_l3', 'label_n', 'label_pe', 'transformer', 'autotransformer', 'inductor',
            'capacitor', 'resistor', 'fuse', 'switch', 'breaker', 'contactor_coil', 'lamp',
            'motor', 'generator', 'voltmeter', 'ammeter', 'hv_warning', 'bolt', 'class2',
            'class1', 'ip_badge', 'hz', 'phase_arrow', 'thermal', 'fan', 'input', 'output',
            'conformity', 'weee', 'manual']
    for s in need:
        assert s in SYMBOLS, s
    cats = {c[0] for c in CATEGORIES}
    for s in SYMBOLS.values():
        assert s['cat'] in cats and s['en'] and s['fa']


def test_pdf_size_100x60():
    doc = all_symbols_doc()
    p = os.path.join(OUT, 'plate_100x60.pdf')
    W, H = export.export_pdf(doc, p, dpi=600)
    mb = mediaboxes(p)
    assert len(mb) == 1
    assert abs(mb[0][2] - 100 * PT) < 0.01 and abs(mb[0][3] - 60 * PT) < 0.01, mb


def test_png_600dpi():
    doc = all_symbols_doc()
    p = os.path.join(OUT, 'plate_100x60_600.png')
    export.export_png(doc, p, dpi=600)
    im = Image.open(p)
    assert im.size == (round(100 / 25.4 * 600), round(60 / 25.4 * 600)), im.size
    dpi = im.info.get('dpi')
    assert dpi and abs(dpi[0] - 600) < 1


def test_svg_mm():
    doc = all_symbols_doc()
    doc.add(make_element('text', text='ترانس رضا', x=10, y=50, w=40, h=8))
    p = os.path.join(OUT, 'plate_100x60.svg')
    export.export_svg(doc, p)
    s = open(p, encoding='utf-8').read()
    assert 'width="100mm"' in s and 'height="60mm"' in s and 'viewBox="0 0 100 60"' in s
    from textshape import shape
    assert shape('ترانس رضا') in s and 'bidi-override' in s
    import xml.dom.minidom
    xml.dom.minidom.parseString(s.encode('utf-8'))


def test_tiled_and_calibration():
    doc = Document(100, 60)
    p = os.path.join(OUT, 'tiled.pdf')
    info = export.export_tiled_pdf(doc, p, copies=10, spacing=3, dpi=150)
    mb = mediaboxes(p)
    assert all(abs(m[2] - 210 * PT) < 0.01 and abs(m[3] - 297 * PT) < 0.01 for m in mb)
    assert info['pages'] == len(mb)
    assert info['per_page'] == 6 and info['rotated']
    doc.vars['serial'] = 'TR-0098'
    info = export.export_tiled_pdf(doc, os.path.join(OUT, 'tiled_serial.pdf'), copies=3,
                                   dpi=100, vary_serial=True)
    assert info['serials'] == ['TR-0098', 'TR-0099', 'TR-0100']
    export.export_calibration_pdf(os.path.join(OUT, 'calibration.pdf'))


def test_correction():
    doc = Document(100, 60)
    p = os.path.join(OUT, 'corr.pdf')
    export.export_pdf(doc, p, dpi=100, corr=(1.02, 0.99))
    mb = mediaboxes(p)[0]
    assert abs(mb[2] - 102 * PT) < 0.01 and abs(mb[3] - 59.4 * PT) < 0.01
    assert abs(export.factor_from_measure(98) - 100 / 98.0) < 1e-9


def test_model_ops():
    doc = Document(100, 60)
    h = History(doc)
    e = doc.add_new('rect')
    h.push(doc)
    doc.align([e['id']], 'left')
    assert abs(e['x']) < 1e-6
    h.push(doc)
    d2 = h.undo()
    assert abs(d2.elements[0]['x'] - 35) < 1e-6
    d3 = h.redo()
    assert abs(d3.elements[0]['x']) < 1e-6
    ids = doc.duplicate([e['id']])
    assert len(doc.elements) == 2
    doc.send_back(ids)
    assert doc.elements[0]['id'] == ids[0]
    assert next_serial('TR-0099') == 'TR-0100'
    assert next_serial('A9') == 'A10'
    doc2 = Document.from_json(doc.to_json())
    assert doc2.to_dict() == doc.to_dict()


def test_jalali():
    from model import gregorian_to_jalali
    assert gregorian_to_jalali(2026, 11, 13) == (1405, 8, 22)
    assert gregorian_to_jalali(2025, 3, 21) == (1404, 1, 1)
    assert gregorian_to_jalali(2024, 3, 20) == (1403, 1, 1)


def test_shaping():
    s = shape('سلام')
    assert s != 'سلام' and '\ufe8e' in s or '\ufee3' in s or s[0] != 'س'


def test_templates():
    for t in TEMPLATES:
        doc = t['build'](defaults(t['id']))
        assert doc.elements
        export.export_png(doc, os.path.join(OUT, 'tpl_%s.png' % t['id']), dpi=300)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
    print('outputs in', OUT)
