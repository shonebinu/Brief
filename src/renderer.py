import gi
import re

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, Pango


@Gtk.Template(resource_path="/com/shonebinu/Brief/renderer.ui")
class CommandPage(Adw.Bin):
    __gtype_name__ = "CommandPage"

    overlay = Gtk.Template.Child()
    content_box = Gtk.Template.Child()
    scroller = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def display_content(self, raw_text, cmd_arg_format):
        self.scroller.get_vadjustment().set_value(0)

        child = self.content_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.content_box.remove(child)
            child = next_child

        lines = raw_text.splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("# "):
                self.content_box.append(
                    Gtk.Label(
                        label=line[2:], xalign=0, wrap=True, css_classes=["title-1"]
                    )
                )

            elif line.startswith("> "):
                self.content_box.append(
                    Gtk.Label(
                        label=re.sub(
                            r"`([^`]+)`",
                            r'<span font="monospace">\1</span>',
                            line[2:],
                        ),
                        xalign=0,
                        wrap=True,
                        css_classes=["dim-label"],
                        use_markup=True,
                    )
                )

            elif line.startswith("- "):
                self.content_box.append(
                    Gtk.Label(
                        label=line[2:],
                        xalign=0,
                        wrap=True,
                        margin_top=12,
                        css_classes=["heading"],
                    )
                )

            elif line.startswith("`") and line.endswith("`"):
                self.content_box.append(
                    self._create_code_block(line[1:-1], cmd_arg_format)
                )

    def _create_code_block(self, code_text, cmd_arg_format):
        row = Adw.ActionRow()
        row.set_activatable(False)
        row.add_css_class("property")

        label = Gtk.Label(label=code_text, xalign=0, selectable=True, wrap=True)
        label.add_css_class("monospace")
        label.set_ellipsize(Pango.EllipsizeMode.NONE)
        row.add_prefix(label)

        btn = Gtk.Button(icon_name="edit-copy-symbolic")
        btn.add_css_class("flat")
        btn.set_tooltip_text("Copy to clipboard")
        btn.set_valign(Gtk.Align.CENTER)

        btn.connect("clicked", lambda b: self._copy_to_clipboard(code_text))

        row.add_suffix(btn)
        return row

    def _copy_to_clipboard(self, text):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)

        toast = Adw.Toast.new("Copied to clipboard")
        toast.set_timeout(2)
        self.overlay.add_toast(toast)
