import json
import shutil
import threading
from collections import defaultdict
from pathlib import Path
import langcodes
import requests
import os
from functools import lru_cache
from gi.repository import Gio, GLib


class PageManager:
    TLDR_PAGES_ZIP_URL = (
        "https://github.com/tldr-pages/tldr/releases/download/v2.3/tldr.zip"
    )

    def __init__(self):
        # /app is read-only at runtime.
        # ${FLATPAK_DEST} in flatpak manifest resolves to /app
        self.system_data_dir = Path("/app/share/tldr/")
        self.cache_dir = Path(GLib.get_user_cache_dir()) / "brief"
        self.local_data_dir = self.cache_dir / "tldr"
        self.zip_path = self.cache_dir / "tldr.zip"

        self.settings = Gio.Settings.new("io.github.shonebinu.Brief")

        self.is_updating = False

    def get_data_dir(self):
        return (
            self.local_data_dir
            if (self.local_data_dir / "commands.json").exists()
            else self.system_data_dir
        )

    @lru_cache(maxsize=1)
    def get_commands_map(self):
        return json.loads(
            (self.get_data_dir() / "commands.json").read_text(encoding="utf-8")
        )

    def get_available_languages(self):
        languages = [
            (langcodes.get(lang).autonym().title(), lang)
            for lang in self.get_commands_map()
        ]

        return sorted(languages, key=lambda x: x[0])

    def get_available_platforms(self):
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

        platforms = [
            (pretty_names.get(plat, plat.replace("-", " ").title()), plat)
            for plat in self.get_commands_map().get("en", {})
        ]

        return sorted(platforms, key=lambda x: x[0])

    def get_all_commands(self):
        commands = defaultdict(lambda: defaultdict(list))
        enabled_langs = self.settings.get_strv("languages")
        enabled_plats = self.settings.get_strv("platforms")

        all_commands = self.get_commands_map()

        for lang in enabled_langs:
            for plat in enabled_plats:
                if plat in all_commands.get(lang, {}):
                    commands[lang][plat] = all_commands[lang][plat]

        return commands

    def get_page(self, lang_code, platform, command):
        filepath = (
            self.get_data_dir() / f"pages.{lang_code}" / platform / f"{command}.md"
        )

        if filepath.exists():
            return filepath.read_text(encoding="utf-8")

        return f"Command '{command}' not found in path '{filepath}'."

    def update_cache(self, progress_cb, finished_cb):
        if self.is_updating:
            return finished_cb(False, "An update process is already going on")

        self.is_updating = True
        self.progress_cb = progress_cb
        self.finished_cb = finished_cb

        threading.Thread(target=self.download_and_process_tldr_zip, daemon=True).start()

    def download_and_process_tldr_zip(self):
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            self.download_tldr_zip()
            GLib.idle_add(self.progress_cb, -1, "Extracting...")
            self.process_tldr_zip()
            GLib.idle_add(self.finished_cb, True, "Cache updated successfully")
        except requests.exceptions.ConnectionError:
            GLib.idle_add(self.finished_cb, False, "No network connection")
        except requests.exceptions.Timeout:
            GLib.idle_add(self.finished_cb, False, "Connection timed out")
        except Exception as e:
            GLib.idle_add(self.finished_cb, False, str(e))
        finally:
            self.is_updating = False

    def download_tldr_zip(self):
        with requests.get(self.TLDR_PAGES_ZIP_URL, stream=True, timeout=15) as r:
            r.raise_for_status()
            downloaded = 0
            total_size = int(r.headers.get("content-length", 0))

            with open(self.zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            fraction = downloaded / total_size
                            percent = int(fraction * 100)
                            label = f"Downloading... {percent}% ({downloaded / 1024 / 1024:.1f} MB)"
                        else:
                            fraction = -1.0
                            label = f"Downloading... {downloaded / 1024 / 1024:.1f} MB"

                        GLib.idle_add(
                            self.progress_cb,
                            fraction,
                            label,
                        )

    def process_tldr_zip(self):
        extract_temp = self.cache_dir / "tldr.tmp"
        shutil.rmtree(extract_temp, ignore_errors=True)

        shutil.unpack_archive(self.zip_path, extract_temp)

        commands = defaultdict(lambda: defaultdict(list))

        for entry in extract_temp.iterdir():
            if entry.is_dir() and entry.name.startswith("pages."):
                lang = entry.name.split(".", 1)[1]

                for platform_dir in entry.iterdir():
                    if platform_dir.is_dir():
                        platform = platform_dir.name

                        for md_file in platform_dir.glob("*.md"):
                            command = md_file.stem
                            commands[lang][platform].append(command)
            else:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()

        (extract_temp / "commands.json").write_text(
            json.dumps(commands, indent=2), encoding="utf-8"
        )

        shutil.rmtree(self.local_data_dir, ignore_errors=True)
        os.replace(extract_temp, self.local_data_dir)  # atomic operation

        self.zip_path.unlink()
        shutil.rmtree(extract_temp, ignore_errors=True)

        self.get_commands_map.cache_clear()
