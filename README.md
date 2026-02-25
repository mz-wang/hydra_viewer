# Hydra Viewer

[![PyPI version](https://img.shields.io/pypi/v/hydra-viewer.svg)](https://pypi.org/project/hydra-viewer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Hydra Viewer** is a terminal-based developer tool designed to eliminate the friction of managing complex [Hydra](https://hydra.cc/) configurations. It provides a real-time, interactive environment to visualize, edit, and verify your configuration hierarchy without leaving the terminal.

Built with [Textual](https://textual.textualize.io/), it combines a modern TUI experience with the flexibility of Hydra's configuration system.

![Hydra Viewer Main Interface](https://raw.githubusercontent.com/mz-wang/hydra-viewer/master/docs/images/screenshot_main_tui.svg)

---

## 🌟 Key Features

### 🏢 Real-Time Merge Preview
Instantly see the fully resolved configuration. As you edit files or type overrides, Hydra Viewer merges your `defaults` list and displays the final result on the right panel. No more running your app just to check if your overrides worked!

### 📝 Hybrid Editing Modes
- **Multi-Panel Mode**: Perfect for initial setup. Each file in your `defaults` list is displayed as a separate panel, allowing you to see the entire configuration flow at once.
- **Tabbed Mode**: Ideal for focused editing of individual modules.
- **Auto-Save & Hot-Reload**: Changes are automatically saved (with a 500ms debounce) and the preview is updated instantly.

### 🧭 Advanced Navigation
- **Module Tree**: A logical view of your Hydra configuration structure. Double-click a node to update your `defaults` entry directly from the tree!
- **File Browser**: A full-featured file manager with hot-keys for creating, renaming, moving, and deleting YAML files.
- **Auto-detect**: Launching in a project root automatically finds your entry-point `config.yaml` or `conf/` directory.

### 🧪 Dynamic Overrides
The bottom command bar supports full Hydra override syntax (e.g., `model.layers=50 ++db.port=3306`). The resolved view updates live as you type, helping you debug complex CLI arguments before execution.

### 📸 Configuration Snapshots
Experiment without fear. Create full snapshots of your configuration state and restore them later. perfect for comparing different experimental setups.

---

## 🚀 Installation

### Using pip
```bash
pip install hydra-viewer
```

### Using uv (Recommended)
If you use [uv](https://github.com/astral-sh/uv), you can run it as a tool:
```bash
uv tool install hydra-viewer
```
Or run it instantly without installation:
```bash
uvx hydra-viewer
```

---

## 📖 Deep Dive & Workflow

### 1. Launching
Navigate to your project root (where `config.yaml` or a `conf/` folder resides):
```bash
hydra-viewer
```
If you are elsewhere, specify the path:
```bash
hydra-viewer /path/to/my/hydra/project
```

### 2. Editing Workflow
- Use the **left panel** to browse files.
- Press `Ctrl+E` to toggle between **Multi-Panel** and **Tab** modes.
- Edits in the center panel are synced to disk automatically. The **right panel** (Resolved View) will turn red if your YAML syntax or Hydra defaults are invalid.

### 3. Testing Overrides
Type your intended CLI arguments in the **bottom command bar**.
- `model=resnet50` (Change group)
- `db.timeout=10` (Override value)
- `++new_param=true` (Add new parameter)

### 4. Managing Snapshots
- `Ctrl+B`: Tag the current state of all config files.
- `Ctrl+R`: View and restore from your history.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Context | Action |
| --- | --- | --- |
| **Global** | | |
| `Ctrl+Q` | Any | Quit application |
| `Ctrl+S` | Editor | Force save current file |
| `Ctrl+E` | Any | Switch Editor Mode (Multi-Panel vs Tab) |
| `Ctrl+O` | Any | Open Directory Picker |
| `Ctrl+B` | Any | Create Backup Snapshot |
| `Ctrl+R` | Any | Restore from Snapshot |
| `F5` | Any | Manual Refresh of all views |
| `Tab` | Any | Switch focus between panels |
| **File Browser** | When focused | |
| `n` | | Create new file/folder |
| `r` | | Rename selected file |
| `c` | | Copy selected file |
| `m` | | Move selected file |
| `Delete` | | Delete selected file |
| **Module Tree** | When focused | |
| `Enter` | | Open file in editor |
| `Double Click` | | Edit `defaults` entry for this module |

---

## 🛠 Troubleshooting

1. **"No config directory found"**: Ensure you are in the directory containing `config.yaml` or use the command line argument.
2. **Preview is Red**: This indicates a validation error. Check the error message at the top of the preview pane for details on which line in which file is causing the issue.
3. **Symbols appear as squares**: Since this tool is built with Textual and uses certain symbols, you might see square boxes (tofu) if your terminal environment does not have [Nerd Fonts](https://www.nerdfonts.com/) installed. This is purely aesthetic and does not affect the tool's functionality.
4. **Snapshots**: Snapshots are stored in a hidden `.hydra_backups/` directory.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the file for details.
