import gi

from .renderer import CommandPage
from .sidebar import BriefSidebar, CommandItem
from .tldr import PageManager

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio


@Gtk.Template(resource_path="/io/github/shonebinu/Brief/window.ui")
class BriefWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BriefWindow"

    toast_overlay = Gtk.Template.Child()
    content_stack = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    navigation_page = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.manager = PageManager()
        self.current_item = None

        self.sidebar = BriefSidebar(self.manager, self.toast_overlay)
        self.sidebar.connect("command-activated", self.on_command_selected)

        self.split_view.set_sidebar(self.sidebar)

        self.command_view = CommandPage(self.toast_overlay)
        self.content_stack.add_named(self.command_view, "content")

        self.manager.settings.connect("changed", self.on_settings_changed)

        self.setup_actions()

    def setup_actions(self):
        action = Gio.SimpleAction.new("update_cache", None)
        action.connect("activate", self.on_update_cache_action)
        self.add_action(action)

    def on_update_cache_action(self, action, param):
        self.sidebar.start_update_process()

    def on_command_selected(self, sidebar, item: CommandItem):
        self.load_command_page(item)

    def load_command_page(self, item: CommandItem):
        self.current_item = item

        raw_text = self.manager.get_page(item.language, item.platform, item.name)

        if raw_text:
            self.navigation_page.set_title(item.name)
            self.content_stack.set_visible_child_name("content")
            self.command_view.display_content(
                raw_text, self.manager.settings.get_string("format")
            )
            self.split_view.set_show_content(True)

    def on_settings_changed(self, settings, key):
        if self.current_item and self.split_view.get_show_content():
            self.load_command_page(self.current_item)
