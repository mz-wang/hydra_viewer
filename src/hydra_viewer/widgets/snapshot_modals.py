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

import time
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label

from hydra_viewer.core.snapshot import SnapshotManager


class BackupModal(ModalScreen[str]):
    DEFAULT_CSS = """
    BackupModal {
        align: center middle;
    }
    #dialog {
        layout: vertical;
        padding: 1;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    #title {
        height: 1;
        content-align: center middle;
        text-style: bold;
    }
    #input {
        width: 100%;
        margin: 1 0;
    }
    .buttons {
        width: 100%;
        height: 3;
        align: center middle;
        dock: bottom;
    }
    Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Create Snapshot", id="title")
            yield Input(placeholder="Enter tag name...", id="input")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button("Create", variant="primary", id="create", flat=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            input_widget = self.query_one(Input)
            tag = input_widget.value or "manual"
            self.dismiss(tag)
        else:
            self.dismiss(None)


class RestoreModal(ModalScreen[Path]):
    DEFAULT_CSS = """
    RestoreModal {
        align: center middle;
    }
    #dialog {
        width: 80;
        height: 20;
        border: thick $background 80%;
        background: $surface;
        layout: vertical;
    }
    DataTable {
        height: 1fr;
        border: solid $secondary;
    }
    #buttons {
        height: 3;
        dock: bottom;
        layout: horizontal;
        align: center middle;
    }
    Button {
        margin-left: 1;
    }
    """

    def __init__(self, snapshot_manager: SnapshotManager):
        super().__init__()
        self.manager = snapshot_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Select Snapshot to Restore (Double click or Select & Confirm)", id="header")
            yield DataTable(id="table")
            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button("Restore", variant="primary", id="restore", flat=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Tag", "Date", "Path")

        snapshots = self.manager.list_snapshots()
        for snap in snapshots:
            ts = snap.get("timestamp", 0)
            date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            row_key = snap.get("path")
            table.add_row(snap.get("tag"), date_str, row_key, key=row_key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restore":
            table = self.query_one(DataTable)
            if table.cursor_row is not None:
                try:
                    # coordinate_to_cell_key might not be available or stable?
                    # row_key is what we set in add_row(..., key=...).
                    # get_row_at(index) returns values.
                    # We can use table.get_row(table.cursor_row) if cursor_row is index.
                    # But wait, we set explicit key.
                    # Usually table.get_row_at(cursor_row) returns list of values.
                    # But we need the Path. We stored it as key.
                    # Can we get current row key?
                    # Since Textual 0.29+, cursor_row is index.
                    # We can iterate or use coordinate.
                    # Let's rely on coordinate.
                    coord = table.cursor_coordinate
                    cell_key = table.coordinate_to_cell_key(coord)
                    row_key = cell_key.row_key
                    if row_key and row_key.value:
                        self.dismiss(Path(row_key.value))
                        return
                except Exception:
                    pass
            self.app.notify("Please select a snapshot", severity="warning")

        else:
            self.dismiss(None)
