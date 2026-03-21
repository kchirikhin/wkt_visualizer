import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GObject, Gtk

from .model import WktEntry


class PropertiesBar(Gtk.Box):
    """Bottom bar showing properties of the selected WktEntry."""

    def __init__(self, on_changed):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._on_changed = on_changed
        self._entry = None
        self._bindings = []
        self._widget_handlers = []  # list of (widget, handler_id)

        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        # Name entry
        name_label = Gtk.Label(label="Name:")
        self.append(name_label)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_width_chars(16)
        self.append(self._name_entry)

        # Color button
        color_label = Gtk.Label(label="Color:")
        self.append(color_label)
        self._color_btn = Gtk.ColorButton()
        self._color_btn.set_use_alpha(False)
        self.append(self._color_btn)

        # Line width slider
        width_label = Gtk.Label(label="Width:")
        self.append(width_label)
        self._width_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 1, 10, 0.5
        )
        self._width_scale.set_size_request(100, -1)
        self._width_scale.set_draw_value(True)
        self.append(self._width_scale)

        # Fill opacity slider
        opacity_label = Gtk.Label(label="Opacity:")
        self.append(opacity_label)
        self._opacity_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 1, 0.05
        )
        self._opacity_scale.set_size_request(100, -1)
        self._opacity_scale.set_draw_value(True)
        self.append(self._opacity_scale)

        # WKT text
        self._wkt_label = Gtk.Label()
        self._wkt_label.set_hexpand(True)
        self._wkt_label.set_xalign(0)
        self._wkt_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self._wkt_label.set_selectable(True)
        self.append(self._wkt_label)

        self.set_visible(False)

    def bind_entry(self, entry: WktEntry | None):
        # Unbind previous
        for binding in self._bindings:
            binding.unbind()
        self._bindings.clear()

        for widget, hid in self._widget_handlers:
            widget.disconnect(hid)
        self._widget_handlers.clear()

        self._entry = entry

        if entry is None:
            self.set_visible(False)
            return

        self.set_visible(True)

        # Name: bidirectional binding
        b = entry.bind_property(
            "name",
            self._name_entry,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self._bindings.append(b)

        # Color: set initial value, then connect signal
        rgba = Gdk.RGBA()
        rgba.red = entry.color_r
        rgba.green = entry.color_g
        rgba.blue = entry.color_b
        rgba.alpha = 1.0
        self._color_btn.set_rgba(rgba)

        def on_color_set(_btn):
            c = self._color_btn.get_rgba()
            entry.color_r = c.red
            entry.color_g = c.green
            entry.color_b = c.blue
            self._on_changed()

        hid = self._color_btn.connect("color-set", on_color_set)
        self._widget_handlers.append((self._color_btn, hid))

        # Width slider
        self._width_scale.set_value(entry.line_width)

        def on_width_changed(_scale):
            entry.line_width = self._width_scale.get_value()
            self._on_changed()

        hid = self._width_scale.connect("value-changed", on_width_changed)
        self._widget_handlers.append((self._width_scale, hid))

        # Opacity slider
        self._opacity_scale.set_value(entry.fill_opacity)

        def on_opacity_changed(_scale):
            entry.fill_opacity = self._opacity_scale.get_value()
            self._on_changed()

        hid = self._opacity_scale.connect("value-changed", on_opacity_changed)
        self._widget_handlers.append((self._opacity_scale, hid))

        # WKT text
        wkt_display = entry.wkt
        if len(wkt_display) > 200:
            wkt_display = wkt_display[:200] + "..."
        self._wkt_label.set_text(wkt_display)

