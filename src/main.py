import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

from .window import BriefWindow
from .preferences import BriefPreferencesWindow


class BriefApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.shonebinu.Brief",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path="/com/shonebinu/Brief",
        )
        self.create_action("quit", lambda *_: self.quit(), ["<control>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = BriefWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(
            application_name="Brief",
            application_icon="io.github.shonebinu.Brief",
            developer_name="Shone Binu",
            version="0.1.0",
            developers=["Shone Binu"],
            copyright="© 2025 Shone Binu",
        )
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        pref_window = BriefPreferencesWindow()
        pref_window.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    app = BriefApplication()
    return app.run(sys.argv)
