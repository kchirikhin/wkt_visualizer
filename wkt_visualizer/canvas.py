import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, Gtk

from .model import WktEntry


class CanvasState:
    """Pan/zoom state with world↔screen coordinate transforms."""

    def __init__(self):
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def world_to_screen(self, wx, wy, height):
        sx = (wx - self.offset_x) * self.scale
        sy = height - (wy - self.offset_y) * self.scale
        return sx, sy

    def screen_to_world(self, sx, sy, height):
        wx = sx / self.scale + self.offset_x
        wy = (height - sy) / self.scale + self.offset_y
        return wx, wy

    def fit_bounds(self, minx, miny, maxx, maxy, width, height, padding=0.10):
        dx = maxx - minx
        dy = maxy - miny
        if dx < 1e-12 and dy < 1e-12:
            # Single point — use a fixed window
            self.scale = min(width, height) / 10.0
            self.offset_x = minx - 5.0
            self.offset_y = miny - 5.0
            return
        usable_w = width * (1 - 2 * padding)
        usable_h = height * (1 - 2 * padding)
        if usable_w < 1 or usable_h < 1:
            return
        self.scale = min(usable_w / max(dx, 1e-12), usable_h / max(dy, 1e-12))
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        self.offset_x = cx - (width / 2) / self.scale
        self.offset_y = cy - (height / 2) / self.scale


def _nice_interval(raw):
    """Round a raw interval to a 'nice' number: 1, 2, or 5 × 10^n."""
    if raw <= 0:
        return 1.0
    exp = math.floor(math.log10(raw))
    base = 10 ** exp
    frac = raw / base
    if frac <= 1.0:
        return base
    elif frac <= 2.0:
        return 2 * base
    elif frac <= 5.0:
        return 5 * base
    else:
        return 10 * base


