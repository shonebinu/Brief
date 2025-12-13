import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio, Pango, GObject
from .tldr import PageManager
from .renderer import CommandPage


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


class CommandListRow(Gtk.Box):

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_start=8,
            margin_end=8,
            margin_top=8,
            margin_bottom=8,
        )

        self.name_label = Gtk.Label(
            xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END
        )
        self.append(self.name_label)

        self.plat_box = Gtk.Box(spacing=4, css_classes=["dim-label"])
        self.plat_box.append(Gtk.Image(icon_name="computer-symbolic"))
        self.plat_label = Gtk.Label(css_classes=["caption"])
        self.plat_box.append(self.plat_label)
        self.append(self.plat_box)

        self.lang_box = Gtk.Box(spacing=4, css_classes=["dim-label"])
        self.lang_box.append(Gtk.Image(icon_name="preferences-desktop-locale-symbolic"))
        self.lang_label = Gtk.Label(css_classes=["caption"])
        self.lang_box.append(self.lang_label)
        self.append(self.lang_box)

    def bind(self, item: CommandItem):
        self.name_label.set_label(item.name)
        self.plat_label.set_label(item.platform)
        self.lang_label.set_label(item.language)


@Gtk.Template(resource_path="/com/shonebinu/Brief/window.ui")
class BriefWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BriefWindow"

    content_stack = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    results_list_view = Gtk.Template.Child()
    item_factory = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    navigation_page = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.manager = PageManager()
        self.list_store = Gio.ListStore(item_type=CommandItem)

        self.command_view = CommandPage()
        self.content_stack.add_named(self.command_view, "content")

        self.item_factory.connect("setup", self._on_factory_setup)
        self.item_factory.connect("bind", self._on_factory_bind)

        self.process_commands()
        self.setup_models()

        self.manager.settings.connect("changed", self.refresh_data)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", self.on_search_activate)
        self.results_list_view.connect("activate", self.on_list_item_activated)

    def _on_factory_setup(self, _factory, list_item):
        list_item.set_child(CommandListRow())

    def _on_factory_bind(self, _factory, list_item):
        row_widget = list_item.get_child()
        item = list_item.get_item()
        row_widget.bind(item)

    def process_commands(self):
        commands_map = self.manager.get_all_commands()
        command_items = [
            CommandItem(cmd, platform, lang)
            for lang, platforms in commands_map.items()
            for platform, cmd_list in platforms.items()
            for cmd in cmd_list
        ]
        command_items.sort(key=lambda x: x.name)

        self.list_store.remove_all()
        self.list_store.splice(0, 0, command_items)

    def setup_models(self):
        self.filter = Gtk.CustomFilter.new(match_func=self.filter_func)
        self.filter_model = Gtk.FilterListModel(
            model=self.list_store, filter=self.filter
        )

        self.sorter = Gtk.CustomSorter.new(sort_func=self.sort_func)
        self.sort_model = Gtk.SortListModel(model=self.filter_model, sorter=self.sorter)

        self.selection_model = Gtk.SingleSelection(
            model=self.sort_model, autoselect=False, selected=Gtk.INVALID_LIST_POSITION
        )

        self.results_list_view.set_model(self.selection_model)

    def refresh_data(self, *args):
        self.process_commands()
        self.selection_model.set_selected(Gtk.INVALID_LIST_POSITION)

    def on_search_changed(self, _entry):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self.sorter.changed(Gtk.SorterChange.DIFFERENT)

    def on_search_activate(self, _entry):
        if self.selection_model.get_n_items() > 0:
            self.selection_model.set_selected(0)
            selected_item = self.selection_model.get_selected_item()
            if selected_item:
                self.load_command_page(selected_item)

    def on_list_item_activated(self, list_view, position):
        item = self.selection_model.get_item(position)
        if item:
            self.load_command_page(item)

    def filter_func(self, item, *args):
        query = self.search_entry.get_text().lower()
        return not query or query in item.name.lower()

    def sort_func(self, item1, item2, *args):
        query = self.search_entry.get_text().lower()
        if not query:
            return (item1.name.lower() > item2.name.lower()) - (
                item1.name.lower() < item2.name.lower()
            )

        s1, s2 = item1.name.lower(), item2.name.lower()

        def rank(s):
            return 0 if s == query else 1 if s.startswith(query) else 2

        return (rank(s1) - rank(s2)) or (s1 > s2) - (s1 < s2)

    def load_command_page(self, item: CommandItem):
        raw_text = self.manager.get_page(item.language, item.platform, item.name)

        if raw_text:
            self.navigation_page.set_title(item.name)
            self.content_stack.set_visible_child_name("content")
            self.command_view.display_content(
                raw_text, self.manager.settings.get_string("format")
            )
            self.split_view.set_show_content(True)
