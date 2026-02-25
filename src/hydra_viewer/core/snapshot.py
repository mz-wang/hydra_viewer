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

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from hydra_viewer.core.parser import HydraConfigParser


@dataclass
class SnapshotMeta:
    tag: str
    timestamp: float
    modules: list[str]  # List of module paths relative to config_dir


class SnapshotManager:
    BACKUP_DIR_NAME = ".hydra_backups"

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.backup_root = config_dir / self.BACKUP_DIR_NAME
        self.parser = HydraConfigParser(config_dir)

    def verify_backup_dir(self) -> None:
        if not self.backup_root.exists():
            self.backup_root.mkdir(exist_ok=True)

    def create(self, tag: str) -> Path:
        self.verify_backup_dir()
        timestamp = time.time()
        # Create folder name: YYYYMMDD_HHMMSS_{tag}
        time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        folder_name = f"{time_str}_{tag}"
        backup_path = self.backup_root / folder_name
        backup_path.mkdir()

        # Get all current modules
        modules = self.parser.parse()
        relative_paths = []

        # Backup config.yaml (root)
        if self.parser.main_config_path:
            try:
                shutil.copy2(self.parser.main_config_path, backup_path / self.parser.main_config_path.name)
                relative_paths.append(self.parser.main_config_path.name)
            except Exception:
                pass

        # Backup resolved modules
        for mod in modules:
            if mod.resolved and mod.path:
                try:
                    # Maintain directory structure inside backup?
                    # E.g. model/resnet.yaml -> backup/model/resnet.yaml
                    rel_path = mod.path.relative_to(self.config_dir)
                    dest = backup_path / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(mod.path, dest)
                    relative_paths.append(str(rel_path))
                except Exception:
                    pass

        # Save metadata
        meta = SnapshotMeta(tag=tag, timestamp=timestamp, modules=relative_paths)
        with open(backup_path / "meta.json", "w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, indent=2)

        return backup_path

    def list_snapshots(self) -> list[dict]:
        if not self.backup_root.exists():
            return []

        snapshots = []
        for d in self.backup_root.iterdir():
            if d.is_dir():
                meta_file = d / "meta.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, encoding="utf-8") as f:
                            data = json.load(f)
                            # add path to data
                            data["path"] = str(d)
                            snapshots.append(data)
                    except Exception:
                        pass

        # Sort by timestamp desc
        snapshots.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return snapshots

    def restore(self, snapshot_path: Path) -> None:
        # 1. Create a "pre-restore" backup automatically
        self.create("pre_restore_backup")

        # 2. Restore files
        # We should clear existing config files or overwrite?
        # Overwrite is safer, but if user added new files they stick around.
        # Ideally, we restore exactly the state in snapshot.

        # Check meta
        meta_file = snapshot_path / "meta.json"
        if not meta_file.exists():
            raise FileNotFoundError("Snapshot metadata not found")

        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)

        files = meta.get("modules", [])

        for rel_path_str in files:
            source = snapshot_path / rel_path_str
            dest = self.config_dir / rel_path_str

            if source.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
