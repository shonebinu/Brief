import gi
import random
from rapidfuzz import fuzz, utils
from functools import lru_cache

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GObject, Gtk, Pango, GLib


class CommandItem(GObject.Object):
    __gtype_name__ = "CommandItem"

    name = GObject.Property(type=str)
    platform = GObject.Property(type=str)
    language = GObject.Property(type=str)

    def __init__(self, name, platform, language):
        super().__init__()
        self.name = name
        self.platform = platform
        self.language = language


@Gtk.Template(resource_path="/io/github/shonebinu/Brief/sidebar.ui")
class BriefSidebar(Adw.NavigationPage):
    __gtype_name__ = "BriefSidebar"

    search_entry = Gtk.Template.Child()

    list_view = Gtk.Template.Child()
    selection_model = Gtk.Template.Child()
    list_store = Gtk.Template.Child()
    sorter = Gtk.Template.Child()
    filter = Gtk.Template.Child()

    progress_revealer = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()
    status_label = Gtk.Template.Child()

    def __init__(self, manager, load_command_page, toast_overlay, **kwargs):
        super().__init__(**kwargs)

        self.manager = manager
        self.load_command_page = load_command_page
        self.toast_overlay = toast_overlay

        self.is_updating = False
        self.timeout_id = None

        self.process_commands()

        self.setup_shortcuts()

        self.manager.settings.connect("changed", self.refresh_data)

    def setup_shortcuts(self):
        shortcut_controller = Gtk.ShortcutController(scope=Gtk.ShortcutScope.MANAGED)
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>k")
        action = Gtk.CallbackAction.new(
            lambda *_: (self.search_entry.grab_focus(), True)[1]
        )
        shortcut = Gtk.Shortcut.new(trigger, action)
        shortcut_controller.add_shortcut(shortcut)
        self.add_controller(shortcut_controller)

    def process_commands(self):
        commands_map = self.manager.get_all_commands()
        command_items = [
            CommandItem(cmd, platform, lang)
            for lang, platforms in commands_map.items()
            for platform, cmd_list in platforms.items()
            for cmd in cmd_list
        ]

        random.shuffle(command_items)

        self.list_store.remove_all()
        self.list_store.splice(0, 0, command_items)

    @lru_cache(maxsize=30000)
    def get_fuzzy_score(self, cmd_name, search_text):
        score = fuzz.ratio(cmd_name, search_text, processor=utils.default_process)
        return int(score * 100)

    @Gtk.Template.Callback()
    def sort_commands(self, _obj, cmd_name, search_text):
        if not search_text:
            return 0

        return self.get_fuzzy_score(cmd_name, search_text)

    @Gtk.Template.Callback()
    def filter_commands(self, _obj, cmd_name, search_text):
        if not search_text:
            return True

        return self.get_fuzzy_score(cmd_name, search_text) >= 30 * 100

    @Gtk.Template.Callback()
    def on_search_changed(self, *args):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self.sorter.changed(Gtk.SorterChange.DIFFERENT)
        if self.selection_model.get_n_items() > 0:
            self.list_view.scroll_to(0, Gtk.ListScrollFlags.NONE, None)

    @Gtk.Template.Callback()
    def on_list_item_activated(self, list_view, position):
        item = self.selection_model.get_item(position)
        if item:
            self.load_command_page(item)

    @Gtk.Template.Callback()
    def on_search_activate(self, *args):
        if self.selection_model.get_n_items() > 0:
            item = self.selection_model.get_item(0)
            if item:
                self.selection_model.set_selected(0)
                self.load_command_page(item)

    def refresh_data(self, *args):
        self.process_commands()
        self.selection_model.set_selected(Gtk.INVALID_LIST_POSITION)

    def start_update_process(self):
        if self.is_updating:
            toast = Adw.Toast.new("An update process is already going on")
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)
            return

        self.is_updating = True

        self.progress_revealer.set_reveal_child(True)
        self.status_label.set_label("Preparing...")

        self.timeout_id = GLib.timeout_add(100, self.pulse)

        self.manager.update_cache(
            progress_cb=self.on_update_progress, finished_cb=self.on_update_finished
        )

    def on_update_progress(self, fraction, text):
        self.status_label.set_label(text)
        if fraction >= 0:
            if self.timeout_id:
                GLib.source_remove(self.timeout_id)
                self.timeout_id = None
            self.progress_bar.set_fraction(fraction)
        else:
            if self.timeout_id is None:
                self.progress_bar.set_fraction(0.0)
                self.timeout_id = GLib.timeout_add(100, self.pulse)

    def pulse(self):
        self.progress_bar.pulse()
        return True

    def on_update_finished(self, success, message):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

        self.progress_revealer.set_reveal_child(False)
        self.progress_bar.set_fraction(0.0)

        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

        if success:
            self.refresh_data()

        self.is_updating = False
