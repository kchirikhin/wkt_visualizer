import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from .canvas import WktCanvas
from .model import WktEntry
from .panels import GeometryPanels
from .properties import PropertiesBar


class WktVisualizerWindow(Gtk.ApplicationWindow):
    def __init__(self, app, entries: list[WktEntry]):
        super().__init__(application=app, title="WKT Visualizer")
        self.set_default_size(1100, 700)

        self._selected_entry = None
        self._notify_handlers = []

        # Stores: all entries start in displayed
        self.hidden_store = Gio.ListStore.new(WktEntry)
        self.displayed_store = Gio.ListStore.new(WktEntry)
        for entry in entries:
            self.displayed_store.append(entry)

        # Main vertical layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(vbox)

        # Horizontal paned: panels | canvas
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        vbox.append(paned)

        # Left: panels
        self.panels = GeometryPanels(
            self.hidden_store,
            self.displayed_store,
            on_visibility_changed=self._on_visibility_changed,
            on_selection_changed=self._on_selection_changed,
        )
        paned.set_start_child(self.panels)
        paned.set_resize_start_child(False)
        paned.set_shrink_start_child(False)

        # Right: canvas
        self.canvas = WktCanvas(self.displayed_store)
        paned.set_end_child(self.canvas)
        paned.set_resize_end_child(True)
        paned.set_shrink_end_child(False)

        # Bottom: properties bar
        self.properties = PropertiesBar(on_changed=self._on_property_changed)
        vbox.append(self.properties)

        # Deferred auto-fit after window is mapped and sized
        self.connect("map", self._on_map)

    def _on_map(self, _widget):
        GLib.idle_add(self.canvas.auto_fit)

    def _on_visibility_changed(self):
        self.canvas.auto_fit()

    def _on_selection_changed(self, entry: WktEntry | None):
        # Disconnect previous notify handlers
        if self._selected_entry is not None:
            for hid in self._notify_handlers:
                self._selected_entry.disconnect(hid)
        self._notify_handlers.clear()

        self._selected_entry = entry
        self.properties.bind_entry(entry)

        if entry is not None:
            for prop in ("color-r", "color-g", "color-b", "line-width", "fill-opacity", "name"):
                hid = entry.connect(f"notify::{prop}", self._on_entry_notify)
                self._notify_handlers.append(hid)

    def _on_entry_notify(self, _entry, _pspec):
        self.canvas.queue_draw()

    def _on_property_changed(self):
        self.canvas.queue_draw()


class WktVisualizerApp(Gtk.Application):
    def __init__(self, entries: list[WktEntry]):
        super().__init__(
            application_id="com.github.wkt_visualizer",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self._entries = entries

    def do_activate(self):
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-icon-theme-name", "Adwaita")
        win = WktVisualizerWindow(self, self._entries)
        win.present()
