import sys

import gi

from .preferences import BriefPreferencesWindow
from .window import BriefWindow
from .tldr import PageManager

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk


class BriefApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.shonebinu.Brief",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path="/io/github/shonebinu/Brief",
        )
        self.manager = PageManager()

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
            version="0.2.0",
            developers=["Shone Binu"],
            copyright="© 2025-present Shone Binu",
            website="https://github.com/shonebinu/Brief",
            issue_url="https://github.com/shonebinu/Brief/issues",
            license_type="GTK_LICENSE_GPL_3_0",
        )

        about.add_link("Donate with Ko-Fi", "https://ko-fi.com/shonebinu")
        about.add_link("Sponsor on Github", "https://github.com/sponsors/shonebinu")

        about.add_legal_section(
            "Data Source",
            "© 2014—present the <a href='https://github.com/orgs/tldr-pages/people'>tldr-pages team</a> and <a href='https://github.com/tldr-pages/tldr/graphs/contributors'>contributors</a>.",
            Gtk.License.CUSTOM,
            "This work is licensed under the <a href='https://creativecommons.org/licenses/by/4.0/'>Creative Commons Attribution 4.0 International License</a> (CC-BY).",
        )

        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        pref_window = BriefPreferencesWindow(manager=self.manager)
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
