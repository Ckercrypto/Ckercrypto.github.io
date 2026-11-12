"""Export: 1:1 PDF, A4 tiled PDF with cut marks, PNG at dpi, SVG in mm,
and the printer calibration page.  Pure Python (Pillow + hand-written PDF).

corr = (x_factor, y_factor) printer scale correction, 1.0 = none.
"""
import math
import re

from PIL import Image, ImageDraw

import raster
from model import next_serial
from pdfwriter import PdfWriter, f, mm2pt, pdf_text_escape
from svgwriter import doc_to_svg

A4 = (210.0, 297.0)


def safe_name(s, default='plate'):
    s = re.sub(r'[\\/:*?"<>|\s]+', '_', (s or '').strip()).strip('_')
    return s or default


def export_png(doc, path, dpi=600, corr=(1.0, 1.0), extra_vars=None):
    img = raster.render_plate(doc, dpi, extra_vars, corr)
    img.save(path, dpi=(dpi, dpi), optimize=False)
    return img.size


def export_svg(doc, path, corr=(1.0, 1.0), extra_vars=None):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(doc_to_svg(doc, corr, extra_vars))


def export_pdf(doc, path, dpi=600, corr=(1.0, 1.0), extra_vars=None):
    """Single plate; page MediaBox = plate size (x correction) in points."""
    pdf = PdfWriter()
    img = raster.render_plate(doc, dpi, extra_vars)
    im = pdf.add_image(img)
    W, H = mm2pt(doc.w * corr[0]), mm2pt(doc.h * corr[1])
    content = 'q %s 0 0 %s 0 0 cm /Im1 Do Q\n' % (f(W), f(H))
    pdf.add_page(W, H, content, {'Im1': im})
    pdf.save(path)
    return W, H


def tile_layout(pw, ph, spacing=2.0, margin=8.0, sheet=A4):
    sw, sh = sheet
    cols = int(math.floor((sw - 2 * margin + spacing) / (pw + spacing) + 1e-9))
    rows = int(math.floor((sh - 2 * margin + spacing) / (ph + spacing) + 1e-9))
    return max(0, cols), max(0, rows)


def export_tiled_pdf(doc, path, copies=None, spacing=2.0, margin=8.0, dpi=600,
                     corr=(1.0, 1.0), vary_serial=False, cut_marks=True,
                     auto_rotate=True, sheet=A4):
    """N copies on A4 sheets with cut marks.  Returns dict with layout info.

    copies=None fills one full sheet.  With vary_serial each copy gets the
    next serial number (starting from the document's current serial)."""
    pw0, ph0 = doc.w * corr[0], doc.h * corr[1]
    c0, r0 = tile_layout(pw0, ph0, spacing, margin, sheet)
    c1, r1 = tile_layout(ph0, pw0, spacing, margin, sheet)
    rotated = auto_rotate and c1 * r1 > c0 * r0
    if rotated:
        pw, ph, cols, rows = ph0, pw0, c1, r1
    else:
        pw, ph, cols, rows = pw0, ph0, c0, r0
    per_page = cols * rows
    if per_page == 0:
        raise ValueError('Plate is larger than the printable sheet area')
    if not copies:
        copies = per_page
    copies = int(copies)
    sw, sh = sheet
    gw = cols * pw + (cols - 1) * spacing
    gh = rows * ph + (rows - 1) * spacing
    gx0 = (sw - gw) / 2.0
    gy0 = (sh - gh) / 2.0

    pdf = PdfWriter()
    serial = doc.vars.get('serial', '0001')
    shared_img = None
    if not vary_serial:
        shared_img = pdf.add_image(raster.render_plate(doc, dpi))
    serials = []
    done = 0
    pages = 0
    while done < copies:
        n_here = min(per_page, copies - done)
        images = {}
        content = []
        for i in range(n_here):
            r, c = divmod(i, cols)
            x = gx0 + c * (pw + spacing)
            y_top = gy0 + r * (ph + spacing)
            X = mm2pt(x)
            Y = mm2pt(sh - y_top - ph)
            if vary_serial:
                name = 'Im%d' % i
                images[name] = pdf.add_image(
                    raster.render_plate(doc, dpi, {'serial': serial}))
                serials.append(serial)
                serial = next_serial(serial)
            else:
                name = 'Im1'
                images[name] = shared_img
            if rotated:
                # 90 deg clockwise: plate top edge ends up on the right
                content.append('q 0 %s %s 0 %s %s cm /%s Do Q' % (
                    f(-mm2pt(pw0)), f(mm2pt(ph0)), f(X), f(Y + mm2pt(pw0)), name))
            else:
                content.append('q %s 0 0 %s %s %s cm /%s Do Q' % (
                    f(mm2pt(pw)), f(mm2pt(ph)), f(X), f(Y), name))
        if cut_marks:
            content.append(_cut_marks(n_here, cols, rows, pw, ph, spacing, gx0, gy0, sheet,
                                      margin))
        label = 'Trans Plate Designer  |  %s x %s mm  |  %d/%d  |  spacing %s mm' % (
            f(doc.w), f(doc.h), done + n_here, copies, f(spacing))
        content.append('BT /F1 6 Tf %s %s Td (%s) Tj ET' % (
            f(mm2pt(margin)), f(mm2pt(min(margin, gy0) / 2.0)), pdf_text_escape(label)))
        pdf.add_page(mm2pt(sw), mm2pt(sh), '\n'.join(content) + '\n', images, font=True)
        done += n_here
        pages += 1
    pdf.save(path)
    return {'cols': cols, 'rows': rows, 'per_page': per_page, 'pages': pages,
            'copies': copies, 'rotated': rotated, 'serials': serials,
            'next_serial': serial if vary_serial else None}


