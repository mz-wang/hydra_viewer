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

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, TextArea


class ResolvedView(Static):
    DEFAULT_CSS = """

    ResolvedView {
        width: 30%; /* Will be adjusted in main layout */
        height: 100%;
        border-left: solid $primary;
    }

    #resolved-header {
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
        width: 100%;
    }

    #resolved-text {
        width: 100%;
        height: 1fr;
        border-left: none;
        border-right: none;
    }
    """

    text = reactive("")

    def compose(self) -> ComposeResult:
        # Read-only TextArea
        yield Static("Resolved Configuration", id="resolved-header")
        yield TextArea(self.text, language="yaml", show_line_numbers=True, read_only=True, id="resolved-text")

    def update_content(self, new_content: str) -> None:
        self.text = new_content
        try:
            text_area = self.query_one(TextArea)
            text_area.text = new_content
            # rudimentary error highlighting check
            if new_content.startswith("# Error"):
                text_area.styles.background = "#330000"
            else:
                text_area.styles.background = "$surface"
        except Exception:
            pass
