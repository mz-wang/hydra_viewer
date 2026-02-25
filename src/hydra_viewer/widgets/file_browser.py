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

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import watchfiles
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, Tree
from textual.widgets.tree import TreeNode

# ---------------------------------------------------------------------------
# Modals
# ---------------------------------------------------------------------------


class NewFileModal(ModalScreen[str | None]):
    DEFAULT_CSS = """
    NewFileModal {
        align: center middle;
    }
    #dialog {
        layout: vertical;
        padding: 1;
        width: 60;
        height: 14;
        border: thick $background 80%;
        background: $surface;
    }
    #title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    Input {
        margin-bottom: 2;
    }
    .buttons {
        width: 100%;
        height: 3;
        content-align: center middle;
        align: center middle;
        dock: bottom;
    }
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, default_prefix: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._default_prefix = default_prefix

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("New File Name (relative to config dir):", id="title")
            yield Input(
                value=self._default_prefix,
                placeholder="e.g. group/new_file.yaml",
                id="filename",
            )
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button("Create", variant="success", id="create", flat=True)

    def on_mount(self) -> None:
        inp = self.query_one("#filename", Input)
        inp.focus()
        inp.cursor_position = len(inp.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            filename = self.query_one("#filename", Input).value
            if filename:
                self.dismiss(filename)
            else:
                self.app.notify("Filename cannot be empty", severity="error")
        else:
            self.dismiss(None)


class DeleteFileConfirmModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    DeleteFileConfirmModal {
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
    .buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    Button {
        margin: 1 2;
    }
    """

    def __init__(self, filename: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.filename = filename

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Are you sure you want to delete:\n{self.filename}?", id="question")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="primary", id="cancel", flat=True)
                yield Button("Delete", variant="error", id="delete", flat=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete":
            self.dismiss(True)
        else:
            self.dismiss(False)


class RenameFileModal(ModalScreen[str | None]):
    """Rename a file – only the filename (basename) can be changed."""

    DEFAULT_CSS = """
    RenameFileModal {
        align: center middle;
    }
    #dialog {
        layout: vertical;
        padding: 1;
        width: 60;
        height: 14;
        border: thick $background 80%;
        background: $surface;
    }
    #title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    Input {
        margin-bottom: 2;
    }
    .buttons {
        width: 100%;
        height: 3;
        align: center middle;
        dock: bottom;
    }
    Button { margin: 0 1; }
    """

    def __init__(self, old_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._old_name = old_name

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Rename File:", id="title")
            yield Input(value=self._old_name, id="newname")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button("Rename", variant="success", id="rename", flat=True)

    def on_mount(self) -> None:
        self.query_one("#newname", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rename":
            new_name = self.query_one("#newname", Input).value.strip()
            if new_name:
                self.dismiss(new_name)
            else:
                self.app.notify("Filename cannot be empty", severity="error")
        else:
            self.dismiss(None)


class _PathInputModal(ModalScreen[str | None]):
    """Shared base modal for Copy and Move: shows current rel path, user edits target."""

    DEFAULT_CSS = """
    _PathInputModal {
        align: center middle;
    }
    #dialog {
        layout: vertical;
        padding: 1;
        width: 70;
        height: 14;
        border: thick $background 80%;
        background: $surface;
    }
    #title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    Input {
        margin-bottom: 2;
    }
    .buttons {
        width: 100%;
        height: 3;
        align: center middle;
        dock: bottom;
    }
    Button { margin: 0 1; }
    """

    _action_label: str = "OK"
    _title_text: str = "Target Path (relative to config dir):"

    def __init__(self, current_rel_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_rel_path = current_rel_path

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title_text, id="title")
            yield Input(value=self._current_rel_path, id="target")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button(self._action_label, variant="success", id="confirm", flat=True)

    def on_mount(self) -> None:
        self.query_one("#target", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            target = self.query_one("#target", Input).value.strip()
            if target:
                self.dismiss(target)
            else:
                self.app.notify("Target path cannot be empty", severity="error")
        else:
            self.dismiss(None)


class CopyFileModal(_PathInputModal):
    _action_label = "Copy"
    _title_text = "Copy To (relative to config dir):"


class MoveFileModal(_PathInputModal):
    _action_label = "Move"
    _title_text = "Move To (relative to config dir):"


# ---------------------------------------------------------------------------
# FileBrowser widget
# ---------------------------------------------------------------------------


class FileBrowser(Vertical):
    config_dir: Path | None

    BINDINGS = [
        Binding("n", "add_file", "New", show=True),
        Binding("delete", "delete_file", "Delete", show=True),
        Binding("r", "rename_file", "Rename", show=True),
        Binding("c", "copy_file", "Copy", show=True),
        Binding("m", "move_file", "Move", show=True),
    ]

    DEFAULT_CSS = """
    FileBrowser {
        height: 1fr;
        background: $panel;
        border-right: solid $primary;
    }

    #browser-header {
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
        width: 100%;
    }

    #file-tree {
        height: 1fr;
    }

    #toolbar {
        height: 3;
        dock: bottom;
        background: $surface;
        align: center middle;
    }

    #toolbar Button {
        margin: 0 1;
        min-width: 4;
        content-align: center middle;
    }
    """

    class FileSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    class FileListChanged(Message):
        pass

    def __init__(self, config_dir: Path | None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config_dir = config_dir
        self._watcher_task: asyncio.Task[None] | None = None
        # Suppress watcher-triggered refreshes while we are making our own changes
        self._suppress_watch: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        label = f"Files: {self.config_dir.name}" if self.config_dir else "File Browser"
        yield Static(f"{label}", id="browser-header")
        yield Tree("Config Files", id="file-tree")
        with Horizontal(id="toolbar"):
            yield Button("+", id="add-file", variant="success", flat=True)
            yield Button("-", id="delete-file", variant="error", flat=True)

    def on_mount(self) -> None:
        self.refresh_tree()
        self._restart_watcher()

    def on_unmount(self) -> None:
        self._cancel_watcher()

    # ------------------------------------------------------------------
    # Directory change: public API used by app.py
    # ------------------------------------------------------------------

    def set_config_dir(self, path: Path | None) -> None:
        """Switch the watched directory; cancels old watcher and starts a new one."""
        self.config_dir = path
        self.refresh_tree()
        self._restart_watcher()

    # ------------------------------------------------------------------
    # File-system watcher
    # ------------------------------------------------------------------

    def _cancel_watcher(self) -> None:
        if self._watcher_task is not None:
            self._watcher_task.cancel()
            self._watcher_task = None

    def _restart_watcher(self) -> None:
        self._cancel_watcher()
        if self.config_dir and self.config_dir.exists():
            self._watcher_task = asyncio.create_task(self._watch_loop())

    async def _watch_loop(self) -> None:
        """Background coroutine: watch config_dir and auto-refresh on changes."""
        if not self.config_dir:
            return
        try:
            async for _changes in watchfiles.awatch(self.config_dir):
                if not self._suppress_watch:
                    self.refresh_tree()
                    self.post_message(self.FileListChanged())
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Tree building
    # ------------------------------------------------------------------

    def refresh_tree(self) -> None:
        if not self.config_dir:
            return

        header = self.query_one("#browser-header", Static)
        try:
            header.update(f"Explorer: {self.config_dir.name}")
        except Exception:
            pass

        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        tree.root.expand()
        self._build_tree(self.config_dir, tree.root)

    def _build_tree(self, path: Path, node: TreeNode) -> None:  # type: ignore[type-arg]
        try:
            items = list(path.iterdir())
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if item.name.startswith(".") or item.name == "__pycache__":
                    continue
                if item.is_dir():
                    dir_node = node.add(item.name, data=item, expand=False)
                    self._build_tree(item, dir_node)
                elif item.suffix in (".yaml", ".yml"):
                    node.add(item.name, data=item, allow_expand=False)
        except Exception as e:
            self.app.notify(f"Error reading directory {path}: {e}", severity="error")

    # ------------------------------------------------------------------
    # Toolbar buttons
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-file":
            self.action_add_file()
            event.stop()
        elif event.button.id == "delete-file":
            self.action_delete_file()
            event.stop()

    # ------------------------------------------------------------------
    # Tree selection
    # ------------------------------------------------------------------

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:  # type: ignore[type-arg]
        if event.node.data and isinstance(event.node.data, Path) and event.node.data.is_file():
            self.post_message(self.FileSelected(event.node.data))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _focused_dir(self) -> Path | None:
        """Return the directory context of the current cursor node."""
        if not self.config_dir:
            return None
        tree = self.query_one("#file-tree", Tree)
        node = tree.cursor_node
        if node and node.data and isinstance(node.data, Path):
            return node.data if node.data.is_dir() else node.data.parent
        return self.config_dir

    def _focused_file(self) -> Path | None:
        """Return path of current cursor node if it is a file, else None."""
        tree = self.query_one("#file-tree", Tree)
        node = tree.cursor_node
        if node and node.data and isinstance(node.data, Path) and node.data.is_file():
            return node.data
        return None

    def _rel(self, path: Path) -> str:
        """Relative posix string from config_dir."""
        if self.config_dir:
            try:
                return path.relative_to(self.config_dir).as_posix()
            except ValueError:
                pass
        return path.name

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_add_file(self) -> None:
        if not self.config_dir:
            self.app.notify("No config directory loaded.", severity="warning")
            return

        focused_dir = self._focused_dir() or self.config_dir
        try:
            rel = focused_dir.relative_to(self.config_dir).as_posix()
            default_prefix = "" if rel == "." else rel.rstrip("/") + "/"
        except ValueError:
            default_prefix = ""

        config_dir = self.config_dir

        def handle_new_file(filename: str | None) -> None:
            if not filename:
                return
            if not filename.endswith(".yaml") and not filename.endswith(".yml"):
                filename += ".yaml"
            target_path = config_dir / filename
            try:
                if target_path.exists():
                    self.app.notify(f"File already exists: {filename}", severity="warning")
                    return
                self._suppress_watch = True
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text("")
                finally:
                    self._suppress_watch = False
                self.app.notify(f"Created {filename}")
                self.refresh_tree()
                self.post_message(self.FileListChanged())
            except Exception as e:
                self.app.notify(f"Failed to create file: {e}", severity="error")

        self.app.push_screen(NewFileModal(default_prefix=default_prefix), handle_new_file)

    def action_delete_file(self) -> None:
        if not self.config_dir:
            self.app.notify("No config directory loaded.", severity="warning")
            return
        target_path = self._focused_file()
        if not target_path:
            self.app.notify("Please select a file to delete", severity="warning")
            return

        config_dir = self.config_dir

        def handle_delete(confirm: bool | None) -> None:
            if confirm:
                try:
                    self._suppress_watch = True
                    try:
                        target_path.unlink()
                    finally:
                        self._suppress_watch = False
                    self.app.notify(f"Deleted {target_path.name}")
                    self.refresh_tree()
                    self.post_message(self.FileListChanged())
                except Exception as e:
                    self.app.notify(f"Failed to delete file: {e}", severity="error")

        self.app.push_screen(
            DeleteFileConfirmModal(target_path.relative_to(config_dir).as_posix()),
            handle_delete,
        )

    def action_rename_file(self) -> None:
        if not self.config_dir:
            self.app.notify("No config directory loaded.", severity="warning")
            return
        target_path = self._focused_file()
        if not target_path:
            self.app.notify("Please select a file to rename", severity="warning")
            return

        def handle_rename(new_name: str | None) -> None:
            if not new_name:
                return
            if not new_name.endswith(".yaml") and not new_name.endswith(".yml"):
                new_name += ".yaml"
            dest = target_path.parent / new_name
            if dest.exists():
                self.app.notify(f"File already exists: {new_name}", severity="warning")
                return
            try:
                self._suppress_watch = True
                try:
                    target_path.rename(dest)
                finally:
                    self._suppress_watch = False
                self.app.notify(f"Renamed to {new_name}")
                self.refresh_tree()
                self.post_message(self.FileListChanged())
            except Exception as e:
                self.app.notify(f"Failed to rename: {e}", severity="error")

        self.app.push_screen(RenameFileModal(target_path.name), handle_rename)

    def action_copy_file(self) -> None:
        if not self.config_dir:
            self.app.notify("No config directory loaded.", severity="warning")
            return
        target_path = self._focused_file()
        if not target_path:
            self.app.notify("Please select a file to copy", severity="warning")
            return

        config_dir = self.config_dir

        def handle_copy(dest_rel: str | None) -> None:
            if not dest_rel:
                return
            if not dest_rel.endswith(".yaml") and not dest_rel.endswith(".yml"):
                dest_rel += ".yaml"
            dest = config_dir / dest_rel
            if dest.exists():
                self.app.notify(f"File already exists: {dest_rel}", severity="warning")
                return
            try:
                self._suppress_watch = True
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target_path, dest)
                finally:
                    self._suppress_watch = False
                self.app.notify(f"Copied to {dest_rel}")
                self.refresh_tree()
                self.post_message(self.FileListChanged())
            except Exception as e:
                self.app.notify(f"Failed to copy: {e}", severity="error")

        self.app.push_screen(CopyFileModal(self._rel(target_path)), handle_copy)

    def action_move_file(self) -> None:
        if not self.config_dir:
            self.app.notify("No config directory loaded.", severity="warning")
            return
        target_path = self._focused_file()
        if not target_path:
            self.app.notify("Please select a file to move", severity="warning")
            return

        config_dir = self.config_dir

        def handle_move(dest_rel: str | None) -> None:
            if not dest_rel:
                return
            if not dest_rel.endswith(".yaml") and not dest_rel.endswith(".yml"):
                dest_rel += ".yaml"
            dest = config_dir / dest_rel
            if dest.exists():
                self.app.notify(f"File already exists: {dest_rel}", severity="warning")
                return
            try:
                self._suppress_watch = True
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target_path), dest)
                finally:
                    self._suppress_watch = False
                self.app.notify(f"Moved to {dest_rel}")
                self.refresh_tree()
                self.post_message(self.FileListChanged())
            except Exception as e:
                self.app.notify(f"Failed to move: {e}", severity="error")

        self.app.push_screen(MoveFileModal(self._rel(target_path)), handle_move)