def _cut_marks(n, cols, rows, pw, ph, spacing, gx0, gy0, sheet, margin):
    sw, sh = sheet
    used_rows = int(math.ceil(n / float(cols)))
    used_cols = cols if used_rows > 1 else n
    xs, ys = set(), set()
    for c in range(used_cols):
        x = gx0 + c * (pw + spacing)
        xs.update((round(x, 4), round(x + pw, 4)))
    for r in range(used_rows):
        y = gy0 + r * (ph + spacing)
        ys.update((round(y, 4), round(y + ph, 4)))
    gy1 = gy0 + used_rows * ph + (used_rows - 1) * spacing
    gx1 = gx0 + used_cols * pw + (used_cols - 1) * spacing
    L = []

    def line(x1, y1, x2, y2):
        L.append('%s %s m %s %s l S' % (f(mm2pt(x1)), f(mm2pt(sh - y1)),
                                        f(mm2pt(x2)), f(mm2pt(sh - y2))))
    gap = 1.0
    top_len = min(5.0, gy0 - gap - 0.5)
    left_len = min(5.0, gx0 - gap - 0.5)
    for x in xs:
        if top_len > 0.8:
            line(x, gy0 - gap, x, gy0 - gap - top_len)
            line(x, gy1 + gap, x, gy1 + gap + top_len)
    for y in ys:
        if left_len > 0.8:
            line(gx0 - gap, y, gx0 - gap - left_len, y)
            line(gx1 + gap, y, gx1 + gap + left_len, y)
    if spacing >= 3.0:
        t = min(3.0, spacing / 2.0 - 0.5)
        for i in range(n):
            r, c = divmod(i, cols)
            x = gx0 + c * (pw + spacing)
            y = gy0 + r * (ph + spacing)
            for cx, sx in ((x, -1), (x + pw, 1)):
                for cy, sy in ((y, -1), (y + ph, 1)):
                    line(cx + sx * 0.5, cy, cx + sx * (0.5 + t), cy)
                    line(cx, cy + sy * 0.5, cx, cy + sy * (0.5 + t))
    return 'q 0 G %s w\n%s\nQ' % (f(mm2pt(0.15)), '\n'.join(L))


CALIB_TEXT_EN = [
    'Printer calibration page',
    '1. Print this page at 100% / "Actual size". Turn OFF "Fit to page" / "Scale to fit".',
    '2. Measure the 100 mm and 50 mm rulers below with a good steel ruler.',
    '3. In the app open Settings > Printer calibration and type what you measured.',
    '   The app sets correction = 100 / measured (for example 98 mm -> 102.04 %).',
    '4. Print again: the rulers on later prints should now match exactly.',
]
CALIB_TEXT_FA = [
    'صفحهٔ کالیبراسیون چاپگر',
    '۱. این صفحه را با مقیاس ۱۰۰٪ (Actual size) چاپ کنید و «Fit to page» را خاموش کنید.',
    '۲. خط‌کش ۱۰۰ و ۵۰ میلی‌متری را با یک خط‌کش فلزی دقیق اندازه بگیرید.',
    '۳. در برنامه: «تنظیمات / کالیبراسیون چاپگر» عدد اندازه‌گیری‌شده را وارد کنید.',
    '۴. دوباره چاپ کنید؛ اندازه‌ها اکنون باید دقیق باشند.',
]


