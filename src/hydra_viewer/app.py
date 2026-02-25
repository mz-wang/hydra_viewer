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

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Footer, Header, TextArea

from hydra_viewer.core.merger import ConfigMerger
from hydra_viewer.core.parser import HydraConfigParser
from hydra_viewer.core.snapshot import SnapshotManager
from hydra_viewer.widgets.command_bar import CommandBar
from hydra_viewer.widgets.directory_picker import DirectoryPicker
from hydra_viewer.widgets.file_browser import FileBrowser
from hydra_viewer.widgets.module_tree import ModuleTree
from hydra_viewer.widgets.multi_panel_editor import MultiPanelEditor
from hydra_viewer.widgets.resolved_view import ResolvedView
from hydra_viewer.widgets.snapshot_modals import BackupModal, RestoreModal
from hydra_viewer.widgets.yaml_editor import YamlEditor


class HydraViewer(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #main_container {
        height: 1fr;
    }
    #left-panel {
        width: 25%;
        height: 100%;
    }
    FileBrowser {
        height: 1fr;
        min-height: 6;
    }
    ModuleTree {
        width: 100%;
        height: 1fr;
    }
    MultiPanelEditor {
        width: 50%;
    }
    YamlEditor {
        width: 50%;
    }
    ResolvedView {
        width: 25%;
    }
    .mode-indicator {
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        content-align: center middle;
    }
    .hidden {
        display: none;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "save_file", "Save"),
        Binding("ctrl+b", "create_snapshot", "Backup"),
        Binding("ctrl+r", "restore_snapshot", "Restore"),
        Binding("f5", "reload_all", "Refresh"),
        Binding("ctrl+o", "open_directory", "Open Dir"),
        Binding("ctrl+e", "toggle_editor", "Toggle Editor"),
    ]

    def __init__(self, config_dir: Path | None, **kwargs):
        super().__init__(**kwargs)
        self.config_dir = config_dir
        # Initialize with dummy or None, handle in on_mount
        if self.config_dir:
            self.init_core(self.config_dir)
        else:
            self.parser = None
            self.merger = None
            self.snapshot_manager = None

        self.current_overrides: str = ""
        self._multi_panel_mode: bool = True  # True = MultiPanelEditor, False = YamlEditor
        self._debounce_timer: Timer | None = None

    def init_core(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.parser = HydraConfigParser(self.config_dir)
        self.merger = ConfigMerger(self.config_dir)
        self.snapshot_manager = SnapshotManager(self.config_dir)
        self._org_files = self.parser.find_org_files()

    def on_mount(self) -> None:
        if not self.config_dir:
            # If no config dir, show picker immediately
            self.action_open_directory()
        else:
            # We have a config dir, verify it exists and load
            if not self.config_dir.exists():
                self.notify(f"Config directory not found: {self.config_dir}", severity="error")
                self.action_open_directory()
            else:
                self.action_reload_all(notify=False)

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main_container"):
            with Vertical(id="left-panel"):
                yield FileBrowser(self.config_dir, id="file-browser")  # type: ignore[arg-type]
                yield ModuleTree(
                    [],
                    org_files=getattr(self, "_org_files", []),
                    current_org=getattr(self.parser, "main_config_path", None) if self.parser else None,
                    id="module-tree",
                )
            yield MultiPanelEditor(id="multi-panel-editor")
            yield YamlEditor(id="yaml-editor", classes="hidden")
            yield ResolvedView()

        yield CommandBar()
        yield Footer()

    async def on_module_tree_module_selected(self, message: ModuleTree.ModuleSelected) -> None:
        if self._multi_panel_mode:
            editor = self.query_one(MultiPanelEditor)
            if message.module.path:
                editor.scroll_to_path(message.module.path)
        else:
            editor_tabs = self.query_one(YamlEditor)
            await editor_tabs.open_module(message.module)

    def on_module_tree_org_file_changed(self, message: ModuleTree.OrgFileChanged) -> None:
        if not self.parser:
            return
        self.parser.set_main_config(message.path)
        if self.merger:
            self.merger.set_main_config(message.path)
        modules = self.parser.reload()
        org_files = self.parser.find_org_files()
        tree = self.query_one(ModuleTree)
        tree.refresh_modules(modules, org_files=org_files, current_org=message.path)
        self.query_one(MultiPanelEditor).load_modules(modules)
        self.refresh_preview()
        self.notify(f"Switched to org file: {message.path.name}")

    def on_module_tree_module_edited(self, message: ModuleTree.ModuleEdited) -> None:
        if not self.parser:
            return
        try:
            self.parser.update_defaults_item(message.old, message.new_group, message.new_name)
            self.notify(f"Updated defaults: {message.new_group}/{message.new_name}")
            self.action_reload_all(notify=False)
        except Exception as e:
            self.notify(f"Failed to update defaults: {e}", severity="error")
            return
        # Reload after writing back
        modules = self.parser.reload()
        org_files = self.parser.find_org_files()
        tree = self.query_one(ModuleTree)
        tree.refresh_modules(
            modules,
            org_files=org_files,
            current_org=self.parser.main_config_path,
        )
        self.query_one(MultiPanelEditor).load_modules(modules)
        self.notify(f"Updated: {message.old.group}/{message.old.name} → {message.new_group}/{message.new_name}")

    async def on_file_browser_file_selected(self, message: FileBrowser.FileSelected) -> None:
        path = message.path
        if not self.parser:
            self._open_in_extra(path)
            return
        modules = self.parser.parse()
        module_paths = [m.path for m in modules if m.path]
        if path in module_paths:
            if self._multi_panel_mode:
                self.query_one(MultiPanelEditor).scroll_to_path(path)
            else:
                for m in modules:
                    if m.path == path:
                        await self.query_one(YamlEditor).open_module(m)
                        break
        else:
            self._open_in_extra(path)

    def _open_in_extra(self, path: Path) -> None:
        if self._multi_panel_mode:
            self.query_one(MultiPanelEditor).open_extra_file(path)
        else:
            # In tab mode, open as a regular module tab
            from hydra_viewer.core.parser import ConfigModule

            dummy = ConfigModule(group="extra", name=path.stem, path=path, resolved=True)
            self.run_worker(self.query_one(YamlEditor).open_module(dummy), exclusive=False)

    def on_file_browser_file_list_changed(self, _: FileBrowser.FileListChanged) -> None:
        # Refresh FileBrowser tree is handled internally inside FileBrowser.
        # Here we only update the org-file dropdown in ModuleTree so newly
        # created / deleted root yaml files appear in the Select list.
        # We do NOT rebuild the editor panes (load_modules) because this event
        # also fires on ordinary file-content saves (watchfiles tracks content
        # changes too), which would destroy the active TextArea and kick the
        # user out of edit mode.
        if self.parser:
            org_files = self.parser.find_org_files()
            tree = self.query_one(ModuleTree)
            tree.refresh_modules(
                self.parser.parse(),
                org_files=org_files,
                current_org=self.parser.main_config_path,
            )

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Debounced auto-save: 500 ms after the last keystroke, save & refresh preview."""
        if not self.parser:
            return
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(0.5, self._auto_save_and_refresh)

    def _auto_save_and_refresh(self) -> None:
        """Silently save the currently focused file and refresh the resolved view."""
        self._debounce_timer = None
        if self._multi_panel_mode:
            self.query_one(MultiPanelEditor).save_current_file(silent=True)
        else:
            self.query_one(YamlEditor).save_current_file(silent=True)
        self.refresh_preview()

    def action_save_file(self) -> None:
        if self._multi_panel_mode:
            self.query_one(MultiPanelEditor).save_current_file()
        else:
            self.query_one(YamlEditor).save_current_file()
        self.refresh_preview()

    def action_toggle_editor(self) -> None:
        """Toggle between MultiPanelEditor and YamlEditor (tab mode)."""
        self._multi_panel_mode = not self._multi_panel_mode
        mpe = self.query_one(MultiPanelEditor)
        ye = self.query_one(YamlEditor)
        if self._multi_panel_mode:
            mpe.remove_class("hidden")
            ye.add_class("hidden")
            self.notify("Switched to multi-panel mode")
        else:
            mpe.add_class("hidden")
            ye.remove_class("hidden")
            self.notify("Switched to tab mode")

    def on_command_bar_command_changed(self, message: CommandBar.CommandChanged) -> None:
        self.current_overrides = message.overrides
        self.refresh_preview()

    def refresh_preview(self) -> None:
        if not self.merger:
            return

        raw_overrides = self.current_overrides.split() if self.current_overrides else []
        valid_overrides = [ov for ov in raw_overrides if "=" in ov]

        try:
            merged_yaml = self.merger.merge(valid_overrides)
            view = self.query_one(ResolvedView)
            view.update_content(merged_yaml)
        except Exception:
            pass

    def action_create_snapshot(self) -> None:
        if not self.snapshot_manager:
            self.notify("No config directory loaded.", severity="error")
            return

        def handle_backup(tag: str | None) -> None:
            # Re-check snapshot_manager as static checkers might not infer it exists from closure context perfectly?
            # Actually closure captures self.
            if tag and self.snapshot_manager:
                try:
                    path = self.snapshot_manager.create(tag)
                    self.notify(f"Snapshot created: {path.name}")
                except Exception as e:
                    self.notify(f"Backup failed: {e}", severity="error")

        self.push_screen(BackupModal(), handle_backup)

    def action_restore_snapshot(self) -> None:
        if not self.snapshot_manager:
            return

        def handle_restore(path: Path | None) -> None:
            if path and self.snapshot_manager:
                try:
                    self.snapshot_manager.restore(path)
                    self.notify(f"Restored from {path.name}")
                    self.action_reload_all()
                except Exception as e:
                    self.notify(f"Restore failed: {e}", severity="error")

        self.push_screen(RestoreModal(self.snapshot_manager), handle_restore)

    def action_reload_all(self, notify: bool = True) -> None:
        if not self.parser:
            return

        # Keep merger in sync with the parser's currently active org file.
        if self.merger and self.parser.main_config_path:
            self.merger.set_main_config(self.parser.main_config_path)

        # Reload modules
        modules = self.parser.parse()
        org_files = self.parser.find_org_files()
        tree = self.query_one(ModuleTree)
        tree.refresh_modules(modules, org_files=org_files, current_org=self.parser.main_config_path)

        # Reload editors
        self.query_one(YamlEditor).reload_all_tabs()
        mpe = self.query_one(MultiPanelEditor)
        mpe.load_modules(modules)

        # Refresh preview
        self.refresh_preview()

        if notify:
            self.notify("Reloaded all configurations.")

    def action_open_directory(self) -> None:
        def handle_select(path: Path | None) -> None:
            if path:
                self.init_core(path)
                # Rebuild FileBrowser and restart watcher
                try:
                    self.query_one(FileBrowser).set_config_dir(path)
                except Exception:
                    pass
                self.action_reload_all(notify=False)
                self.notify(f"Opened {path}")
            elif not self.config_dir:
                self.notify("No directory selected.", severity="warning")

        start = self.config_dir or Path.cwd()
        self.push_screen(DirectoryPicker(start), handle_select)


if __name__ == "__main__":
    # For testing app.py directly
    pass
