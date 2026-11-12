"""Tiny hand-written PDF 1.4 writer (pure Python, works on Android).

Only what the app needs: pages with exact MediaBox in points, Flate
compressed RGB image XObjects, vector lines and the built-in Helvetica font.
"""
import zlib

MM = 72.0 / 25.4  # points per millimetre


def mm2pt(v):
    return v * MM


def f(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return s if s not in ('', '-0') else '0'


class PdfWriter:
    def __init__(self):
        self.objs = []
        self.pages = []
        self.pages_num = self._reserve()
        self.font_num = None

    def _reserve(self):
        self.objs.append(None)
        return len(self.objs)

    def _set(self, num, data):
        if isinstance(data, str):
            data = data.encode('latin-1')
        self.objs[num - 1] = data

    def add(self, data):
        n = self._reserve()
        self._set(n, data)
        return n

    def add_stream(self, dict_body, data, compress=True):
        if isinstance(data, str):
            data = data.encode('latin-1')
        if compress:
            data = zlib.compress(data, 6)
            dict_body += ' /Filter /FlateDecode'
        head = ('<< %s /Length %d >>\nstream\n' % (dict_body, len(data))).encode('latin-1')
        return self.add(head + data + b'\nendstream')

    def add_image(self, img):
        """Add a Pillow image (converted to RGB) as an image XObject."""
        img = img.convert('RGB')
        body = ('/Type /XObject /Subtype /Image /Width %d /Height %d '
                '/ColorSpace /DeviceRGB /BitsPerComponent 8' % (img.width, img.height))
        return self.add_stream(body, img.tobytes(), compress=True)

    def helvetica(self):
        if self.font_num is None:
            self.font_num = self.add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica '
                                     '/Encoding /WinAnsiEncoding >>')
        return self.font_num

    def add_page(self, w_pt, h_pt, content, images=None, font=False):
        res = []
        if images:
            res.append('/XObject << %s >>' % ' '.join(
                '/%s %d 0 R' % (k, v) for k, v in images.items()))
        if font:
            res.append('/Font << /F1 %d 0 R >>' % self.helvetica())
        cnum = self.add_stream('', content, compress=True)
        pnum = self.add('<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %s %s] '
                        '/Resources << %s >> /Contents %d 0 R >>'
                        % (self.pages_num, f(w_pt), f(h_pt), ' '.join(res), cnum))
        self.pages.append(pnum)
        return pnum

    def tobytes(self):
        self._set(self.pages_num, '<< /Type /Pages /Kids [%s] /Count %d >>' % (
            ' '.join('%d 0 R' % p for p in self.pages), len(self.pages)))
        info = self.add('<< /Producer (Trans Plate Designer) /Creator (Trans Plate Designer) >>')
        cat = self.add('<< /Type /Catalog /Pages %d 0 R >>' % self.pages_num)
        out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = []
        for i, data in enumerate(self.objs):
            offsets.append(len(out))
            out += ('%d 0 obj\n' % (i + 1)).encode('latin-1')
            out += data
            out += b'\nendobj\n'
        xref = len(out)
        out += ('xref\n0 %d\n' % (len(self.objs) + 1)).encode('latin-1')
        out += b'0000000000 65535 f \n'
        for off in offsets:
            out += ('%010d 00000 n \n' % off).encode('latin-1')
        out += ('trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n'
                % (len(self.objs) + 1, cat, info, xref)).encode('latin-1')
        return bytes(out)

    def save(self, path):
        with open(path, 'wb') as fh:
            fh.write(self.tobytes())


def pdf_text_escape(s):
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
