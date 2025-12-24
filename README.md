<div align=center>

![Brief app screenshot](./data/screenshots/banner.png)

<img src="./data/icons/hicolor/scalable/apps/io.github.shonebinu.Brief.svg" alt="Brief Logo" width="128" >

# Brief

**Browse command-line cheatsheets**

![Flathub Downloads](https://img.shields.io/flathub/downloads/io.github.shonebinu.Brief?style=for-the-badge)
![Flathub Version](https://img.shields.io/flathub/v/io.github.shonebinu.Brief?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/shonebinu/Brief?style=for-the-badge&color=yellow)

</div>

## Description

Brief is an app for browsing command-line cheatsheets written in Python, using GTK4 and Libadwaita. The data source is [tldr-pages](https://github.com/tldr-pages/tldr). It lets you search through thousands of command-line tools across multiple platforms and languages, providing simplified help pages.

## Features

- Works completely offline.
- Filter platform specific commands (Linux, Windows, Android, etc.).
- View command help pages in multiple available languages.
- Change the command argument format between long (`ls --all`) or short (`ls -a`).
- Lets you update the cache within the app to download the latest data.

## Install

<a href='https://flathub.org/apps/io.github.shonebinu.Brief'>
    <img width='240' alt='Get Brief on Flathub' src='https://flathub.org/api/badge?svg&locale=en '/>
</a>

## Development

You can clone this project and run it using [Gnome Builder](https://apps.gnome.org/Builder/). The Python libraries used in this project are defined inside [requirements.txt](./requirements.txt), which you may install if you want editor completions.

## Credits

The entirety of the data used in this project is from [tldr-pages](https://github.com/tldr-pages/tldr) and without their valuable work, this project wouldn't exist.
