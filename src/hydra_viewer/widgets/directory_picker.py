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
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Input, Label


class DirectoryPicker(Screen[Path]):
    """Screen for selecting a directory."""

    DEFAULT_CSS = """
    DirectoryPicker {
        align: center middle;
    }

    #container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        layout: vertical;
    }

    #path-input-container {
        height: 3;
        margin-bottom: 1;
        layout: horizontal;
    }

    #path-input {
        width: 1fr;
    }

    #btn-up {
        width: 10;
        min-width: 10;
        margin-left: 1;
    }

    #tree-container {
        height: 1fr;
        border: solid $secondary;
        margin-bottom: 1;
    }

    #controls {
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    Button {
        width: 20;
        margin-left: 2;
        background: transparent;
        border: none;
    }

    Button:hover {
        background: $primary-darken-2;
    }

    .label {
        height: 1;
        content-align: left middle;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, start_path: Path):
        super().__init__()
        self.start_path = start_path.resolve()
        self.selected_path = self.start_path

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="container"):
            yield Label(" Select Config Directory:", classes="label")

            with Horizontal(id="path-input-container"):
                yield Input(value=str(self.selected_path), id="path-input", placeholder="Enter path here...")
                yield Button("Up", id="btn-up", flat=True)

            with Vertical(id="tree-container"):
                yield DirectoryTree(self.start_path, id="dir-tree")

            with Horizontal(id="controls"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button("Select Current", variant="primary", id="select", flat=True)
        yield Footer()

    def on_mount(self) -> None:
        # Focus input initially for quick navigation? Or tree?
        # Tree is usually better for browsing.
        self.query_one("#dir-tree", DirectoryTree).focus()

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.selected_path = event.path
        self.query_one("#path-input", Input).value = str(self.selected_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "select":
            # If user typed something but didn't hit enter, value is in input
            input_val = self.query_one("#path-input", Input).value
            try:
                path_from_input = Path(input_val).resolve()
                if path_from_input.exists() and path_from_input.is_dir():
                    self.dismiss(path_from_input)
                else:
                    # Fallback to tree selection if input is invalid/empty?
                    self.dismiss(self.selected_path)
            except Exception:
                self.dismiss(self.selected_path)

        elif button_id == "btn-up":
            tree = self.query_one("#dir-tree", DirectoryTree)
            try:
                current_root = Path(tree.path).resolve()
                parent = current_root.parent
                # On windows, parent of "C:/" is "C:/".
                if parent != current_root:
                    tree.path = str(
                        parent
                    )  # DirectoryTree.path expects string or Path? Textual 0.86+ handles both usually, but let's check.
                    # Older textual versions expect string.
                    self.start_path = parent
                    self.selected_path = parent
                    self.query_one("#path-input", Input).value = str(parent)
            except Exception as e:
                self.notify(f"Cannot go up: {e}", severity="error")

        elif button_id == "cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        path_str = event.value
        try:
            new_path = Path(path_str).resolve()
            if new_path.exists() and new_path.is_dir():
                self.start_path = new_path
                self.selected_path = new_path
                tree = self.query_one("#dir-tree", DirectoryTree)
                # Setting path changes root
                tree.path = str(new_path)
                tree.focus()
            else:
                self.notify(f"Directory not found: {path_str}", severity="error")
        except Exception as e:
            self.notify(f"Invalid path: {e}", severity="error")
