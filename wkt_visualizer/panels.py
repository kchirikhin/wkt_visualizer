import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gtk

from .model import WktEntry


def _insert_ordered(store: Gio.ListStore, entry: WktEntry):
    """Insert entry maintaining (group_index, entry_id) ordering."""
    key = (entry.group_index, entry.entry_id)
    for i in range(store.get_n_items()):
        item = store.get_item(i)
        if (item.group_index, item.entry_id) > key:
            store.insert(i, entry)
            return
    store.append(entry)


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

        # Detect if any entry has a group
        self._has_groups = any(
            displayed_store.get_item(i).group
            for i in range(displayed_store.get_n_items())
        )

        # -- Displayed list --
        displayed_label = Gtk.Label(label="Displayed")
        displayed_label.add_css_class("heading")
        displayed_label.set_margin_top(4)
        displayed_label.set_margin_bottom(2)
        self.append(displayed_label)

        self.displayed_list = Gtk.ListBox()
        self.displayed_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.displayed_list.bind_model(displayed_store, _create_row_widget)
        self.displayed_list.connect("row-selected", self._on_displayed_selected)
        if self._has_groups:
            self.displayed_list.set_header_func(
                self._header_func, "hide"
            )

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

        hide_all_btn = Gtk.Button(label="Hide All")
        hide_all_btn.connect("clicked", self._on_hide_all_clicked)
        button_box.append(hide_all_btn)

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
        self.hidden_list.connect("row-selected", self._on_hidden_selected)
        if self._has_groups:
            self.hidden_list.set_header_func(
                self._header_func, "show"
            )

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
        _insert_ordered(to_store, entry)
        if self._has_groups:
            self.displayed_list.invalidate_headers()
            self.hidden_list.invalidate_headers()
        self._on_visibility_changed()

    # -- Displayed list handlers --

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

    def _on_hidden_selected(self, _listbox, row):
        if row is not None:
            self.displayed_list.unselect_all()
            idx = row.get_index()
            if 0 <= idx < self.hidden_store.get_n_items():
                self._on_selection_changed(self.hidden_store.get_item(idx))
                return
        if self.displayed_list.get_selected_row() is None:
            self._on_selection_changed(None)

    # -- Group headers --

    def _header_func(self, row, before, action):
        """Add group header when group changes between rows."""
        idx = row.get_index()
        store = self.displayed_store if action == "hide" else self.hidden_store
        if idx < 0 or idx >= store.get_n_items():
            row.set_header(None)
            return
        entry = store.get_item(idx)
        if not entry.group:
            # Check if previous row had a different group
            if before is not None:
                prev_idx = before.get_index()
                if 0 <= prev_idx < store.get_n_items():
                    prev_entry = store.get_item(prev_idx)
                    if prev_entry.group:
                        # Transition from grouped to ungrouped — no header needed
                        pass
            row.set_header(None)
            return

        need_header = True
        if before is not None:
            prev_idx = before.get_index()
            if 0 <= prev_idx < store.get_n_items():
                prev_entry = store.get_item(prev_idx)
                if prev_entry.group_index == entry.group_index:
                    need_header = False

        if not need_header:
            row.set_header(None)
            return

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header_box.set_margin_start(4)
        header_box.set_margin_end(4)
        header_box.set_margin_top(6)
        header_box.set_margin_bottom(2)

        label = Gtk.Label(label=entry.group)
        label.set_xalign(0)
        label.set_hexpand(True)
        label.add_css_class("heading")
        header_box.append(label)

        btn_label = "Hide All" if action == "hide" else "Show All"
        btn = Gtk.Button(label=btn_label)
        btn.add_css_class("flat")
        gi = entry.group_index
        if action == "hide":
            btn.connect("clicked", lambda _b, g=gi: self._on_hide_group(g))
        else:
            btn.connect("clicked", lambda _b, g=gi: self._on_show_group(g))
        header_box.append(btn)

        row.set_header(header_box)

    def _on_hide_group(self, group_index):
        """Move all entries with matching group_index from displayed to hidden."""
        to_move = []
        for i in range(self.displayed_store.get_n_items()):
            entry = self.displayed_store.get_item(i)
            if entry.group_index == group_index:
                to_move.append(entry)
        for entry in to_move:
            for i in range(self.displayed_store.get_n_items()):
                if self.displayed_store.get_item(i) is entry:
                    self.displayed_store.remove(i)
                    _insert_ordered(self.hidden_store, entry)
                    break
        if to_move:
            self.displayed_list.invalidate_headers()
            self.hidden_list.invalidate_headers()
            self._on_visibility_changed()

    def _on_show_group(self, group_index):
        """Move all entries with matching group_index from hidden to displayed."""
        to_move = []
        for i in range(self.hidden_store.get_n_items()):
            entry = self.hidden_store.get_item(i)
            if entry.group_index == group_index:
                to_move.append(entry)
        for entry in to_move:
            for i in range(self.hidden_store.get_n_items()):
                if self.hidden_store.get_item(i) is entry:
                    self.hidden_store.remove(i)
                    _insert_ordered(self.displayed_store, entry)
                    break
        if to_move:
            self.displayed_list.invalidate_headers()
            self.hidden_list.invalidate_headers()
            self._on_visibility_changed()

    # -- Button handlers --

    def _on_hide_clicked(self, _btn):
        entry, idx = self._get_selected_entry(self.displayed_list, self.displayed_store)
        if entry is not None:
            self._move_entry(self.displayed_store, self.hidden_store, idx)

    def _on_show_clicked(self, _btn):
        entry, idx = self._get_selected_entry(self.hidden_list, self.hidden_store)
        if entry is not None:
            self._move_entry(self.hidden_store, self.displayed_store, idx)

    def _on_hide_all_clicked(self, _btn):
        while self.displayed_store.get_n_items() > 0:
            entry = self.displayed_store.get_item(0)
            self.displayed_store.remove(0)
            _insert_ordered(self.hidden_store, entry)
        self._on_visibility_changed()

    def _on_show_all_clicked(self, _btn):
        while self.hidden_store.get_n_items() > 0:
            entry = self.hidden_store.get_item(0)
            self.hidden_store.remove(0)
            _insert_ordered(self.displayed_store, entry)
        self._on_visibility_changed()
