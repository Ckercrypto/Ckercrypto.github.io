"""Persian / Arabic text shaping helpers (pure Python, no Kivy).

Kivy and Pillow (without libraqm) draw glyphs one by one, left to right.
To show Persian correctly we first reshape letters into their joined
presentation forms (arabic_reshaper) and then reorder the string into
visual order (python-bidi).  Strings that contain no RTL characters are
returned unchanged.
"""
import re

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _reshaper = arabic_reshaper.ArabicReshaper(configuration={
        'delete_harakat': False,
        'support_ligatures': True,
    })
    HAVE_SHAPING = True
except Exception:  # pragma: no cover - fallback if libs missing
    _reshaper = None
    get_display = None
    HAVE_SHAPING = False

_RTL_RE = re.compile('[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]')
_STRONG_LTR_RE = re.compile('[A-Za-z\u00C0-\u024F]')


def has_rtl(s):
    return bool(s) and bool(_RTL_RE.search(s))


def is_rtl(s):
    """True when the first strong character of s is right-to-left."""
    for ch in s or '':
        if _RTL_RE.match(ch):
            return True
        if _STRONG_LTR_RE.match(ch):
            return False
    return False


def shape_line(s):
    if not s or not HAVE_SHAPING or not has_rtl(s):
        return s
    return get_display(_reshaper.reshape(s))


def shape(s):
    """Shape a (possibly multi-line) string for visual display."""
    if s is None:
        return ''
    if '\n' not in s:
        return shape_line(s)
    return '\n'.join(shape_line(x) for x in s.split('\n'))
