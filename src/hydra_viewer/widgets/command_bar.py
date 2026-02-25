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
from textual.message import Message
from textual.widgets import Input, Static


class CommandBar(Static):
    DEFAULT_CSS = """
    CommandBar {
        dock: bottom;
        height: 4;
        background: $boost;
        padding: 0;
        layout: horizontal;
        align: left middle;
    }

    #cmd-label {
        width: 16;
        height: 100%;
        background: $accent;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

    Input {
        /* Do NOT set height: 100% — Input text is always rendered at the top of
           the widget, so stretching it to fill the container causes text to appear
           top-aligned.  Instead let Input use its natural (auto) height and rely on
           the parent's `align: left middle` to centre it vertically. */
        height: auto;
        border: none;
    }
    """

    class CommandChanged(Message):
        """Sent when the command string changes (e.g. overrides updated)."""

        def __init__(self, overrides: str) -> None:
            self.overrides = overrides
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("Overrides:", id="cmd-label")
        yield Input(placeholder="e.g. ++model.layers=101", id="cmd-input")

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.CommandChanged(event.value))
