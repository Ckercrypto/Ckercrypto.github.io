# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Windows build (one-folder, windowed).
#   pyinstaller TransPlateDesigner.spec --noconfirm
# Output: dist/TransPlateDesigner/TransPlateDesigner.exe
import os

# get_deps_all() only scans module names (no window is created), which is
# the reliable choice on headless CI runners.
from kivy.tools.packaging.pyinstaller_hooks import get_deps_all, hookspath, runtime_hooks

try:
    from kivy_deps import sdl2, glew
    dep_bins = sdl2.dep_bins + glew.dep_bins
    try:
        from kivy_deps import angle
        dep_bins += angle.dep_bins
    except ImportError:
        pass
except ImportError:  # building on a non-Windows host (for testing the spec)
    dep_bins = []

try:
    deps = get_deps_all()
except Exception as exc:  # e.g. no usable display while PyInstaller probes providers
    print('get_deps_all() failed (%s); using a static provider list' % exc)
    deps = {'hiddenimports': [
        'kivy.core.window.window_sdl2', 'kivy.core.text.text_sdl2', 'kivy.core.text.text_pil',
        'kivy.core.image.img_sdl2', 'kivy.core.image.img_pil', 'kivy.core.image.img_tex',
        'kivy.core.clipboard.clipboard_sdl2', 'kivy.core.clipboard.clipboard_winctypes',
        'kivy.core.clipboard.clipboard_dummy', 'kivy.core.gl',
        'kivy.graphics.cgl_backend.cgl_glew', 'kivy.graphics.cgl_backend.cgl_sdl2',
        'kivy.graphics.cgl_backend.cgl_gl', 'kivy.graphics.cgl_backend.cgl_debug',
        'kivy.graphics.cgl_backend.cgl_mock', 'kivy.input.providers.mouse',
        'kivy.input.providers.wm_touch', 'kivy.input.providers.wm_pen',
        'kivy.input.providers.wm_common', 'kivy.input.postproc',
    ], 'excludes': []}
deps['hiddenimports'] = list(deps.get('hiddenimports', [])) + [
    'arabic_reshaper', 'bidi', 'bidi.algorithm', 'six', 'PIL.Image', 'PIL.ImageDraw',
    'PIL.ImageFont', 'kivy.uix.filechooser', 'kivy.uix.popup', 'kivy.uix.modalview',
    'ui', 'ui.common', 'ui.canvas', 'ui.props', 'ui.dialogs', 'ui.screens',
    'model', 'symbols', 'render', 'raster', 'export', 'pdfwriter', 'svgwriter',
    'i18n', 'templates', 'textshape', 'platform_io',
]

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    datas=[('assets', 'assets')],
    hookspath=hookspath(),
    runtime_hooks=runtime_hooks(),
    noarchive=False,
    **deps
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TransPlateDesigner',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join('assets', 'icon.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in dep_bins],
    strip=False,
    upx=False,
    name='TransPlateDesigner',
)
