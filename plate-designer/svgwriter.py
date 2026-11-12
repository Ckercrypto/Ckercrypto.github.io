"""SVG export in millimetre units (vector; good for laser / CNC engraving)."""
from xml.sax.saxutils import escape

import render
from textshape import has_rtl, shape_line


def n(v):
    s = ('%.3f' % v).rstrip('0').rstrip('.')
    return s if s not in ('', '-0') else '0'


def _paint(op):
    fill = op.get('fill') or 'none'
    st = op.get('stroke')
    if st and op.get('sw', 0) > 0:
        return ('fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round" '
                'stroke-linecap="round"' % (fill, st, n(op['sw'])))
    return 'fill="%s" stroke="none"' % fill


def path_d(pts, closed):
    d = 'M%s %s' % (n(pts[0][0]), n(pts[0][1]))
    d += ''.join(' L%s %s' % (n(x), n(y)) for x, y in pts[1:])
    return d + (' Z' if closed else '')


def doc_to_svg(doc, corr=(1.0, 1.0), extra_vars=None, cut_outline=True):
    cx, cy = corr
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<svg xmlns="http://www.w3.org/2000/svg" '
           'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
           'width="%smm" height="%smm" viewBox="0 0 %s %s" preserveAspectRatio="none">'
           % (n(doc.w * cx), n(doc.h * cy), n(doc.w), n(doc.h)),
           '<title>%s</title>' % escape(doc.name or 'Trans Plate'),
           '<desc>Trans Plate Designer - units are millimetres (1 user unit = 1 mm)</desc>',
           '<g id="plate">',
           '<path id="plate-bg" d="%s" fill="%s" stroke="none"/>'
           % (path_d(render.plate_outline(doc), True), doc.bg),
           '</g>', '<g id="artwork">']
    for op in render.compile_doc(doc, extra_vars):
        k = op['k']
        if k == 'path':
            if len(op['pts']) < 2:
                continue
            out.append('<path d="%s" %s/>' % (path_d(op['pts'], op['closed']), _paint(op)))
        elif k == 'circle':
            out.append('<circle cx="%s" cy="%s" r="%s" %s/>'
                       % (n(op['cx']), n(op['cy']), n(op['r']), _paint(op)))
        elif k == 'text':
            lines = op['text'].split('\n')
            bls = render.text_baselines(op['y'], op['h'], op['size'], len(lines))
            align = op.get('align', 'center')
            tr = ''
            if op.get('rot'):
                tr = ' transform="rotate(%s %s %s)"' % (n(op['rot']), n(op['px']), n(op['py']))
            for line, bl in zip(lines, bls):
                if not line:
                    continue
                # Persian is written pre-shaped (joined presentation forms) in
                # visual order with bidi-override, so it renders correctly even
                # in programs without Arabic shaping (laser/CNC software, cairo).
                rtl = has_rtl(line)
                vis = shape_line(line) if rtl else line
                if align == 'left':
                    x, anchor = op['x'], 'start'
                elif align == 'right':
                    x, anchor = op['x'] + op['w'], 'end'
                else:
                    x, anchor = op['x'] + op['w'] / 2, 'middle'
                out.append('<text x="%s" y="%s" font-family="Vazirmatn, Tahoma, sans-serif" '
                           'font-size="%s" font-weight="%s" fill="%s" text-anchor="%s"%s%s>%s</text>'
                           % (n(x), n(bl), n(op['size']), 'bold' if op.get('bold') else 'normal',
                              op.get('color') or '#000000', anchor,
                              ' direction="ltr" unicode-bidi="bidi-override"' if rtl else '', tr,
                              escape(vis)))
        elif k == 'image':
            tr = ''
            if op.get('rot'):
                tr = ' transform="rotate(%s %s %s)"' % (
                    n(op['rot']), n(op['x'] + op['w'] / 2), n(op['y'] + op['h'] / 2))
            out.append('<image x="%s" y="%s" width="%s" height="%s" preserveAspectRatio="none"'
                       ' xlink:href="data:image/png;base64,%s"%s/>'
                       % (n(op['x']), n(op['y']), n(op['w']), n(op['h']), op['data'], tr))
    out.append('</g>')
    if cut_outline:
        out.append('<g id="cut-line"><path d="%s" fill="none" stroke="#ff0000" '
                   'stroke-width="0.05"/></g>' % path_d(render.plate_outline(doc), True))
    out.append('</svg>')
    return '\n'.join(out)
