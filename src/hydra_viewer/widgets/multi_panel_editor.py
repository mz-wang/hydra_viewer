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

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea

from hydra_viewer.core.parser import ConfigModule

_LINES_THRESHOLD = 50
_TITLE_ROWS = 2  # 1 label + 1 border row budgeted
_MIN_TEXTAREA_ROWS = 3


class _ConfirmReplaceModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    _ConfirmReplaceModal {
        align: center middle;
    }
    #dialog {
        layout: vertical;
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    .buttons {
        width: 100%;
        height: 3;
        align: center middle;
    }
    Button { margin: 0 2; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("The external file has unsaved changes.\nDiscard them and open a new file?")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="primary", id="cancel", flat=True)
                yield Button("Discard & Open", variant="error", id="discard", flat=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "discard")


class FilePane(Vertical):
    """A single file editing pane: title bar + TextArea."""

    DEFAULT_CSS = """
    FilePane {
        border: solid $primary;
        margin-bottom: 1;
        height: auto;
    }

    FilePane #pane-title {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        text-style: bold;
        padding-left: 1;
    }

    FilePane TextArea {
        height: 1fr;
        border-left: none;
        border-right: none;
    }

    FilePane TextArea:focus {
        outline: solid $accent;
        border-left: none;
        border-right: none;
    }
    """

    class SaveRequested(Message):
        def __init__(self, pane: FilePane) -> None:
            self.pane = pane
            super().__init__()

    def __init__(self, path: Path, content: str, **kwargs):
        super().__init__(**kwargs)
        self.file_path = path
        self._original_content = content
        self._content = content

    def compose(self) -> ComposeResult:
        yield Label(self._make_title(), id="pane-title", markup=False)
        lines = len(self._content.splitlines()) or 1
        ta_height = min(lines, _LINES_THRESHOLD) + 3  # Match _update_height buffer
        ta = TextArea(
            self._content,
            language="yaml",
            id="pane-textarea",
        )
        ta.show_line_numbers = True  # helpful for code
        ta.styles.height = ta_height
        yield ta

    def on_mount(self) -> None:
        self._update_height()

    def _make_title(self, dirty: bool = False) -> str:
        # Request 5: Filename without suffix + relative path hint
        name_no_ext = self.file_path.stem
        # Try to show tail path as context
        from pathlib import PureWindowsPath, WindowsPath

        if isinstance(self.file_path, WindowsPath) or isinstance(self.file_path, PureWindowsPath):
            slash_separator = "\\"
        else:
            slash_separator = "/"
        tail_path = f"...{slash_separator}{Path(*self.file_path.parts[-2:])}"
        content = f"{name_no_ext} ({tail_path})"

        marker = " *" if dirty else ""
        return f" {content}{marker}"

    def _update_height(self) -> None:
        lines = len(self._content.splitlines()) or 1
        # Fix for Issue 1: Ensure enough height when lines < threshold
        # TextArea needs slightly more space so it doesn't scroll small content.
        # Add buffer of 2 lines to capped height just to be safe for TextArea vertical padding/scrollbar reservation.
        capped = min(lines, _LINES_THRESHOLD)
        textarea_height = capped + 3  # Increased buffer

        total = textarea_height + _TITLE_ROWS
        self.styles.height = total
        ta = self.query_one("#pane-textarea", TextArea)
        ta.styles.height = textarea_height

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        ta = self.query_one("#pane-textarea", TextArea)
        dirty = ta.text != self._original_content
        title = self.query_one("#pane-title", Label)
        title.update(self._make_title(dirty=dirty))

    @property
    def is_dirty(self) -> bool:
        try:
            return self.query_one("#pane-textarea", TextArea).text != self._original_content
        except Exception:
            return False

    def get_text(self) -> str:
        return self.query_one("#pane-textarea", TextArea).text

    def save(self) -> None:
        text = self.get_text()
        self.file_path.write_text(text, encoding="utf-8")
        self._original_content = text
        title = self.query_one("#pane-title", Label)
        title.update(self._make_title(dirty=False))

    def reload(self) -> None:
        if self.file_path.exists():
            self._content = self.file_path.read_text(encoding="utf-8")
            self._original_content = self._content
            ta = self.query_one("#pane-textarea", TextArea)
            ta.text = self._content
            self._update_height()
            title = self.query_one("#pane-title", Label)
            title.update(self._make_title(dirty=False))


class ExtraFilePane(FilePane):
    """A file pane for files outside the defaults list. Shown at the top."""

    DEFAULT_CSS = """
    ExtraFilePane {
        border: solid $warning;
        margin-bottom: 1;
        height: auto;
    }

    ExtraFilePane #pane-title {
        height: 1;
        background: #2a2a00;
        color: $warning;
        text-style: bold;
        padding-left: 1;
    }

    ExtraFilePane TextArea {
        height: 1fr;
    }
    """

    def _make_title(self, dirty: bool = False) -> str:
        marker = " *" if dirty else ""
        from pathlib import PureWindowsPath, WindowsPath

        if isinstance(self.file_path, WindowsPath) or isinstance(self.file_path, PureWindowsPath):
            slash_separator = "\\"
        else:
            slash_separator = "/"
        path_str = f"...{slash_separator}{Path(*self.file_path.parts[-2:])}"

        prefix = f"[External]{marker}"
        return f" {prefix}  {path_str}"


