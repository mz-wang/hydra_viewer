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

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from omegaconf import DictConfig, OmegaConf


@dataclass
class ConfigModule:
    group: str
    name: str
    path: Path | None
    resolved: bool
    is_group: bool = False  # If it's a config group but specific item not selected? Or just a module.

    def __str__(self) -> str:
        return f"{self.group}={self.name}"


class HydraConfigParser:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.main_config_path = self._find_main_config()

    def _find_main_config(self) -> Path | None:
        # Typically config.yaml, or a file with defaults list
        candidates = list(self.config_dir.glob("*.yaml"))
        for cand in candidates:
            # simple heuristic: check if it has defaults
            try:
                content = yaml.safe_load(cand.read_text(encoding="utf-8"))
                if content and "defaults" in content:
                    return cand
            except Exception:
                continue
        return candidates[0] if candidates else None

    def parse(self) -> list[ConfigModule]:
        modules: list[ConfigModule] = []
        if not self.main_config_path:
            return modules

        try:
            cfg = OmegaConf.load(self.main_config_path)
            if not isinstance(cfg, DictConfig):
                return modules
            defaults_node = cfg.get("defaults", [])
            # Convert to python types, don't resolve interpolations yet as we just want structure
            defaults: list[Any] = OmegaConf.to_container(defaults_node, resolve=False) if defaults_node else []  # type: ignore
        except Exception:
            return modules

        if not defaults:
            return modules

        for item in defaults:
            # item can be string or dict
            if isinstance(item, str):
                if item == "_self_":
                    continue
                # item like "db/mysql" is group=db, name=mysql
                if "/" in item:
                    group, name = item.rsplit("/", 1)
                    self._add_module(modules, group, name)
                else:
                    # item might be a name referring to a file in root? or a group?
                    # In Hydra, a string item usually refers to a config group if it's a directory,
                    # or a config file if it's a file.
                    # But without 'group=name' syntax it's ambiguous.
                    # We will try to resolve it as a file relative to config_dir first
                    self._resolve_string_item(modules, item)

            elif isinstance(item, dict):
                for group, name in item.items():
                    if not isinstance(group, str):
                        continue

                    if isinstance(name, str):
                        self._add_module(modules, group, name)
                    # Handle list of names if valid in Hydra? (Usually one selection)

        return modules

    def _resolve_string_item(self, modules: list[ConfigModule], item: str) -> None:
        # Check if item corresponds to a file
        p = self.config_dir / f"{item}.yaml"
        if p.exists():
            modules.append(ConfigModule(group="root", name=item, path=p, resolved=True))
            return

        # Check if item is a directory (config group)
        # But if it's just 'db', we don't know which db is selected unless defaults list has it.
        # Wait, defaults list item IS the selection.
        # If item is "db/mysql", we handled it.
        # If item is "some_config", it's likely a file.
        pass

    def _add_module(self, modules: list[ConfigModule], group: str, name: str) -> None:
        # Construct expected path
        # group can be nested "group/subgroup"
        rel_path = f"{group}/{name}.yaml"
        full_path = self.config_dir / rel_path

        resolved = full_path.exists()
        modules.append(ConfigModule(group=group, name=name, path=full_path if resolved else None, resolved=resolved))

    # ------------------------------------------------------------------ #
    # Org-file management                                                  #
    # ------------------------------------------------------------------ #

    def find_org_files(self) -> list[Path]:
        """Return all yaml files in config_dir root."""
        result: list[Path] = []
        for p in sorted(self.config_dir.glob("*.yaml")) + sorted(self.config_dir.glob("*.yml")):
            result.append(p)
        return result

    def set_main_config(self, path: Path) -> None:
        """Switch the active org file. Call reload() afterwards to refresh parsed modules."""
        self.main_config_path = path

    def reload(self) -> list[ConfigModule]:
        """Re-parse using the current main_config_path and return the fresh module list."""
        return self.parse()

    def update_defaults_item(self, old: "ConfigModule", new_group: str, new_name: str) -> None:
        """
        Locate the defaults entry for *old* in the org file and rewrite it to
        new_group/new_name, preserving surrounding YAML formatting.

        Supported formats inside the defaults list:
          String item:  ``- old_group/old_name``
          Dict item:    ``- old_group: old_name``
          Dict+override: ``- override old_group: old_name``
        """
        if not self.main_config_path or not self.main_config_path.exists():
            raise FileNotFoundError("No org file is loaded.")

        text = self.main_config_path.read_text(encoding="utf-8")

        old_group = re.escape(old.group)
        old_name = re.escape(old.name)

        # Pattern 1: "  - group/name" (string style, possibly with spaces)
        pat_str = re.compile(
            r"^(?P<indent>[ \t]*)- (?P<override>override )?(?P<gn>" + old_group + r"/" + old_name + r")(?P<rest>\s*)$",
            re.MULTILINE,
        )
        # Pattern 2: "  - group: name" or "  - override group: name"
        pat_dict = re.compile(
            r"^(?P<indent>[ \t]*)- (?P<override>override )?" + old_group + r"\s*:\s*" + old_name + r"(?P<rest>\s*)$",
            re.MULTILINE,
        )

        def _repl_str(m: re.Match) -> str:  # type: ignore[type-arg]
            override = m.group("override") or ""
            return f"{m.group('indent')}- {override}{new_group}/{new_name}{m.group('rest')}"

        def _repl_dict(m: re.Match) -> str:  # type: ignore[type-arg]
            override = m.group("override") or ""
            return f"{m.group('indent')}- {override}{new_group}: {new_name}{m.group('rest')}"

        new_text, n1 = pat_str.subn(_repl_str, text)
        if n1 == 0:
            new_text, n2 = pat_dict.subn(_repl_dict, text)
            if n2 == 0:
                raise ValueError(f"Could not find defaults entry for {old.group}/{old.name} in {self.main_config_path}")

        self.main_config_path.write_text(new_text, encoding="utf-8")
