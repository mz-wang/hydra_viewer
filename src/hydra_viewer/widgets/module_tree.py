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
from textual.message import Message
from textual.widgets import Button, Input, Label, Select, Static, Tree

from hydra_viewer.core.parser import ConfigModule

_NO_EDIT_GROUPS = {"_self_", "override _self_"}


class ModuleTree(Vertical):
    DEFAULT_CSS = """
    ModuleTree {
        width: 30%;
        height: 100%;
        background: $panel;
        color: $text;
        border-right: solid $primary;
    }

    #org-select-label {
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
    }

    #org-select {
        height: auto;
        margin: 0;
    }

    #org-input {
        display: none;
        margin: 0;
    }

    #org-input.visible {
        display: block;
    }

    #module-tree {
        height: 1fr;
    }

    #edit-panel {
        height: auto;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
        display: none;
    }

    #edit-panel.visible {
        display: block;
    }

    #edit-label {
        height: 1;
        color: $text-muted;
    }

    #edit-input {
        margin: 0;
    }

    #edit-buttons {
        height: 3;
        align: right middle;
    }

    #edit-buttons Button {
        min-width: 8;
        margin: 0 1;
    }
    """

    class ModuleSelected(Message):
        """Selected module message."""

        def __init__(self, module: ConfigModule) -> None:
            self.module = module
            super().__init__()

    class OrgFileChanged(Message):
        """Emitted when the user switches the org file via dropdown."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    class ModuleEdited(Message):
        """Emitted when a node is successfully edited and written back to org file."""

        def __init__(self, old: ConfigModule, new_group: str, new_name: str) -> None:
            self.old = old
            self.new_group = new_group
            self.new_name = new_name
            super().__init__()

    def __init__(
        self,
        modules: list[ConfigModule],
        org_files: list[Path] | None = None,
        current_org: Path | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.modules = modules
        self.org_files: list[Path] = org_files or []
        self.current_org = current_org

        self._last_selected: ConfigModule | None = None
        self._last_select_time: float = 0.0
        self._editing_module: ConfigModule | None = None

    # ------------------------------------------------------------------ #
    # Compose & build                                                      #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        # Using Static for header-like appearance but customizable
        yield Static("Config Tree", id="org-select-label")
        options = self._build_select_options()
        yield Select(options, id="org-select", allow_blank=False)
        yield Input(placeholder="Enter filename manually...", id="org-input")
        yield Tree("Config Modules", id="module-tree")
        with Vertical(id="edit-panel"):
            yield Label("Edit node (new_group/new_name):", id="edit-label")
            yield Input(placeholder="group/name", id="edit-input")
            with Horizontal(id="edit-buttons"):
                yield Button("Cancel", variant="default", id="edit-cancel", flat=True)
                yield Button("Apply", variant="success", id="edit-apply", flat=True)

    def on_mount(self) -> None:
        self._rebuild_tree()
        self._update_select()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _build_select_options(self) -> list[tuple[str, str | Path]]:
        options: list[tuple[str, str | Path]] = [(p.name, p) for p in self.org_files]
        options.append(("Manual Input...", "MANUAL"))
        return options

    def _update_select(self) -> None:
        sel = self.query_one("#org-select", Select)
        inp = self.query_one("#org-input", Input)

        options = self._build_select_options()

        # Suppress Select.Changed events during programmatic updates to prevent
        # the spurious Changed events fired by set_options/value assignment from
        # being misinterpreted as user changes, which would cause an infinite
        # org-file switching loop.
        with self.prevent(Select.Changed):
            sel.set_options(options)

            if self.current_org and self.current_org in self.org_files:
                sel.value = self.current_org
                inp.remove_class("visible")
            else:
                # If current_org is not in the list, it might be a manual file
                # or simply not found. We select "Manual Input..." and show input
                sel.value = "MANUAL"
                inp.add_class("visible")
                if self.current_org:
                    # Try to display something useful if we have a path
                    try:
                        name = self.current_org.name
                        inp.value = name
                    except Exception:
                        pass

    def _rebuild_tree(self) -> None:
        tree = self.query_one("#module-tree", Tree)
        tree.clear()
        tree.root.expand()
        self._build_tree(tree)

    def _build_tree(self, tree: Tree) -> None:  # type: ignore[type-arg]
        groups: dict[str, list[ConfigModule]] = {}
        for m in self.modules:
            group_key = m.group
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(m)

        for group_name, mods in sorted(groups.items()):
            group_node = tree.root.add(group_name, expand=True)
            for m in mods:
                label = f"{m.name}"
                if not m.resolved:
                    label += " ⚠"
                group_node.add_leaf(label, data=m)

    def _is_editable(self, module: ConfigModule) -> bool:
        if module.group in _NO_EDIT_GROUPS:
            return False
        if module.group == "root":
            return False
        return True

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def refresh_modules(
        self,
        new_modules: list[ConfigModule],
        org_files: list[Path] | None = None,
        current_org: Path | None = None,
    ) -> None:
        self.modules = new_modules
        if org_files is not None:
            self.org_files = org_files
        if current_org is not None:
            self.current_org = current_org
        self._rebuild_tree()
        self._update_select()

    # ------------------------------------------------------------------ #
    # Event handlers                                                       #
    # ------------------------------------------------------------------ #

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:  # type: ignore[type-arg]
        module: ConfigModule | None = event.node.data  # type: ignore[assignment]
        if module is None:
            return

        self.post_message(self.ModuleSelected(module))

        now = time.monotonic()
        if module is self._last_selected and (now - self._last_select_time) < 0.6:
            # Double-click detected
            if self._is_editable(module):
                self._start_edit(module)
            else:
                self.app.notify("This entry cannot be edited.", severity="warning")
        else:
            self._last_selected = module
            self._last_select_time = now

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "org-select":
            return

        inp = self.query_one("#org-input", Input)

        if event.value == "MANUAL":
            inp.add_class("visible")
            inp.focus()
            return

        inp.remove_class("visible")  # Ensure hidden if not manual

        if not isinstance(event.value, Path):
            return

        path: Path = event.value
        if path != self.current_org:
            self.current_org = path
            self.post_message(self.OrgFileChanged(path))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "org-input":
            filename = event.value.strip()
            if not filename:
                return

            # Let's try to get parent from first org file if available
            parent = Path(".")
            if self.org_files:
                parent = self.org_files[0].parent

            path = parent / filename
            self.current_org = path
            self.post_message(self.OrgFileChanged(path))

        elif event.input.id == "edit-input":
            self._apply_edit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "edit-cancel":
            self._cancel_edit()
        elif event.button.id == "edit-apply":
            self._apply_edit()

    # ------------------------------------------------------------------ #
    # Edit logic                                                           #
    # ------------------------------------------------------------------ #

    def _start_edit(self, module: ConfigModule) -> None:
        self._editing_module = module
        panel = self.query_one("#edit-panel")
        panel.add_class("visible")
        inp = self.query_one("#edit-input", Input)
        inp.value = f"{module.group}/{module.name}"
        inp.focus()
        lbl = self.query_one("#edit-label", Label)
        lbl.update(f"Editing: {module.group}/{module.name}")

    def _cancel_edit(self) -> None:
        self._editing_module = None
        panel = self.query_one("#edit-panel")
        panel.remove_class("visible")

    def _apply_edit(self) -> None:
        if not self._editing_module:
            return

        inp = self.query_one("#edit-input", Input)
        raw = inp.value.strip()

        if "/" not in raw:
            self.app.notify("Format must be group/name", severity="error")
            return

        new_group, new_name = raw.rsplit("/", 1)
        if not new_group or not new_name:
            self.app.notify("Both group and name must be non-empty", severity="error")
            return

        self.post_message(self.ModuleEdited(self._editing_module, new_group, new_name))
        self._cancel_edit()
