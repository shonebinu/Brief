import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk, GLib


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
                text_content = GLib.markup_escape_text(line[2:])

                text_content = re.sub(
                    r"`([^`]+)`",
                    r'<span font="monospace">\1</span>',
                    text_content,
                )

                text_content = re.sub(
                    r"&lt;(https?://[^&]+)&gt;", r'<a href="\1">\1</a>', text_content
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
                    self.create_code_block(line[1:-1], cmd_arg_format)
                )

    def create_code_block(self, code_text, cmd_arg_format):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["card"])

        scrolled = Gtk.ScrolledWindow(hexpand=True)

        formatted_code = self.format_command(code_text, cmd_arg_format)

        scrolled.set_child(
            Gtk.Label(
                label=formatted_code,
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

        btn.connect("clicked", lambda b: self.copy_to_clipboard(formatted_code))

        box.append(scrolled)
        box.append(btn)

        return box

    def copy_to_clipboard(self, text):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)

        toast = Adw.Toast.new("Copied to clipboard")
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def format_command(self, text, fmt):
        # https://github.com/tldr-pages/tldr/blob/v2.3/CLIENT-SPECIFICATION.md#page-structure
        pattern = r"\\\{\\\{|\\\}\\\}|\{\{(.*?)\}\}"

        def replace(match):
            full_match = match.group(0)

            if full_match == r"\{\{":
                return "{{"
            if full_match == r"\}\}":
                return "}}"

            content = match.group(1)

            if content.startswith("[") and content.endswith("]") and "|" in content:
                options = content[1:-1].split("|", 1)
                short_form = options[0]
                long_form = options[1] if len(options) > 1 else ""

                if fmt == "short":
                    return short_form
                elif fmt == "long":
                    return long_form
                else:
                    return content

            return content

        return re.sub(pattern, replace, text)