def _calib_text_image(dpi=300):
    from textshape import shape_line
    w_mm, h_mm = 190.0, 66.0
    s = dpi / 25.4
    img = Image.new('RGB', (int(w_mm * s), int(h_mm * s)), 'white')
    d = ImageDraw.Draw(img)
    y = 6.0
    for i, t in enumerate(CALIB_TEXT_EN):
        font = raster.get_font(i == 0, (4.2 if i == 0 else 3.0) * s)
        d.text((2 * s, y * s), t, font=font, fill='black', anchor='ls')
        y += 5.2 if i == 0 else 4.2
    y += 2.5
    for i, t in enumerate(CALIB_TEXT_FA):
        font = raster.get_font(i == 0, (4.2 if i == 0 else 3.0) * s)
        d.text(((w_mm - 2) * s, y * s), shape_line(t), font=font, fill='black', anchor='rs')
        y += 5.6 if i == 0 else 4.6
    return img, w_mm, h_mm


def export_calibration_pdf(path):
    sw, sh = A4
    pdf = PdfWriter()
    timg, tw, th = _calib_text_image()
    im = pdf.add_image(timg)
    C = []
    x0, top = 10.0, 10.0
    C.append('q %s 0 0 %s %s %s cm /Im1 Do Q' % (f(mm2pt(tw)), f(mm2pt(th)), f(mm2pt(x0)),
                                                 f(mm2pt(sh - top - th))))

    def line(x1, y1, x2, y2):
        C.append('%s %s m %s %s l S' % (f(mm2pt(x1)), f(mm2pt(sh - y1)),
                                        f(mm2pt(x2)), f(mm2pt(sh - y2))))

    def text(x, y, s, size=7):
        C.append('BT /F1 %s Tf %s %s Td (%s) Tj ET' % (f(size), f(mm2pt(x)),
                                                        f(mm2pt(sh - y)), pdf_text_escape(s)))

    def hruler(x, y, length, label):
        C.append('q 0 G %s w' % f(mm2pt(0.2)))
        line(x, y, x + length, y)
        for i in range(int(length) + 1):
            L = 6 if i % 10 == 0 else (4 if i % 5 == 0 else 2.5)
            line(x + i, y, x + i, y - L)
            if i % 10 == 0:
                text(x + i - (0.9 if i < 10 else 1.6 if i < 100 else 2.4), y - 7, str(i), 6)
        C.append('Q')
        text(x, y + 5, label, 8)

    hruler(15, 100, 100, '100 mm ruler (X direction)')
    hruler(15, 130, 50, '50 mm ruler (X direction)')
    # vertical 100 mm ruler for the Y direction
    vx, vy = 170.0, 95.0
    C.append('q 0 G %s w' % f(mm2pt(0.2)))
    line(vx, vy, vx, vy + 100)
    for i in range(101):
        L = 6 if i % 10 == 0 else (4 if i % 5 == 0 else 2.5)
        line(vx, vy + i, vx + L, vy + i)
        if i % 10 == 0:
            text(vx + 7, vy + i + 1, str(i), 6)
    C.append('Q')
    text(vx - 12, vy - 4, '100 mm ruler (Y direction)', 8)
    # 50 x 50 mm square
    C.append('q 0 G %s w' % f(mm2pt(0.25)))
    C.append('%s %s %s %s re S' % (f(mm2pt(15)), f(mm2pt(sh - 210)), f(mm2pt(50)), f(mm2pt(50))))
    C.append('Q')
    text(15, 155, '50 x 50 mm square', 8)
    text(10, 290, 'Trans Plate Designer - calibration page (printed without correction)', 6)
    pdf.add_page(mm2pt(sw), mm2pt(sh), '\n'.join(C) + '\n', {'Im1': im}, font=True)
    pdf.save(path)


def factor_from_measure(measured_mm, expected_mm=100.0):
    if not measured_mm or measured_mm <= 0:
        return 1.0
    return expected_mm / float(measured_mm)
