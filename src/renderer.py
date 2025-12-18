import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk


@Gtk.Template(resource_path="/io/github/shonebinu/Brief/renderer.ui")
class CommandPage(Adw.Bin):
    __gtype_name__ = "CommandPage"

    content_box = Gtk.Template.Child()
    scroller = Gtk.Template.Child()

    def __init__(self, toast_overlay, **kwargs):
        super().__init__(**kwargs)

        self.toast_overlay = toast_overlay

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
                text_content = line[2:]

                text_content = re.sub(
                    r"`([^`]+)`",
                    r'<span font="monospace">\1</span>',
                    text_content,
                )

                text_content = re.sub(
                    r"<(https?://[^>]+)>", r'<a href="\1">\1</a>', text_content
                )

                self.content_box.append(
                    Gtk.Label(
                        label=text_content,
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
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["card"])

        scrolled = Gtk.ScrolledWindow(hexpand=True)

        def format_command(text, fmt):
            def replace(match):
                content = match.group(1)

                if content.startswith("[") and "|" in content:
                    parts = content[1:-1].split("|")
                    return parts[1] if fmt == "long" else parts[0]

                return content

            return re.sub(r"\{\{(.*?)\}\}", replace, text)

        scrolled.set_child(
            Gtk.Label(
                label=format_command(code_text, cmd_arg_format),
                xalign=0,
                selectable=True,
                wrap=False,
                css_classes=["monospace"],
                margin_top=18,
                margin_bottom=18,
                margin_start=18,
                margin_end=18,
            )
        )

        btn = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy to clipboard",
            valign=Gtk.Align.CENTER,
            css_classes=["flat"],
            margin_end=6,
        )

        btn.connect("clicked", lambda b: self._copy_to_clipboard(code_text))

        box.append(scrolled)
        box.append(btn)

        return box

    def _copy_to_clipboard(self, text):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)

        toast = Adw.Toast.new("Copied to clipboard")
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)
