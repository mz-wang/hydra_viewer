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

import yaml


def find_config_root(start_path: Path) -> Path | None:
    """
    Find the root configuration directory by looking for a config.yaml
    (or any yaml) that contains a 'defaults' list, traversing upwards.

    Args:
        start_path: The path to start searching from

    Returns:
        The path to the configuration directory if found, else None
    """
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    root = current.root

    while current != root:
        # Check for config.yaml or main.yaml or similar that has defaults
        # For simplicity in MVP, we look for any .yaml file that has a 'defaults' list
        # detailed hydra logic might be more complex, but this is a good heuristic

        for yaml_file in current.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict) and "defaults" in content and isinstance(content["defaults"], list):
                        return current
            except Exception:
                continue

        current = current.parent

    return None
