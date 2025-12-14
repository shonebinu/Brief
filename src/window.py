import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk
from .tldr import PageManager
from .renderer import CommandPage
from .sidebar import BriefSidebar, CommandItem


@Gtk.Template(resource_path="/com/shonebinu/Brief/window.ui")
class BriefWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BriefWindow"

    content_stack = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    navigation_page = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.manager = PageManager()

        self.sidebar = BriefSidebar(self.manager)
        self.sidebar.connect("command-activated", self.on_command_selected)

        self.split_view.set_sidebar(self.sidebar)

        self.command_view = CommandPage()
        self.content_stack.add_named(self.command_view, "content")

    def on_command_selected(self, sidebar, item: CommandItem):
        self.load_command_page(item)

    def load_command_page(self, item: CommandItem):
        raw_text = self.manager.get_page(item.language, item.platform, item.name)

        if raw_text:
            self.navigation_page.set_title(item.name)
            self.content_stack.set_visible_child_name("content")
            self.command_view.display_content(
                raw_text, self.manager.settings.get_string("format")
            )
            self.split_view.set_show_content(True)
