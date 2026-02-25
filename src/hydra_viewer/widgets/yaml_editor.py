# Copyright (c) 2026 Mengzhao Wang
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SPDX-License-Identifier: MIT

from pathlib import Path

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static, TabbedContent, TabPane, TextArea

from hydra_viewer.core.parser import ConfigModule


class YamlEditor(Static):
    BINDINGS = [
        # Binding("ctrl+s", "save", "Save File"), # Global binding usually better, or focused.
    ]

    DEFAULT_CSS = """
    YamlEditor {
        width: 70%;
        height: 100%;
    }
    .welcome-msg {
        content-align: center middle;
        height: 100%;
    }
    """

    class FileSaved(Message):
        """File saved message."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.open_files: dict[str, Path] = {}  # tab_id -> file_path

    def compose(self) -> ComposeResult:
        with TabbedContent(id="tabs"):
            with TabPane("Welcome", id="welcome"):
                yield Static("Select a config module from the left to edit.", classes="welcome-msg")

    async def open_module(self, module: ConfigModule) -> None:
        if not module.path or not module.resolved:
            self.notify("Cannot open unresolved module.", severity="warning")
            return

        path = module.path
        tabs = self.query_one(TabbedContent)

        # Unique ID for the tab
        # Using name might conflict if same name in diff groups?
        # Using full path hash or group-name is safer.
        norm_group = module.group.replace("/", "_").replace(" ", "_")
        norm_name = module.name.replace("/", "_").replace(".", "_")
        tab_id = f"tab-{norm_group}-{norm_name}"

        if tab_id in self.open_files:
            tabs.active = tab_id
            return

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            self.notify(f"Error reading file: {e}", severity="error")
            return

        self.open_files[tab_id] = path

        # Add new tab
        text_area = TextArea(content, language="yaml", id=f"editor-{tab_id}")
        pane = TabPane(f"{module.name}", text_area, id=tab_id)

        # add_pane is async
        await tabs.add_pane(pane)
        tabs.active = tab_id

    def save_current_file(self, *, silent: bool = False) -> None:
        tabs = self.query_one(TabbedContent)
        if not tabs.active:
            return

        tab_id = tabs.active
        if tab_id == "welcome":
            return

        path = self.open_files.get(tab_id)
        if not path:
            return

        try:
            # We need to find the TextArea inside the active pane.
            # tabs.get_pane(tab_id) returns the TabPane
            pane = tabs.get_pane(tab_id)
            if not pane:
                self.notify("Error: Tab invalid", severity="error")
                return

            text_area = pane.query_one(TextArea)
            content = text_area.text
            path.write_text(content, encoding="utf-8")
            self.post_message(self.FileSaved(path))
            if not silent:
                self.notify(f"Saved {path.name}")
        except Exception as e:
            self.notify(f"Error saving file: {e}", severity="error")

    # Allow parent to control save, or bind locally if focused.
    # Textual priority: if focused widget handles binding, good.
    # TextArea handles ctrl+s? No.
    # So we can keep binding here.
    def action_save(self) -> None:
        self.save_current_file()

    def reload_all_tabs(self) -> None:
        """Reload content for all open tabs from disk."""
        tabs = self.query_one(TabbedContent)

        # Iterate over open files using self.open_files
        # But we need to update usage of TextArea in tabs

        for tab_id, path in self.open_files.items():
            if not path.exists():
                continue

            try:
                content = path.read_text(encoding="utf-8")
                pane = tabs.get_pane(tab_id)
                if pane:
                    text_area = pane.query_one(TextArea)
                    # Updating text might lose cursor position?
                    # For a reload it is acceptable.
                    text_area.text = content
            except Exception:
                pass

        self.notify("Reloaded open files.")
