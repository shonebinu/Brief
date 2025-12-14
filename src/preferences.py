import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio
from .tldr import PageManager


@Gtk.Template(resource_path="/com/shonebinu/Brief/preferences.ui")
class BriefPreferencesWindow(Adw.PreferencesDialog):
    __gtype_name__ = "BriefPreferencesWindow"

    platform_group = Gtk.Template.Child()
    language_group = Gtk.Template.Child()
    format_row = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.settings = Gio.Settings.new("io.github.shonebinu.Brief")
        self.manager = PageManager()

        self.setup_expander(
            self.platform_group, "platforms", self.manager.get_available_platforms()
        )
        self.setup_expander(
            self.language_group, "languages", self.manager.get_available_languages()
        )

        self.setup_combo(
            self.format_row,
            "format",
            names=["Long Arguments (--all)", "Short Arguments (-a)"],
            codes=["long", "short"],
        )

    def setup_expander(self, expander_row, key, items):
        current_selection = self.settings.get_strv(key)

        for label, code in items:
            row = Adw.SwitchRow(title=label, active=code in current_selection)
            row.connect("notify::active", self.on_list_toggled, key, code)
            expander_row.add_row(row)

    def on_list_toggled(self, row, param, key, code):
        current_list = list(self.settings.get_strv(key))
        is_active = row.get_active()

        if is_active:
            if code not in current_list:
                current_list.append(code)
        else:
            if code in current_list:
                current_list.remove(code)

        self.settings.set_strv(key, current_list)

    def setup_combo(self, row, key, names, codes):
        row.set_model(Gtk.StringList.new(names))

        current_val = self.settings.get_string(key)
        if current_val in codes:
            row.set_selected(codes.index(current_val))

        row.connect(
            "notify::selected",
            lambda *_: self.settings.set_string(key, codes[row.get_selected()]),
        )
