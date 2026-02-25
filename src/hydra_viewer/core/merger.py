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
from typing import Any

import yaml
from omegaconf import DictConfig, OmegaConf


class ConfigMerger:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self._main_config_path: Path | None = None

    def set_main_config(self, path: Path) -> None:
        """Override the main config file used for merging (replaces auto-discovery)."""
        self._main_config_path = path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def merge(self, overrides: list[str] | None = None) -> str:
        """
        Compose the configuration using Hydra's compose API, then apply overrides.

        Falls back to a manual OmegaConf merge when Hydra is unavailable or the
        config structure cannot be composed (e.g. malformed YAML).

        Resolution behaviour:
        - Attempts full interpolation (resolve=True).
        - If resolution fails (e.g. ${hydra:...} runtime resolvers), falls back to
          resolve=False and prepends a warning comment so the rest of the config is
          still readable.
        """
        config_name = self._find_config_name()
        if not config_name:
            return "# Error: No config.yaml found"

        try:
            return self._merge_with_hydra(config_name, overrides or [])
        except Exception as hydra_err:
            # Hydra not installed, config incompatible, etc. – fall back to manual.
            fallback = self._merge_manual(overrides)
            return f"# ⚠ Hydra compose failed ({hydra_err}); showing manual OmegaConf merge\n" + fallback

    # ------------------------------------------------------------------
    # Hydra compose path
    # ------------------------------------------------------------------

    def _merge_with_hydra(self, config_name: str, overrides: list[str]) -> str:
        from hydra import compose, initialize_config_dir
        from hydra.core.global_hydra import GlobalHydra

        abs_config_dir = str(self.config_dir.resolve())

        GlobalHydra.instance().clear()
        with initialize_config_dir(config_dir=abs_config_dir, version_base=None):
            cfg = compose(config_name=config_name, overrides=overrides)

        # Attempt full interpolation resolution first.
        try:
            return OmegaConf.to_yaml(cfg, resolve=True)
        except Exception as resolve_err:
            # Some ${...} values couldn't be resolved (e.g. ${hydra:runtime.cwd}).
            # Show the unresolved template; the viewer is still useful.
            raw = OmegaConf.to_yaml(cfg, resolve=False)
            return f"# ⚠ Warning: some interpolations could not be resolved\n#   ({resolve_err})\n" + raw

    # ------------------------------------------------------------------
    # Manual OmegaConf fallback (original implementation)
    # ------------------------------------------------------------------

    def _merge_manual(self, overrides: list[str] | None = None) -> str:
        try:
            main_cfg_path = self._find_main_config()
            if not main_cfg_path:
                return "# Error: No config.yaml found"

            base_cfg = OmegaConf.load(main_cfg_path)
            if not isinstance(base_cfg, DictConfig):
                base_cfg = DictConfig(base_cfg)

            defaults = base_cfg.get("defaults", [])
            defaults_list: list[Any] = OmegaConf.to_container(defaults, resolve=False) if defaults else []  # type: ignore

            merged_cfg = OmegaConf.create({})

            for item in defaults_list:
                if isinstance(item, str):
                    if item == "_self_":
                        merged_cfg = OmegaConf.merge(merged_cfg, base_cfg)
                    else:
                        self._merge_module_by_name(merged_cfg, item)
                elif isinstance(item, dict):
                    for group, name in item.items():
                        if not isinstance(group, str):
                            continue
                        if group == "override" or group.startswith("override "):
                            continue
                        if isinstance(name, str):
                            self._merge_module_by_group(merged_cfg, group, name)

            if not defaults_list:
                merged_cfg = base_cfg

            if overrides:
                clean_overrides = []
                for ov in overrides:
                    if ov.startswith("~"):
                        continue
                    if "=" not in ov:
                        continue
                    key, value = ov.split("=", 1)
                    if key.startswith("++"):
                        key = key[2:]
                    elif key.startswith("+"):
                        key = key[1:]
                    clean_overrides.append(f"{key}={value}")
                if clean_overrides:
                    override_conf = OmegaConf.from_dotlist(clean_overrides)
                    merged_cfg = OmegaConf.merge(merged_cfg, override_conf)

            return OmegaConf.to_yaml(merged_cfg)

        except Exception as e:
            return f"# Error merging config:\n# {str(e)}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_config_name(self) -> str | None:
        p = self._find_main_config()
        return p.stem if p else None

    def _find_main_config(self) -> Path | None:
        # Prefer explicitly set path (from user's org-file selection).
        if self._main_config_path and self._main_config_path.exists():
            return self._main_config_path
        candidates = list(self.config_dir.glob("*.yaml"))
        for cand in candidates:
            try:
                content = yaml.safe_load(cand.read_text(encoding="utf-8"))
                if content and "defaults" in content:
                    return cand
            except Exception:
                continue
        return candidates[0] if candidates else None

    def _merge_module_by_name(self, cfg: DictConfig, name: str) -> None:
        p = self.config_dir / f"{name}.yaml"
        if p.exists():
            mod_cfg = OmegaConf.load(p)
            cfg.merge_with(mod_cfg)

    def _merge_module_by_group(self, cfg: DictConfig, group: str, name: str) -> None:
        p = self.config_dir / group / f"{name}.yaml"
        if p.exists():
            mod_cfg = OmegaConf.load(p)
            group_cfg = OmegaConf.create({group: mod_cfg})
            cfg.merge_with(group_cfg)

            loaded = OmegaConf.load(p)
            group_cfg = OmegaConf.create({group: loaded})
            cfg.merge_with(group_cfg)
