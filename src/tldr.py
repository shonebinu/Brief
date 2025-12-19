from collections import defaultdict
import langcodes
import gi
import shutil
from pathlib import Path
import threading

gi.require_version("Soup", "3.0")
from gi.repository import Gio, GLib, Soup


class PageManager:
    TLDR_PAGES_ZIP_URL = (
        "https://github.com/tldr-pages/tldr/archive/refs/heads/main.zip"
    )

    def __init__(self):
        # /app is read-only at runtime. TLDR pages are bundled here at flatpak build time and should be used as a fallback if no cached pages exist
        # ${FLATPAK_DEST} in flatpak manifest resolves to /app
        self.system_data_dir = Path("/app/share/tldr-data/")
        self.cache_dir = Path(GLib.get_user_cache_dir()) / "brief"
        self.local_data_dir = self.cache_dir / "tldr-data"
        self.zip_path = self.cache_dir / "tldr.zip"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.settings = Gio.Settings.new("io.github.shonebinu.Brief")
        self.session = Soup.Session.new()

    def _get_data_dir(self):
        return (
            self.local_data_dir
            if self.local_data_dir.exists()
            else self.system_data_dir
        )

    def get_available_languages(self):
        languages = []
        path = self._get_data_dir()

        if path.exists():
            for entry in path.iterdir():
                if entry.name.startswith("pages.") and entry.is_dir():
                    code = entry.name.split(".")[1]
                    languages.append((langcodes.get(code).autonym().title(), code))

        return sorted(languages, key=lambda x: x[0])

    def get_available_platforms(self):
        platforms = []
        default_pages = self._get_data_dir() / "pages.en"

        pretty_names = {
            "osx": "macOS",
            "sunos": "SunOS",
            "cisco-ios": "Cisco iOS",
            "dos": "DOS",
            "freebsd": "FreeBSD",
            "netbsd": "NetBSD",
            "openbsd": "OpenBSD",
            "android": "Android",
            "windows": "Windows",
            "linux": "Linux",
            "common": "Common",
        }

        if default_pages.exists():
            for entry in default_pages.iterdir():
                if entry.is_dir():
                    code = entry.name
                    name = pretty_names.get(code, code.replace("-", " ").title())
                    platforms.append((name, code))

        return sorted(platforms, key=lambda x: x[0])

    def get_all_commands(self):
        commands = defaultdict(lambda: defaultdict(list))
        enabled_langs = self.settings.get_strv("languages")
        enabled_plats = self.settings.get_strv("platforms")
        base_path = self._get_data_dir()

        for lang in enabled_langs:
            for plat in enabled_plats:
                path = base_path / f"pages.{lang}" / plat
                if not path.exists():
                    continue
                entries = [
                    entry.name[:-3]
                    for entry in path.iterdir()
                    if entry.suffix == ".md" and entry.is_file()
                ]
                if entries:
                    commands[lang][plat] = entries

        return commands

    def get_page(self, lang_code, platform, command):
        filepath = (
            self._get_data_dir() / f"pages.{lang_code}" / platform / f"{command}.md"
        )

        if filepath.exists():
            return filepath.read_text(encoding="utf-8")

        return f"Command '{command}' not found in path '{filepath}'."

    def update_cache(self, progress_cb, finished_cb):
        self.progress_cb = progress_cb
        self.finished_cb = finished_cb
        self.downloaded = 0

        self.msg = Soup.Message.new("GET", self.TLDR_PAGES_ZIP_URL)
        self.msg.connect("got-body-data", self._on_got_body_data)

        self.session.send_async(
            self.msg,
            GLib.PRIORITY_DEFAULT,
            None,
            self._on_response_finished,
            None,
        )

    def _on_got_body_data(self, msg, chunk):
        self.downloaded += chunk
        total = msg.get_response_headers().get_content_length()

        fraction = 0 if not total else self.downloaded / total

        GLib.idle_add(
            self.progress_cb,
            fraction,
            f"Downloading... {(fraction * 100):.0f}% ({(self.downloaded / 1024 / 1024):.2f} MB)",
        )

    def _on_response_finished(self, session, result, data):
        try:
            stream = session.send_finish(result)

            file = Gio.File.new_for_path(str(self.zip_path))
            output = file.replace(
                None,
                False,
                Gio.FileCreateFlags.REPLACE_DESTINATION,
                None,
            )

            output.splice_async(
                stream,
                Gio.OutputStreamSpliceFlags.CLOSE_SOURCE
                | Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                GLib.PRIORITY_DEFAULT,
                None,
                self._on_splice_finished,
                None,
            )

        except GLib.Error as e:
            GLib.idle_add(self.finished_cb, False, e.message)

    def _on_splice_finished(self, output, result, data):
        try:
            output.splice_finish(result)
            GLib.idle_add(self.progress_cb, 1.0, "Extracting...")

            threading.Thread(target=self._extract_in_thread, daemon=True).start()

        except GLib.Error as e:
            GLib.idle_add(self.finished_cb, False, e.message)

    def _extract_in_thread(self):
        try:
            self.process_zip()
            GLib.idle_add(self.finished_cb, True, "Cache updated successfully")
        except Exception as e:
            GLib.idle_add(self.finished_cb, False, str(e))

    def process_zip(self):
        extract_temp = Path(self.cache_dir) / "temp_extract"
        shutil.rmtree(extract_temp, ignore_errors=True)

        shutil.unpack_archive(self.zip_path, extract_temp)

        content_root = next(extract_temp.iterdir())
        content_root = Path(content_root)

        pages_en = content_root / "pages.en"
        pages = content_root / "pages"

        if pages_en.exists():
            pages_en.unlink()
        if pages.exists():
            pages.rename(pages_en)

        for entry in content_root.iterdir():
            if not entry.name.startswith("pages."):
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()

        shutil.rmtree(self.local_data_dir, ignore_errors=True)
        shutil.move(str(content_root), self.local_data_dir)

        shutil.rmtree(extract_temp, ignore_errors=True)
        Path(self.zip_path).unlink()
