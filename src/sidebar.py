import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GObject, Gtk, Pango, GLib


class CommandItem(GObject.Object):
    __gtype_name__ = "CommandItem"

    name = GObject.Property(type=str)
    platform = GObject.Property(type=str)
    language = GObject.Property(type=str)
    search_key = GObject.Property(type=str)

    def __init__(self, name, platform, language):
        super().__init__()
        self.name = name
        self.platform = platform
        self.language = language
        self.search_key = name.lower().replace(" ", "").replace("-", "")


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


@Gtk.Template(resource_path="/io/github/shonebinu/Brief/sidebar.ui")
class BriefSidebar(Adw.NavigationPage):
    __gtype_name__ = "BriefSidebar"

    __gsignals__ = {
        "command-activated": (GObject.SignalFlags.RUN_FIRST, None, (CommandItem,)),
    }

    search_entry = Gtk.Template.Child()
    results_list_view = Gtk.Template.Child()
    item_factory = Gtk.Template.Child()

    progress_revealer = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()
    status_label = Gtk.Template.Child()

    def __init__(self, manager, toast_overlay, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
        self.toast_overlay = toast_overlay

        self.list_store = Gio.ListStore(item_type=CommandItem)

        self.item_factory.connect("setup", lambda _, li: li.set_child(CommandListRow()))
        self.item_factory.connect(
            "bind", lambda _, li: li.get_child().bind(li.get_item())
        )

        self.process_commands()
        self.setup_models()

        self.manager.settings.connect("changed", self.refresh_data)
        self.search_entry.connect("activate", self.on_search_activate)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.results_list_view.connect("activate", self.on_list_item_activated)

        self.is_updating = False
        self.timeout_id = None

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
        name_expression = Gtk.PropertyExpression.new(CommandItem, None, "name")

        self.filter = Gtk.CustomFilter.new(match_func=self.filter_func)
        self.filter_model = Gtk.FilterListModel(
            model=self.list_store, filter=self.filter
        )

        multi_sorter = Gtk.MultiSorter()

        self.rank_sorter = Gtk.CustomSorter.new(self.sort_by_relevance)
        multi_sorter.append(self.rank_sorter)

        alpha_sorter = Gtk.StringSorter(expression=name_expression)
        multi_sorter.append(alpha_sorter)

        self.sort_model = Gtk.SortListModel(
            model=self.filter_model, sorter=multi_sorter
        )

        self.selection_model = Gtk.SingleSelection(
            model=self.sort_model,
            autoselect=False,
            can_unselect=True,
            selected=Gtk.INVALID_LIST_POSITION,
        )
        self.results_list_view.set_model(self.selection_model)

    def filter_func(self, item, *args):
        query = self.search_entry.get_text().lower().replace(" ", "").replace("-", "")

        if not query:
            return True

        return query in item.search_key

    def sort_by_relevance(self, item1, item2, *args):
        query = self.search_entry.get_text().lower().replace(" ", "").replace("-", "")
        if not query:
            return Gtk.Ordering.EQUAL

        s1, s2 = item1.search_key, item2.search_key

        def get_rank(s):
            if s == query:
                return 0
            if s.startswith(query):
                return 1
            return 2

        r1, r2 = get_rank(s1), get_rank(s2)

        if r1 < r2:
            return Gtk.Ordering.SMALLER
        if r1 > r2:
            return Gtk.Ordering.LARGER
        return Gtk.Ordering.EQUAL

    def on_search_changed(self, entry):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self.rank_sorter.changed(Gtk.SorterChange.DIFFERENT)

        if self.selection_model.get_n_items() > 0:
            self.results_list_view.scroll_to(0, Gtk.ListScrollFlags.NONE, None)

    def on_list_item_activated(self, list_view, position):
        item = self.selection_model.get_item(position)
        if item:
            self.emit("command-activated", item)

    def on_search_activate(self, _entry):
        if self.selection_model.get_n_items() > 0:
            item = self.selection_model.get_item(0)
            if item:
                self.selection_model.set_selected(0)
                self.emit("command-activated", item)

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
