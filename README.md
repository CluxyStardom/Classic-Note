# Classic Note

A super simple fully offline notes application using Python and GTK.

## Features

- Local JSON note storage in `~/.local/share/classic-note/notes.json`
- Note list and editor layout like a phone-style notes app
- Create, save, export, and delete notes
- Fully offline with no other stuff

## Requirements

- Python 3
- `python3-gi` / PyGObject with GTK 3

## Install

On Debian/Ubuntu:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

## Run

```bash
git clone https://github.com/CluxyStardom/Classic-Note
```

```bash
cd ~/Classic-Note
python3 main.py
```

## Installation

Install the desktop launcher with:

```bash
cd ~/Classic-Note
./install.sh
```

This copies `Classic-Note.desktop` to `~/.local/share/applications` so you can launch the app from your desktop environment menu.

## Notes storage

Notes are stored in:

`~/.local/share/Classic-Note/notes.json`

## Coming Soon

App icon:(
