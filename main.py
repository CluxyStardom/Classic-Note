#!/usr/bin/env python3
import json
import os
import uuid
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, Pango
import gi.repository.PangoCairo as PangoCairo

APP_NAME = "Classic Note"
DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "classic-note")
STORE_FILE = os.path.join(DATA_DIR, "notes.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


class NoteStore:
    def __init__(self, filename=STORE_FILE):
        self.filename = filename
        ensure_data_dir()
        self.notes = self.load()
        self.notes.sort(key=lambda n: (not n.get("pinned", False), -n.get("updated", 0)))

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, list):
                        for note in data:
                            if "pinned" not in note:
                                note["pinned"] = False
                        return data
                    return []
            except (json.JSONDecodeError, IOError):
                return []

        return []

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as handle:
                json.dump(self.notes, handle, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def add_note(self, title="New note", content=""):
        note = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "updated": int(time.time()),
            "pinned": False,
        }
        self.notes.insert(0, note)
        self.notes.sort(key=lambda n: (not n.get("pinned", False), -n.get("updated", 0)))
        self.save()
        return note

    def delete_note(self, note_id):
        self.notes = [note for note in self.notes if note["id"] != note_id]
        self.save()

    def update_note(self, note_id, title, content):
        for note in self.notes:
            if note["id"] == note_id:
                note["title"] = title.strip()
                note["content"] = content
                note["updated"] = int(time.time())
                break
        self.notes.sort(key=lambda n: (not n.get("pinned", False), -n.get("updated", 0)))
        self.save()

    def get_note(self, note_id):
        for note in self.notes:
            if note["id"] == note_id:
                return note
        return None

    def toggle_pin(self, note_id):
        for note in self.notes:
            if note["id"] == note_id:
                note["pinned"] = not note.get("pinned", False)
                note["updated"] = int(time.time())
                break
        self.notes.sort(key=lambda n: (not n.get("pinned", False), -n.get("updated", 0)))
        self.save()


class NotesApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(900, 560)
        self.set_border_width(12)

        self.store = NoteStore()
        if not self.store.notes:
            self.store.add_note("Welcome", "This is your offline notes app. Start typing to create notes.")

        self.search_query = ""
        self.loading_note = False  # Flag to prevent auto-save during note loading

        self.build_ui()
        self.apply_style()

        self.refresh_notes()
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        self.select_first_note()

    def build_ui(self):
        header = Gtk.HeaderBar()
        header.props.title = APP_NAME
        header.props.show_close_button = True
        
        # Create settings menu
        self.create_settings_menu()
        header.pack_start(self.settings_button)
        
        header_right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.new_button = Gtk.Button.new_with_label("New")
        self.export_button = Gtk.Button.new_with_label("Export")
        self.delete_button = Gtk.Button.new_with_label("Delete")
        self.new_button.get_style_context().add_class("suggested-action")
        self.delete_button.get_style_context().add_class("suggested-action")
        header_right.pack_start(self.export_button, False, False, 0)
        header_right.pack_start(self.new_button, False, False, 0)
        header_right.pack_start(self.delete_button, False, False, 0)
        header.pack_end(header_right)

        self.set_titlebar(header)

        self.new_button.connect("clicked", self.on_new_note)
        self.export_button.connect("clicked", self.on_export_note)
        self.delete_button.connect("clicked", self.on_delete_note)

        self.build_notes_panel()

    def create_settings_menu(self):
        # Create menu button
        self.settings_button = Gtk.MenuButton()
        settings_icon = Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        self.settings_button.set_image(settings_icon)
        self.settings_button.set_tooltip_text("Settings")
        
        # Create popover
        self.settings_popover = Gtk.Popover()
        self.settings_button.set_popover(self.settings_popover)
        
        # Create menu box
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        menu_box.set_margin_top(10)
        menu_box.set_margin_bottom(10)
        menu_box.set_margin_start(10)
        menu_box.set_margin_end(10)
        
        # Font size section
        font_size_label = Gtk.Label(label="<b>Font Size</b>", xalign=0)
        font_size_label.set_use_markup(True)
        menu_box.pack_start(font_size_label, False, False, 0)
        
        # Font size buttons
        size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.small_font_btn = Gtk.RadioButton.new_with_label_from_widget(None, "Small")
        self.medium_font_btn = Gtk.RadioButton.new_with_label_from_widget(self.small_font_btn, "Medium")
        self.large_font_btn = Gtk.RadioButton.new_with_label_from_widget(self.small_font_btn, "Large")
        
        # Set medium as default
        self.medium_font_btn.set_active(True)
        
        size_box.pack_start(self.small_font_btn, False, False, 0)
        size_box.pack_start(self.medium_font_btn, False, False, 0)
        size_box.pack_start(self.large_font_btn, False, False, 0)
        menu_box.pack_start(size_box, False, False, 0)
        
        # Font style section
        font_style_label = Gtk.Label(label="<b>Font Style</b>", xalign=0)
        font_style_label.set_use_markup(True)
        menu_box.pack_start(font_style_label, False, False, 0)
        
        # Font family combo box
        self.font_combo = Gtk.ComboBoxText()
        
        # Get system fonts
        font_map = PangoCairo.font_map_get_default()
        families = font_map.list_families()
        
        # Sort families by name and add to combo box
        family_names = sorted([family.get_name() for family in families])
        for name in family_names:
            self.font_combo.append_text(name)
        
        # Set Monospace as default if available, otherwise first font
        try:
            monospace_index = family_names.index("Monospace")
            self.font_combo.set_active(monospace_index)
        except ValueError:
            self.font_combo.set_active(0)  # First font if Monospace not found
            
        menu_box.pack_start(self.font_combo, False, False, 0)
        
        # Connect signals
        self.small_font_btn.connect("toggled", self.on_font_size_changed, "small")
        self.medium_font_btn.connect("toggled", self.on_font_size_changed, "medium")
        self.large_font_btn.connect("toggled", self.on_font_size_changed, "large")
        self.font_combo.connect("changed", self.on_font_family_changed)
        
        self.settings_popover.add(menu_box)
        menu_box.show_all()

    def on_font_size_changed(self, button, size):
        if not button.get_active():
            return
            
        # Map size names to actual font sizes
        size_map = {
            "small": 10,
            "medium": 12,
            "large": 16
        }
        
        font_size = size_map.get(size, 12)
        self.apply_font_settings()

    def on_font_family_changed(self, combo):
        self.apply_font_settings()

    def apply_font_settings(self):
        # Get current settings
        font_family = self.font_combo.get_active_text()
        if not font_family:
            font_family = "Monospace"
            
        # Determine font size
        if self.small_font_btn.get_active():
            font_size = 10
        elif self.large_font_btn.get_active():
            font_size = 16
        else:  # medium
            font_size = 12
            
        # Create font description
        font_desc = f"{font_family} {font_size}"
        
        # Apply to text view
        self.content_view.override_font(Pango.FontDescription.from_string(font_desc))

    def build_notes_panel(self):
        self.main_box = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.add(self.main_box)

        self.notes_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.notes_panel.set_size_request(280, -1)
        self.notes_panel.set_margin_top(6)
        self.notes_panel.set_margin_bottom(6)
        self.notes_panel.set_margin_start(6)
        self.notes_panel.set_margin_end(6)
        self.notes_panel.get_style_context().add_class("sidebar")

        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        heading = Gtk.Label()
        heading.set_markup("<span size='large'><b>Notes</b></span>")
        heading.set_xalign(0)
        self.count_label = Gtk.Label(label="")
        self.count_label.set_xalign(1)
        title_bar.pack_start(heading, True, True, 0)
        title_bar.pack_start(self.count_label, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search notes")
        self.search_entry.connect("search-changed", self.on_search_changed)

        self.notes_listbox = Gtk.ListBox()
        self.notes_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.notes_listbox.connect("row-activated", self.on_note_selected)

        self.notes_scrolled = Gtk.ScrolledWindow()
        self.notes_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.notes_scrolled.add(self.notes_listbox)

        self.notes_panel.pack_start(title_bar, False, False, 0)
        self.notes_panel.pack_start(self.search_entry, False, False, 0)
        self.notes_panel.pack_start(self.notes_scrolled, True, True, 0)

        self.editor_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.editor_panel.set_margin_top(6)
        self.editor_panel.set_margin_bottom(6)
        self.editor_panel.set_margin_start(6)
        self.editor_panel.set_margin_end(6)
        self.editor_panel.get_style_context().add_class("editor-panel")

        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Note title")
        self.title_entry.get_style_context().add_class("note-title-entry")

        # Create title bar with title entry and search
        self.title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.note_search_entry = Gtk.SearchEntry()
        self.note_search_entry.set_placeholder_text("Search in note")
        self.note_search_entry.connect("search-changed", self.on_note_search_changed)
        
        self.title_bar.pack_start(self.title_entry, True, True, 0)
        self.title_bar.pack_start(self.note_search_entry, False, False, 0)

        self.note_status = Gtk.Label(label="")
        self.note_status.set_xalign(0)
        self.note_status.get_style_context().add_class("note-status")

        self.content_view = Gtk.TextView()
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.content_view.get_style_context().add_class("note-content")
        self.content_view.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.1, 0.1, 1.0))
        self.content_view.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.8, 0.8, 1.0))

        # Create search highlight tag
        buffer = self.content_view.get_buffer()
        buffer.create_tag("search-highlight", background="yellow", foreground="black")

        # Connect auto-save signals
        self.title_entry.connect("changed", self.on_content_changed)
        self.content_view.get_buffer().connect("changed", self.on_content_changed)

        self.content_scrolled = Gtk.ScrolledWindow()
        self.content_scrolled.get_style_context().add_class("note-scroll")
        self.content_scrolled.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.12, 0.12, 0.12, 1.0))
        self.content_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.content_scrolled.add(self.content_view)
        self.content_scrolled.set_hexpand(True)
        self.content_scrolled.set_vexpand(True)

        self.editor_panel.pack_start(self.title_bar, False, False, 0)
        self.editor_panel.pack_start(self.note_status, False, False, 0)
        self.editor_panel.pack_start(self.content_scrolled, True, True, 0)

        self.main_box.pack1(self.notes_panel, resize=False, shrink=False)
        self.main_box.pack2(self.editor_panel, resize=True, shrink=False)

    def apply_style(self):
        css = b"""
        window, headerbar, entry, searchentry, textview {
            color: #CCCCCC;
        }

        window {
            background-color: #1A1A1A;
        }

        headerbar {
            background-color: #2B2B2B;
            color: #CCCCCC;
            border-bottom: 1px solid #404040;
        }

        headerbar button {
            color: #CCCCCC;
        }

        button {
            background-color: #404040;
            color: #CCCCCC;
            border-radius: 10px;
            border: 1px solid #555555;
            padding: 6px 14px;
        }

        button.suggested-action {
            background-color: #007ACC;
            color: #FFFFFF;
        }

        button:hover {
            background-color: #555555;
        }

        .sidebar {
            background-color: #2B2B2B;
            border-radius: 18px;
            padding: 16px;
            border: 1px solid #404040;
        }

        .editor-panel {
            background-color: #1E1E1E;
            border-radius: 18px;
            padding: 18px;
            border: 1px solid #333333;
        }

        .note-row {
            background-color: #333333;
            padding: 14px 12px;
            border-radius: 14px;
            margin-bottom: 8px;
            border: 1px solid #404040;
        }

        .note-row:selected {
            background-color: #007ACC;
        }

        .note-title {
            font-weight: 700;
            font-size: 13px;
            color: #FFFFFF;
        }

        .note-subtitle {
            color: #AAAAAA;
            font-size: 11px;
        }

        .note-status {
            color: #AAAAAA;
            font-size: 11px;
        }

        .note-title-entry {
            background-color: #2D2D2D;
            border-radius: 12px;
            padding: 10px;
            border: 1px solid #555555;
            color: #FFFFFF;
        }

        entry, searchentry {
            background-color: #2D2D2D;
            border-radius: 12px;
            padding: 10px;
            border: 1px solid #555555;
            color: #FFFFFF;
        }

        entry text, searchentry text {
            color: #FFFFFF;
        }

        scrolledwindow, scrolledwindow > viewport, .note-scroll, .note-scroll > viewport {
            background-color: #1E1E1E;
            border-radius: 18px;
        }

        .note-content,
        textview,
        textview.note-content {
            background-color: #1A1A1A;
            border-radius: 18px;
            padding: 14px;
            color: #CCCCCC;
            border: 1px solid #333333;
            background-image: none;
        }

        textview, textview.note-content text {
            color: #CCCCCC;
        }

        scrollbar, scrollbar slider {
            background-color: #404040;
        }

        .pin-button {
            background-color: transparent;
            border: none;
            color: #AAAAAA;
            padding: 8px;
            border-radius: 4px;
        }

        .pin-button:hover {
            background-color: #555555;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def refresh_notes(self):
        for child in self.notes_listbox.get_children():
            self.notes_listbox.remove(child)

        query = self.search_query.lower().strip()
        filtered = []
        for note in self.store.notes:
            if not query or query in note["title"].lower() or query in note["content"].lower():
                filtered.append(note)

        self.count_label.set_text(f"{len(filtered)} notes")

        for note in filtered:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("note-row")
            row.note_id = note["id"]

            display_title = note["title"] or "(Untitled)"
            title_label = Gtk.Label(label=display_title, xalign=0)
            title_label.get_style_context().add_class("note-title")

            timestamp = time.strftime("%b %d · %I:%M %p", time.localtime(note["updated"]))
            if timestamp.startswith("0"):
                timestamp = timestamp[1:]
            subtitle = Gtk.Label(label=timestamp, xalign=0)
            subtitle.get_style_context().add_class("note-subtitle")

            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            content_box.pack_start(title_label, False, False, 0)
            content_box.pack_start(subtitle, False, False, 0)

            pin_button = Gtk.Button()
            pin_button.set_relief(Gtk.ReliefStyle.NONE)
            pin_button.get_style_context().add_class("pin-button")
            pin_label = "Unpin note" if note.get("pinned", False) else "Pin note"
            pin_button.set_tooltip_text(pin_label)
            icon_name = "starred-symbolic" if note.get("pinned", False) else "non-starred-symbolic"
            pin_icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            pin_button.set_image(pin_icon)
            pin_button.connect("clicked", self.on_toggle_pin, note["id"])

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row_box.pack_start(content_box, True, True, 0)
            row_box.pack_end(pin_button, False, False, 0)
            row.add(row_box)
            self.notes_listbox.add(row)

        self.notes_listbox.show_all()

    def select_first_note(self):
        rows = self.notes_listbox.get_children()
        if rows:
            self.notes_listbox.select_row(rows[0])
            self.load_selected_note()

    def load_selected_note(self):
        row = self.notes_listbox.get_selected_row()
        if not row:
            self.selected_note_id = None
            self.loading_note = True
            self.title_entry.set_text("")
            # Clear search highlights
            buffer = self.get_buffer()
            buffer.remove_tag_by_name("search-highlight", buffer.get_start_iter(), buffer.get_end_iter())
            buffer.set_text("")
            self.loading_note = False
            self.note_status.set_text("No note selected")
            return

        note_id = row.note_id
        note = self.store.get_note(note_id)
        if note:
            self.selected_note_id = note_id
            self.loading_note = True
            self.title_entry.set_text(note["title"])
            # Clear search highlights before loading new content
            buffer = self.get_buffer()
            buffer.remove_tag_by_name("search-highlight", buffer.get_start_iter(), buffer.get_end_iter())
            buffer.set_text(note["content"])
            self.loading_note = False
            self.note_status.set_text("Loaded note")

    def get_buffer(self):
        return self.content_view.get_buffer()

    def on_note_selected(self, listbox, row):
        self.load_selected_note()

    def on_search_changed(self, entry):
        self.search_query = entry.get_text()
        self.refresh_notes()

    def on_note_search_changed(self, entry):
        search_text = entry.get_text().strip()
        if not search_text or not self.selected_note_id:
            # Clear all highlights if search is empty
            buffer = self.get_buffer()
            buffer.remove_tag_by_name("search-highlight", buffer.get_start_iter(), buffer.get_end_iter())
            self.note_status.set_text("")
            return
        
        # Get the text buffer
        buffer = self.get_buffer()
        
        # Clear previous highlights
        buffer.remove_tag_by_name("search-highlight", buffer.get_start_iter(), buffer.get_end_iter())
        
        # Get all text
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        content = buffer.get_text(start_iter, end_iter, True)
        
        # Find all occurrences (case-insensitive)
        search_lower = search_text.lower()
        content_lower = content.lower()
        start_pos = 0
        found_count = 0
        
        while True:
            pos = content_lower.find(search_lower, start_pos)
            if pos == -1:
                break
                
            # Apply highlight tag to this occurrence
            match_start = buffer.get_iter_at_offset(pos)
            match_end = buffer.get_iter_at_offset(pos + len(search_text))
            buffer.apply_tag(highlight_tag, match_start, match_end)
            
            found_count += 1
            start_pos = pos + 1
        
        if found_count > 0:
            # Scroll to first occurrence
            first_match = buffer.get_iter_at_offset(content_lower.find(search_lower))
            self.content_view.scroll_to_iter(first_match, 0.1, False, 0.0, 0.0)
            self.note_status.set_text(f"Found and highlighted {found_count} occurrence{'s' if found_count != 1 else ''} of '{search_text}'")
        else:
            self.note_status.set_text(f"'{search_text}' not found")

    def on_new_note(self, button):
        note = self.store.add_note()
        self.refresh_notes()
        self.select_note_by_id(note["id"])

    def on_export_note(self, button):
        if not self.selected_note_id:
            return
        
        # Get current note content
        title = self.title_entry.get_text()
        buffer = self.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        content = buffer.get_text(start_iter, end_iter, True)
        
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Export Note",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        # Set default filename
        default_name = title.strip() or "Untitled"
        dialog.set_current_name(f"{default_name}.txt")
        
        # Add text files filter
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    if title.strip():
                        f.write(f"{title}\n\n")
                    f.write(content)
                self.note_status.set_text("Note exported successfully")
            except IOError as e:
                error_dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Export Failed",
                )
                error_dialog.format_secondary_text(f"Could not save file: {str(e)}")
                error_dialog.run()
                error_dialog.destroy()
                self.note_status.set_text("Export failed")
        
        dialog.destroy()

    def on_delete_note(self, button):
        if not self.selected_note_id:
            return
        self.store.delete_note(self.selected_note_id)
        self.refresh_notes()
        self.select_first_note()
        self.note_status.set_text("Deleted")

    def select_note_by_id(self, note_id):
        for row in self.notes_listbox.get_children():
            if getattr(row, "note_id", None) == note_id:
                self.notes_listbox.select_row(row)
                self.load_selected_note()
                return

    def on_content_changed(self, widget):
        if not self.selected_note_id or self.loading_note:
            return
        
        title = self.title_entry.get_text()
        buffer = self.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        content = buffer.get_text(start_iter, end_iter, True)
        
        # Get the current note to check if title changed
        current_note = self.store.get_note(self.selected_note_id)
        title_changed = current_note and current_note["title"] != title
        
        self.store.update_note(self.selected_note_id, title, content)
        
        # Refresh the notes list if title changed to update the sidebar
        if title_changed:
            self.refresh_notes()
            self.select_note_by_id(self.selected_note_id)

    def on_toggle_pin(self, button, note_id):
        self.store.toggle_pin(note_id)
        self.refresh_notes()
        self.select_note_by_id(note_id)


def main():
    window = NotesApp()
    Gtk.main()


if __name__ == "__main__":
    main()


    #just watermark i guess? Cluxystardom follow me on github and tiktok if you want :D
