"""PlateCanvas: zoomable / pannable editing surface.

The picture itself (workspace, plate, mm grid, elements, selection handles,
rulers) is rendered by raster.render_view with Pillow, so the screen shows
exactly what is exported.  This widget handles touches and gestures."""
import math

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget

import raster
from model import el_center, rotate_pt, snap
from ui.common import pil_to_texture

MIN_ZOOM, MAX_ZOOM = 0.3, 120.0


class PlateCanvas(Widget):
    def __init__(self, editor, **kw):
        super().__init__(**kw)
        self.editor = editor
        self.zoom = 4.0
        self.ox = self.oy = 0.0
        self.fitted = False
        self.touches = []
        self.mode = None
        self.changed = False
        self.interacting = False
        with self.canvas:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self._fast = Clock.create_trigger(self._render_fast, 0)
        self._hq = Clock.create_trigger(self._render_hq, 0.3)
        self.bind(size=self._on_size, pos=self._on_pos)

    # ---- geometry --------------------------------------------------------
    @property
    def ruler(self):
        return int(dp(22))

    def ui(self):
        return max(1.0, dp(1))

    def fit(self, *a):
        doc = self.editor.doc
        if self.width < 10 or self.height < 10:
            return
        R = self.ruler
        m = dp(24)
        aw, ah = self.width - R - 2 * m, self.height - R - 2 * m
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, min(aw / doc.w, ah / doc.h)))
        self.ox = R + (self.width - R - doc.w * self.zoom) / 2.0
        self.oy = R + (self.height - R - doc.h * self.zoom) / 2.0
        self.fitted = True
        self.redraw()

    def _on_size(self, *a):
        self.rect.size = self.size
        prev = getattr(self, '_prev_size', None)
        self._prev_size = tuple(self.size)
        if not self.fitted or prev is None:
            self.fit()
            return
        self.ox += (self.width - prev[0]) / 2.0
        self.oy += (self.height - prev[1]) / 2.0
        self.redraw()

    def _on_pos(self, *a):
        self.rect.pos = self.pos

    def to_view(self, x, y):
        return x - self.x, self.top - y

    def to_mm(self, vx, vy):
        return (vx - self.ox) / self.zoom, (vy - self.oy) / self.zoom

    # ---- rendering -------------------------------------------------------
    def redraw(self, *a):
        self._fast()
        self._hq.cancel()
        self._hq()

    def _do_render(self, ss):
        W, H = int(self.width), int(self.height)
        if W < 4 or H < 4:
            return
        ed = self.editor
        img = raster.render_view(ed.doc, W, H, self.zoom, self.ox, self.oy, sel=ed.sel,
                                 grid=ed.show_grid, ruler=self.ruler, ss=ss, ui=self.ui())
        self.rect.texture = pil_to_texture(img)
        self.rect.size = (W, H)
        self.rect.pos = self.pos

    def _render_fast(self, dt):
        self._do_render(1)

    def _render_hq(self, dt):
        if self.touches:
            self._hq()
            return
        self._do_render(2 if self.width * self.height < 4.5e6 else 1)

    # ---- zoom helpers ----------------------------------------------------
    def zoom_at(self, vx, vy, factor):
        mx, my = self.to_mm(vx, vy)
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        self.ox = vx - mx * self.zoom
        self.oy = vy - my * self.zoom
        self.redraw()

    # ---- touches ---------------------------------------------------------
    def on_touch_down(self, t):
        if not self.collide_point(*t.pos):
            return False
        vx, vy = self.to_view(*t.pos)
        if getattr(t, 'is_mouse_scrolling', False):
            f = 1.15
            if t.button in ('scrolldown', 'scrollleft'):
                self.zoom_at(vx, vy, f)
            elif t.button in ('scrollup', 'scrollright'):
                self.zoom_at(vx, vy, 1 / f)
            return True
        t.grab(self)
        self.touches.append(t)
        if len(self.touches) == 2:
            self._start_pinch()
            return True
        if len(self.touches) > 2:
            return True
        ed = self.editor
        t.ud['v0'] = (vx, vy)
        self.changed = False
        self.mode = 'pan'
        t.ud['o0'] = (self.ox, self.oy)
        if getattr(t, 'button', 'left') in ('right', 'middle'):
            return True
        ui = self.ui()
        # handles of a single selected element
        if len(ed.sel) == 1:
            e = ed.doc.get(ed.sel[0])
            if e is not None:
                hr = max(dp(18), 14 * ui)
                for name, hx, hy in raster.handle_positions(e, self.zoom, self.ox, self.oy, ui):
                    if math.hypot(vx - hx, vy - hy) <= hr:
                        self._begin_handle(e, name, t)
                        return True
        mx, my = self.to_mm(vx, vy)
        hit = ed.doc.hit_test(mx, my, tol=dp(5) / self.zoom)
        multi = ed.multi or ('shift' in getattr(t, 'modifiers', []) if hasattr(t, 'modifiers') else False)
        if hit is not None:
            if multi:
                if hit['id'] in ed.sel:
                    ed.set_selection([i for i in ed.sel if i != hit['id']])
                    self.mode = None
                    return True
                ed.set_selection(ed.sel + [hit['id']])
            elif hit['id'] not in ed.sel:
                ed.set_selection([hit['id']])
            self.mode = 'move'
            t.ud['orig'] = {i: (ed.doc.get(i)['x'], ed.doc.get(i)['y']) for i in ed.sel
                            if ed.doc.get(i)}
            if t.is_double_tap and hit['type'] in ('text', 'table'):
                ed.focus_text()
        else:
            if not multi and ed.sel:
                ed.set_selection([])
        return True

    def _begin_handle(self, e, name, t):
        t.ud['el0'] = dict(e)
        t.ud['handle'] = name
        if name == 'rot':
            self.mode = 'rotate'
        elif name in ('p1', 'p2'):
            self.mode = 'endpoint'
        else:
            self.mode = 'resize'

    def _start_pinch(self):
        a, b = self.touches[0], self.touches[1]
        va, vb = self.to_view(*a.pos), self.to_view(*b.pos)
        self._pinch = {
            'd0': max(1.0, math.hypot(va[0] - vb[0], va[1] - vb[1])),
            'z0': self.zoom,
            'mm': self.to_mm((va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2),
        }
        self.mode = 'pinch'

    def on_touch_move(self, t):
        if t.grab_current is not self:
            return False
        if self.mode == 'pinch' and len(self.touches) >= 2:
            a, b = self.touches[0], self.touches[1]
            va, vb = self.to_view(*a.pos), self.to_view(*b.pos)
            d = max(1.0, math.hypot(va[0] - vb[0], va[1] - vb[1]))
            p = self._pinch
            self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, p['z0'] * d / p['d0']))
            mx, my = p['mm']
            cx, cy = (va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2
            self.ox = cx - mx * self.zoom
            self.oy = cy - my * self.zoom
            self.redraw()
            return True
        if len(self.touches) != 1 or 'v0' not in t.ud:
            return True
        vx, vy = self.to_view(*t.pos)
        v0 = t.ud['v0']
        dvx, dvy = vx - v0[0], vy - v0[1]
        ed = self.editor
        st = ed.snap_step
        if self.mode == 'pan':
            o0 = t.ud['o0']
            self.ox, self.oy = o0[0] + dvx, o0[1] + dvy
            self.redraw()
        elif self.mode == 'move':
            if not self.changed and math.hypot(dvx, dvy) < dp(3):
                return True
            dx, dy = dvx / self.zoom, dvy / self.zoom
            for i, (x0, y0) in t.ud.get('orig', {}).items():
                e = ed.doc.get(i)
                if e is None:
                    continue
                e['x'] = snap(x0 + dx, st) if st else round(x0 + dx, 2)
                e['y'] = snap(y0 + dy, st) if st else round(y0 + dy, 2)
            self.changed = True
            ed.live_update()
        elif self.mode == 'resize':
            self._resize(t, vx, vy, st)
        elif self.mode == 'rotate':
            e = ed.doc.get(ed.sel[0])
            cx, cy = el_center(e)
            mx, my = self.to_mm(vx, vy)
            ang = math.degrees(math.atan2(my - cy, mx - cx)) + 90
            ang = (ang + 180) % 360 - 180
            for s in (-180, -90, 0, 90, 180, -135, -45, 45, 135):
                if abs(ang - s) < 4:
                    ang = s
            e['rot'] = round(ang, 1)
            self.changed = True
            ed.live_update()
        elif self.mode == 'endpoint':
            e = ed.doc.get(ed.sel[0])
            mx, my = self.to_mm(vx, vy)
            if st:
                mx, my = snap(mx, st), snap(my, st)
            e0 = t.ud['el0']
            if t.ud['handle'] == 'p1':
                x2, y2 = e0['x'] + e0['w'], e0['y'] + e0['h']
                e['x'], e['y'] = round(mx, 3), round(my, 3)
                e['w'], e['h'] = round(x2 - mx, 3), round(y2 - my, 3)
            else:
                e['w'], e['h'] = round(mx - e0['x'], 3), round(my - e0['y'], 3)
            self.changed = True
            ed.live_update()
        return True

    def _resize(self, t, vx, vy, st):
        ed = self.editor
        e = ed.doc.get(ed.sel[0])
        e0 = t.ud['el0']
        name = t.ud['handle']
        hx = (1 if 'e' in name else -1 if 'w' in name else 0)
        hy = (1 if 's' in name else -1 if 'n' in name else 0)
        rot = math.radians(e0.get('rot', 0) or 0)
        ux, uy = math.cos(rot), math.sin(rot)
        wx, wy = -math.sin(rot), math.cos(rot)
        cx0, cy0 = e0['x'] + e0['w'] / 2, e0['y'] + e0['h'] / 2
        ax = cx0 - hx * e0['w'] / 2 * ux - hy * e0['h'] / 2 * wx
        ay = cy0 - hx * e0['w'] / 2 * uy - hy * e0['h'] / 2 * wy
        mx, my = self.to_mm(vx, vy)
        du = (mx - ax) * ux + (my - ay) * uy
        dv = (mx - ax) * wx + (my - ay) * wy
        minsz = 0.5
        w = max(minsz, hx * du) if hx else e0['w']
        h = max(minsz, hy * dv) if hy else e0['h']
        if st:
            w = max(minsz, snap(w, st)) if hx else w
            h = max(minsz, snap(h, st)) if hy else h
        keep = e0.get('keep_aspect') or e0['type'] == 'hole'
        if keep and hx and hy and e0['w'] > 0 and e0['h'] > 0:
            ratio = e0['w'] / e0['h']
            if w / ratio > h:
                h = w / ratio
            else:
                w = h * ratio
        if e0['type'] == 'hole':
            w = h = max(w, h) if hx and hy else (w if hx else h)
        sx = hx if hx else 0
        sy = hy if hy else 0
        cx = ax + sx * w / 2 * ux + sy * h / 2 * wx
        cy = ay + sx * w / 2 * uy + sy * h / 2 * wy
        e['w'], e['h'] = round(w, 3), round(h, 3)
        e['x'], e['y'] = round(cx - w / 2, 3), round(cy - h / 2, 3)
        self.changed = True
        ed.live_update()

    def on_touch_up(self, t):
        if t.grab_current is not self:
            return False
        t.ungrab(self)
        if t in self.touches:
            self.touches.remove(t)
        if self.mode == 'pinch':
            if len(self.touches) < 2:
                self.mode = None
                # remaining finger continues as pan
                for o in self.touches:
                    o.ud['v0'] = self.to_view(*o.pos)
                    o.ud['o0'] = (self.ox, self.oy)
                    self.mode = 'pan'
            self.redraw()
            return True
        if self.changed:
            self.changed = False
            self.editor.commit()
        if not self.touches:
            self.mode = None
        self.redraw()
        return True