class WktCanvas(Gtk.DrawingArea):
    """Cairo canvas for rendering WKT geometries with pan/zoom."""

    def __init__(self, displayed_store: Gio.ListStore):
        super().__init__()
        self.displayed_store = displayed_store
        self.state = CanvasState()
        self._cursor_x = 0.0
        self._cursor_y = 0.0
        self._pan_active = False
        self._pan_last_x = 0.0
        self._pan_last_y = 0.0

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_focusable(True)
        self.set_draw_func(self._on_draw)

        # Scroll → zoom (cursor-centered)
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll.connect("scroll", self._on_scroll)
        self.add_controller(scroll)

        # Middle-click press/release → toggle pan mode
        middle_click = Gtk.GestureClick.new()
        middle_click.set_button(2)
        middle_click.connect("pressed", self._on_pan_pressed)
        middle_click.connect("released", self._on_pan_released)
        self.add_controller(middle_click)

        # Right-click press/release → toggle pan mode
        right_click = Gtk.GestureClick.new()
        right_click.set_button(3)
        right_click.connect("pressed", self._on_pan_pressed)
        right_click.connect("released", self._on_pan_released)
        self.add_controller(right_click)

        # Motion → cursor coords + pan if active
        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)

        # Double-click → auto-fit
        click = Gtk.GestureClick.new()
        click.set_button(1)
        click.connect("released", self._on_click_released)
        self.add_controller(click)

        # Home key → auto-fit
        key = Gtk.EventControllerKey.new()
        key.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key)

    def auto_fit(self):
        w = self.get_width()
        h = self.get_height()
        if w < 1 or h < 1:
            return
        n = self.displayed_store.get_n_items()
        if n == 0:
            self.state = CanvasState()
            self.queue_draw()
            return
        minx = miny = float("inf")
        maxx = maxy = float("-inf")
        for i in range(n):
            entry = self.displayed_store.get_item(i)
            b = entry.geometry.bounds  # (minx, miny, maxx, maxy)
            minx = min(minx, b[0])
            miny = min(miny, b[1])
            maxx = max(maxx, b[2])
            maxy = max(maxy, b[3])
        self.state.fit_bounds(minx, miny, maxx, maxy, w, h)
        self.queue_draw()

    # -- Event handlers --

    def _on_scroll(self, _ctrl, _dx, dy):
        factor = 1.15 if dy < 0 else 1 / 1.15
        w = self.get_width()
        h = self.get_height()
        # Zoom centered on cursor
        wx, wy = self.state.screen_to_world(self._cursor_x, self._cursor_y, h)
        self.state.scale *= factor
        # Adjust offset so (wx, wy) stays at the same screen position
        self.state.offset_x = wx - self._cursor_x / self.state.scale
        self.state.offset_y = wy - (h - self._cursor_y) / self.state.scale
        self.queue_draw()
        return True

    def _on_pan_pressed(self, _gesture, _n_press, _x, _y):
        self._pan_active = True

    def _on_pan_released(self, _gesture, _n_press, _x, _y):
        self._pan_active = False

    def _pan_button_still_held(self):
        """Query the actual pointer modifier state — the gesture's
        `released` signal is unreliable because GestureClick denies its
        sequence on motion, so we check the live state instead."""
        root = self.get_root()
        if root is None:
            return False
        surface = root.get_surface()
        if surface is None:
            return False
        seat = self.get_display().get_default_seat()
        if seat is None:
            return False
        pointer = seat.get_pointer()
        if pointer is None:
            return False
        pos = surface.get_device_position(pointer)
        if not pos[0]:
            return False
        mods = pos[3]
        return bool(mods & (Gdk.ModifierType.BUTTON2_MASK
                            | Gdk.ModifierType.BUTTON3_MASK))

    def _on_motion(self, _ctrl, x, y):
        if self._pan_active:
            if self._pan_button_still_held():
                if self.state.scale > 1e-12:
                    dx = x - self._pan_last_x
                    dy = y - self._pan_last_y
                    self.state.offset_x -= dx / self.state.scale
                    self.state.offset_y += dy / self.state.scale
            else:
                self._pan_active = False
        self._pan_last_x = x
        self._pan_last_y = y
        self._cursor_x = x
        self._cursor_y = y
        self.queue_draw()

    def _on_click_released(self, gesture, n_press, _x, _y):
        if n_press == 2:
            self.auto_fit()

    def _on_key_pressed(self, _ctrl, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Home:
            self.auto_fit()
            return True
        return False

    # -- Drawing --

    def _on_draw(self, _area, cr, width, height):
        # White background
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        self._draw_grid(cr, width, height)
        self._draw_axes(cr, width, height)

        n = self.displayed_store.get_n_items()
        for i in range(n):
            entry = self.displayed_store.get_item(i)
            self._draw_geometry(cr, entry, width, height)

        self._draw_cursor_coords(cr, width, height)

    def _draw_grid(self, cr, width, height):
        s = self.state
        if s.scale < 1e-12:
            return

        # Compute nice interval: want ~5-10 grid lines across the view
        world_width = width / s.scale
        raw_interval = world_width / 8
        interval = _nice_interval(raw_interval)

        # World bounds of the view
        w_left = s.offset_x
        w_right = s.offset_x + width / s.scale
        w_bottom = s.offset_y
        w_top = s.offset_y + height / s.scale

        cr.set_source_rgba(0.85, 0.85, 0.85, 1)
        cr.set_line_width(0.5)

        # Vertical grid lines
        start_x = math.floor(w_left / interval) * interval
        x = start_x
        while x <= w_right:
            sx, _ = s.world_to_screen(x, 0, height)
            cr.move_to(sx, 0)
            cr.line_to(sx, height)
            cr.stroke()
            x += interval

        # Horizontal grid lines
        start_y = math.floor(w_bottom / interval) * interval
        y = start_y
        while y <= w_top:
            _, sy = s.world_to_screen(0, y, height)
            cr.move_to(0, sy)
            cr.line_to(width, sy)
            cr.stroke()
            y += interval

        # Labels
        cr.set_source_rgba(0.5, 0.5, 0.5, 1)
        cr.set_font_size(10)

        x = start_x
        while x <= w_right:
            sx, _ = s.world_to_screen(x, 0, height)
            label = _format_number(x)
            cr.move_to(sx + 2, height - 3)
            cr.show_text(label)
            x += interval

        y = start_y
        while y <= w_top:
            _, sy = s.world_to_screen(0, y, height)
            label = _format_number(y)
            cr.move_to(3, sy - 3)
            cr.show_text(label)
            y += interval

    def _draw_axes(self, cr, width, height):
        s = self.state
        cr.set_source_rgba(0.3, 0.3, 0.3, 1)
        cr.set_line_width(1.0)

        # X axis (y=0)
        _, sy = s.world_to_screen(0, 0, height)
        if 0 <= sy <= height:
            cr.move_to(0, sy)
            cr.line_to(width, sy)
            cr.stroke()

        # Y axis (x=0)
        sx, _ = s.world_to_screen(0, 0, height)
        if 0 <= sx <= width:
            cr.move_to(sx, 0)
            cr.line_to(sx, height)
            cr.stroke()

    def _draw_geometry(self, cr, entry: WktEntry, width, height):
        geom = entry.geometry
        geom_type = geom.geom_type

        if geom_type == "Point":
            self._draw_point(cr, entry, geom, width, height)
        elif geom_type == "LineString":
            self._draw_linestring(cr, entry, geom, width, height)
        elif geom_type == "Polygon":
            self._draw_polygon(cr, entry, geom, width, height)
        elif geom_type in ("MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"):
            self._draw_multi(cr, entry, geom, width, height)

    def _draw_point(self, cr, entry, geom, width, height):
        sx, sy = self.state.world_to_screen(geom.x, geom.y, height)
        r = entry.line_width * 2
        cr.arc(sx, sy, r, 0, 2 * math.pi)
        cr.set_source_rgba(entry.color_r, entry.color_g, entry.color_b, 1)
        cr.fill()

    def _draw_linestring(self, cr, entry, geom, width, height):
        coords = list(geom.coords)
        if len(coords) < 2:
            return
        sx, sy = self.state.world_to_screen(coords[0][0], coords[0][1], height)
        cr.move_to(sx, sy)
        for x, y in coords[1:]:
            sx, sy = self.state.world_to_screen(x, y, height)
            cr.line_to(sx, sy)
        cr.set_source_rgba(entry.color_r, entry.color_g, entry.color_b, 1)
        cr.set_line_width(entry.line_width)
        cr.stroke()

    def _draw_polygon(self, cr, entry, geom, width, height):
        # Exterior ring
        coords = list(geom.exterior.coords)
        if len(coords) < 3:
            return
        sx, sy = self.state.world_to_screen(coords[0][0], coords[0][1], height)
        cr.move_to(sx, sy)
        for x, y in coords[1:]:
            sx, sy = self.state.world_to_screen(x, y, height)
            cr.line_to(sx, sy)
        cr.close_path()

        # Interior rings (holes)
        for interior in geom.interiors:
            hole_coords = list(interior.coords)
            if len(hole_coords) < 3:
                continue
            sx, sy = self.state.world_to_screen(hole_coords[0][0], hole_coords[0][1], height)
            cr.move_to(sx, sy)
            for x, y in hole_coords[1:]:
                sx, sy = self.state.world_to_screen(x, y, height)
                cr.line_to(sx, sy)
            cr.close_path()

        # Fill with even-odd rule for holes
        import cairo

        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.set_source_rgba(entry.color_r, entry.color_g, entry.color_b, entry.fill_opacity)
        cr.fill_preserve()
        cr.set_fill_rule(cairo.FILL_RULE_WINDING)

        # Stroke
        cr.set_source_rgba(entry.color_r, entry.color_g, entry.color_b, 1)
        cr.set_line_width(entry.line_width)
        cr.stroke()

    def _draw_multi(self, cr, entry, geom, width, height):
        for sub in geom.geoms:
            sub_type = sub.geom_type
            if sub_type == "Point":
                self._draw_point(cr, entry, sub, width, height)
            elif sub_type == "LineString":
                self._draw_linestring(cr, entry, sub, width, height)
            elif sub_type == "Polygon":
                self._draw_polygon(cr, entry, sub, width, height)
            elif sub_type in ("MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"):
                self._draw_multi(cr, entry, sub, width, height)

    def _draw_cursor_coords(self, cr, width, height):
        wx, wy = self.state.screen_to_world(self._cursor_x, self._cursor_y, height)
        text = f"({wx:.4f}, {wy:.4f})"
        cr.set_font_size(11)
        extents = cr.text_extents(text)
        x = width - extents.width - 8
        y = height - 8
        # Background for readability
        cr.set_source_rgba(1, 1, 1, 0.8)
        cr.rectangle(x - 4, y - extents.height - 2, extents.width + 8, extents.height + 6)
        cr.fill()
        cr.set_source_rgba(0.2, 0.2, 0.2, 1)
        cr.move_to(x, y)
        cr.show_text(text)


def _format_number(v):
    """Format a grid number concisely."""
    if v == 0:
        return "0"
    if abs(v) >= 1:
        if v == int(v):
            return str(int(v))
        return f"{v:.1f}"
    return f"{v:.4g}"