class MultiPanelEditor(Vertical):
    """
    Multi-panel editor showing each config file as an independent scrollable pane.
    An optional ExtraFilePane at the top shows files opened from the file browser
    that are not part of the current defaults list.
    """

    DEFAULT_CSS = """
    MultiPanelEditor {
        height: 100%;
    }

    #panel-scroller {
        height: 1fr;
        padding: 0;
        border-left: none;
        border-right: none;
    }
    """

    class FileSaved(Message):
        """Drop-in replacement for YamlEditor.FileSaved."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._module_paths: list[Path] = []  # track defaults-derived panes by path
        self._extra_path: Path | None = None

    # ------------------------------------------------------------------ #
    # Compose                                                              #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="panel-scroller")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def load_modules(self, modules: list[ConfigModule]) -> None:
        """Rebuild panes from a list of ConfigModule (defaults order)."""
        scroller = self.query_one("#panel-scroller", VerticalScroll)

        # Remove all existing module panes (not ExtraFilePane) and placeholder labels.
        # Do NOT use IDs on new panes to avoid DuplicateIds when the old removal
        # is still being processed by the event queue.
        for child in list(scroller.children):
            if not isinstance(child, ExtraFilePane):
                child.remove()

        self._module_paths = []

        for m in modules:
            if not m.resolved or not m.path:
                # Show a placeholder label
                scroller.mount(
                    Label(
                        f"  ⚠ Unresolved: {m.group}/{m.name}",
                        classes="unresolved-placeholder",
                    )
                )
                continue

            try:
                content = m.path.read_text(encoding="utf-8")
            except Exception as e:
                content = f"# Error reading file: {e}"

            pane = FilePane(m.path, content)  # no id= to prevent DuplicateIds on reload
            scroller.mount(pane)
            self._module_paths.append(m.path)

    def open_extra_file(self, path: Path) -> None:
        """Open a file that is not in the defaults list in the ExtraFilePane."""
        existing = self._get_extra_pane()

        if existing and existing.is_dirty:

            def handle_confirm(discard: bool | None) -> None:
                if discard:
                    self._load_extra(path)

            self.app.push_screen(_ConfirmReplaceModal(), handle_confirm)
        else:
            self._load_extra(path)

    def save_all(self) -> None:
        """Save all open panes (both module panes and ExtraFilePane)."""
        for pane in self.query(FilePane):
            if pane.is_dirty:
                try:
                    pane.save()
                    self.post_message(self.FileSaved(pane.file_path))
                    self.app.notify(f"Saved {pane.file_path.name}")
                except Exception as e:
                    self.app.notify(f"Error saving {pane.file_path.name}: {e}", severity="error")

    def save_pane(self, path: Path) -> None:
        """Save the pane for a specific file path."""
        pane = self._find_pane(path)
        if pane and pane.is_dirty:
            try:
                pane.save()
                self.post_message(self.FileSaved(path))
                self.app.notify(f"Saved {path.name}")
            except Exception as e:
                self.app.notify(f"Error saving {path.name}: {e}", severity="error")

    def reload_all(self) -> None:
        """Reload all open panes from disk."""
        for pane in self.query(FilePane):
            pane.reload()

    def scroll_to_path(self, path: Path) -> None:
        """Scroll to the pane associated with the given path."""
        pane = self._find_pane(path)
        if pane:
            pane.scroll_visible()

    def save_current_file(self, *, silent: bool = False) -> None:
        """Save whichever pane currently has focus (compatible shim for app.py)."""
        focused = self.app.focused
        # Walk up from focused widget to find FilePane
        widget = focused
        while widget is not None:
            if isinstance(widget, FilePane):
                try:
                    widget.save()
                    self.post_message(self.FileSaved(widget.file_path))
                    if not silent:
                        self.app.notify(f"Saved {widget.file_path.name}")
                except Exception as e:
                    self.app.notify(f"Error saving: {e}", severity="error")
                return
            widget = widget.parent  # type: ignore[assignment]

    def reload_all_tabs(self) -> None:
        """Shim for YamlEditor API compatibility."""
        self.reload_all()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _pane_id(path: Path) -> str:
        return "filepane-" + path.as_posix().replace("/", "-").replace(".", "-").replace(":", "-")

    def _find_pane(self, path: Path) -> FilePane | None:
        for pane in self.query(FilePane):
            if pane.file_path == path:
                return pane
        return None

    def _get_extra_pane(self) -> ExtraFilePane | None:
        panes = list(self.query(ExtraFilePane))
        return panes[0] if panes else None

    def _load_extra(self, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            content = f"# Error reading file: {e}"

        scroller = self.query_one("#panel-scroller", VerticalScroll)
        existing = self._get_extra_pane()

        if existing:
            existing.file_path = path
            existing._original_content = content
            existing._content = content
            existing.reload()
        else:
            extra = ExtraFilePane(path, content, id="extra-file-pane")
            scroller.mount(extra, before=scroller.children[0] if scroller.children else None)

        self._extra_path = path

        # Scroll to top and focus the extra pane
        self.call_after_refresh(self._focus_extra)

    def _focus_extra(self) -> None:
        extra = self._get_extra_pane()
        if extra:
            scroller = self.query_one("#panel-scroller", VerticalScroll)
            scroller.scroll_home(animate=False)
            try:
                extra.query_one("#pane-textarea", TextArea).focus()
            except Exception:
                pass
