import os
import langcodes
from gi.repository import Gio


class PageManager:
    def __init__(self):
        self.system_path = "/app/share/tldr-data/"
        self.settings = Gio.Settings.new("com.shonebinu.Brief")

    def get_available_languages(self):
        languages = []

        if os.path.exists(self.system_path):
            for folder in os.listdir(self.system_path):
                if folder.startswith("pages."):  # pages.en is symlink to pages
                    code = folder.split(".")[1]
                    name = langcodes.get(code).display_name()
                    languages.append((name, code))

        return sorted(languages, key=lambda x: x[0])

    def get_available_platforms(self):
        platforms = []
        default_pages = os.path.join(self.system_path, "pages")

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

        if os.path.exists(default_pages):
            for folder in os.listdir(default_pages):
                folder_path = os.path.join(default_pages, folder)
                if os.path.isdir(folder_path):
                    code = folder

                    if code in pretty_names:
                        name = pretty_names[code]
                    else:
                        name = code.replace("-", " ").title()

                    platforms.append((name, code))

        return sorted(platforms, key=lambda x: x[0])

    def get_all_commands(self):
        commands = {}

        enabled_langs = self.settings.get_strv("languages")
        enabled_plats = self.settings.get_strv("platforms")

        for lang_code in enabled_langs:
            lang_folder = f"pages.{lang_code}"
            commands[lang_code] = {}

            for platform in enabled_plats:
                folder_path = os.path.join(self.system_path, lang_folder, platform)
                commands[lang_code][platform] = []

                if os.path.exists(folder_path):
                    for filename in os.listdir(folder_path):
                        if filename.endswith(".md"):
                            commands[lang_code][platform].append(filename[:-3])

        return commands

    def get_page(self, lang_code, platform, command):
        filepath = os.path.join(
            self.system_path, f"pages.{lang_code}", platform, f"{command}.md"
        )

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        return f"Command '{command}' not found in path '{filepath}'."
