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

import argparse
from importlib.metadata import version as _pkg_version
from pathlib import Path

import yaml

from hydra_viewer.app import HydraViewer

_VERSION = _pkg_version("hydra-viewer")


def _detect_config_dir() -> Path | None:
    """Try to find a Hydra config directory in CWD.

    Looks for a YAML file at the root of CWD that contains a ``defaults``
    key — the standard Hydra entry-point heuristic.  Returns CWD if found,
    otherwise None (the app will show the directory picker).
    """
    cwd = Path.cwd()
    for p in sorted(cwd.glob("*.yaml")) + sorted(cwd.glob("*.yml")):
        try:
            content = yaml.safe_load(p.read_text(encoding="utf-8"))
            if content and "defaults" in content:
                return cwd
        except Exception:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(
        prog="hydra-viewer",
        description="A TUI for browsing and editing Hydra configuration directories.",
        epilog=(
            "If PATH is omitted the current directory is scanned for a Hydra config;\n"
            "when none is found an interactive directory picker is shown inside the TUI."
        ),
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        metavar="PATH",
        help="path to the Hydra configuration directory",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {_VERSION}",
    )
    args = parser.parse_args()

    config_dir = args.path

    if config_dir is None:
        # No explicit path: try to auto-detect from CWD.
        # If CWD contains a YAML file with a 'defaults' list the app loads it
        # directly; otherwise config_dir stays None and the directory picker is shown.
        config_dir = _detect_config_dir()

    if config_dir and not config_dir.exists():
        print(f"Error: Config directory '{config_dir}' does not exist.")
        return

    app = HydraViewer(config_dir=config_dir)
    app.run()


if __name__ == "__main__":
    main()
