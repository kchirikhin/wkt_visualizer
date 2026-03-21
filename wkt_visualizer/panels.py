import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gtk

from .model import WktEntry


def _create_color_swatch(entry: WktEntry) -> Gtk.DrawingArea:
    da = Gtk.DrawingArea()
    da.set_size_request(16, 16)

    def draw(_area, cr, w, h):
        cr.set_source_rgb(entry.color_r, entry.color_g, entry.color_b)
        cr.rectangle(0, 0, w, h)
        cr.fill()

    da.set_draw_func(draw)

    def on_color_changed(*_args):
        da.queue_draw()

    entry.connect("notify::color-r", on_color_changed)
    entry.connect("notify::color-g", on_color_changed)
    entry.connect("notify::color-b", on_color_changed)

    return da


def _create_row_widget(entry: WktEntry) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    box.set_margin_start(4)
    box.set_margin_end(4)
    box.set_margin_top(2)
    box.set_margin_bottom(2)

    swatch = _create_color_swatch(entry)
    swatch.set_valign(Gtk.Align.CENTER)
    box.append(swatch)

    type_label = Gtk.Label(label=entry.geometry.geom_type)
    type_label.add_css_class("dim-label")
    type_label.set_width_chars(12)
    type_label.set_xalign(0)
    box.append(type_label)

    name_label = Gtk.Label()
    name_label.set_xalign(0)
    name_label.set_hexpand(True)
    name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
    entry.bind_property("name", name_label, "label", GObject.BindingFlags.SYNC_CREATE)
    box.append(name_label)

    return box


class GeometryPanels(Gtk.Box):
    """Two-list panel: Hidden and Displayed geometry lists with transfer controls."""

    def __init__(
        self,
        hidden_store: Gio.ListStore,
        displayed_store: Gio.ListStore,
        on_visibility_changed,
        on_selection_changed,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.hidden_store = hidden_store
        self.displayed_store = displayed_store
        self._on_visibility_changed = on_visibility_changed
        self._on_selection_changed = on_selection_changed

        self.set_size_request(260, -1)

        # -- Displayed list --
        displayed_label = Gtk.Label(label="Displayed")
        displayed_label.add_css_class("heading")
        displayed_label.set_margin_top(4)
        displayed_label.set_margin_bottom(2)
        self.append(displayed_label)

        self.displayed_list = Gtk.ListBox()
        self.displayed_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.displayed_list.bind_model(displayed_store, _create_row_widget)
        self.displayed_list.connect("row-activated", self._on_displayed_activated)
        self.displayed_list.connect("row-selected", self._on_displayed_selected)

        displayed_scroll = Gtk.ScrolledWindow()
        displayed_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        displayed_scroll.set_vexpand(True)
        displayed_scroll.set_child(self.displayed_list)
        self.append(displayed_scroll)

        # -- Buttons --
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        button_box.set_margin_start(4)
        button_box.set_margin_end(4)
        button_box.set_margin_top(4)
        button_box.set_margin_bottom(4)
        button_box.set_halign(Gtk.Align.CENTER)

        hide_btn = Gtk.Button(label="Hide")
        hide_btn.connect("clicked", self._on_hide_clicked)
        button_box.append(hide_btn)

        show_btn = Gtk.Button(label="Show")
        show_btn.connect("clicked", self._on_show_clicked)
        button_box.append(show_btn)

        show_all_btn = Gtk.Button(label="Show All")
        show_all_btn.connect("clicked", self._on_show_all_clicked)
        button_box.append(show_all_btn)

        self.append(button_box)

        # -- Hidden list --
        hidden_label = Gtk.Label(label="Hidden")
        hidden_label.add_css_class("heading")
        hidden_label.set_margin_top(2)
        hidden_label.set_margin_bottom(2)
        self.append(hidden_label)

        self.hidden_list = Gtk.ListBox()
        self.hidden_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.hidden_list.bind_model(hidden_store, _create_row_widget)
        self.hidden_list.connect("row-activated", self._on_hidden_activated)
        self.hidden_list.connect("row-selected", self._on_hidden_selected)

        hidden_scroll = Gtk.ScrolledWindow()
        hidden_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        hidden_scroll.set_vexpand(True)
        hidden_scroll.set_child(self.hidden_list)
        self.append(hidden_scroll)

    def _get_selected_entry(self, listbox: Gtk.ListBox, store: Gio.ListStore):
        row = listbox.get_selected_row()
        if row is None:
            return None, -1
        idx = row.get_index()
        if idx < 0 or idx >= store.get_n_items():
            return None, -1
        return store.get_item(idx), idx

    def _move_entry(self, from_store, to_store, index):
        entry = from_store.get_item(index)
        from_store.remove(index)
        to_store.append(entry)
        self._on_visibility_changed()

    # -- Displayed list handlers --

    def _on_displayed_activated(self, _listbox, row):
        idx = row.get_index()
        if idx >= 0:
            self._move_entry(self.displayed_store, self.hidden_store, idx)

    def _on_displayed_selected(self, _listbox, row):
        if row is not None:
            self.hidden_list.unselect_all()
            idx = row.get_index()
            if 0 <= idx < self.displayed_store.get_n_items():
                self._on_selection_changed(self.displayed_store.get_item(idx))
                return
        # Check if hidden has selection
        if self.hidden_list.get_selected_row() is None:
            self._on_selection_changed(None)

    # -- Hidden list handlers --

    def _on_hidden_activated(self, _listbox, row):
        idx = row.get_index()
        if idx >= 0:
            self._move_entry(self.hidden_store, self.displayed_store, idx)

    def _on_hidden_selected(self, _listbox, row):
        if row is not None:
            self.displayed_list.unselect_all()
            idx = row.get_index()
            if 0 <= idx < self.hidden_store.get_n_items():
                self._on_selection_changed(self.hidden_store.get_item(idx))
                return
        if self.displayed_list.get_selected_row() is None:
            self._on_selection_changed(None)

    # -- Button handlers --

    def _on_hide_clicked(self, _btn):
        entry, idx = self._get_selected_entry(self.displayed_list, self.displayed_store)
        if entry is not None:
            self._move_entry(self.displayed_store, self.hidden_store, idx)

    def _on_show_clicked(self, _btn):
        entry, idx = self._get_selected_entry(self.hidden_list, self.hidden_store)
        if entry is not None:
            self._move_entry(self.hidden_store, self.displayed_store, idx)

    def _on_show_all_clicked(self, _btn):
        while self.hidden_store.get_n_items() > 0:
            entry = self.hidden_store.get_item(0)
            self.hidden_store.remove(0)
            self.displayed_store.append(entry)
        self._on_visibility_changed()
