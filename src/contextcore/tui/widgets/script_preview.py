"""Script preview widget for ContextCore TUI."""

import sys
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static, TextArea
from textual.containers import Vertical, Horizontal

_IS_WINDOWS = sys.platform == "win32"

__all__ = ["ScriptPreview"]


class ScriptPreview(Widget):
    """Widget for displaying and interacting with generated scripts."""

    script_content: reactive[str] = reactive("")

    DEFAULT_CSS = """
    ScriptPreview {
        height: auto;
        padding: 1;
    }

    .preview-header {
        text-style: bold;
        margin-bottom: 1;
    }

    #script-display {
        height: 20;
        margin: 1 0;
        border: solid $primary;
    }

    .button-row {
        margin-top: 1;
        align: center middle;
    }

    .status-message {
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, script: str = ""):
        super().__init__()
        self.script_content = script
        self._save_path: Optional[Path] = None

    def compose(self) -> ComposeResult:
        yield Static("Generated Installation Script", classes="preview-header")

        yield TextArea(
            self.script_content,
            language="bash",
            read_only=True,
            show_line_numbers=True,
            id="script-display"
        )

        with Horizontal(classes="button-row"):
            yield Button("Copy to Clipboard", id="copy-btn")
            yield Button("Save to File", id="save-btn")
            yield Button("Run Script", id="run-btn", variant="primary")

        yield Static("", classes="status-message", id="status-msg")

    def watch_script_content(self, script: str) -> None:
        """Update the display when script content changes."""
        try:
            text_area = self.query_one("#script-display", TextArea)
            text_area.load_text(script)
        except Exception:
            pass

    def update_script(self, script: str) -> None:
        """Update the script content."""
        self.script_content = script

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "copy-btn":
            self._copy_to_clipboard()
        elif event.button.id == "save-btn":
            self._save_to_file()
        elif event.button.id == "run-btn":
            self._show_run_instructions()

    @staticmethod
    def _default_script_path() -> Path:
        """Return platform-appropriate default save path."""
        ext = ".ps1" if _IS_WINDOWS else ".sh"
        return Path.home() / f"contextcore-install{ext}"

    def _copy_to_clipboard(self) -> None:
        """Copy script to clipboard."""
        status = self.query_one("#status-msg", Static)

        try:
            # Try pyperclip first (cross-platform)
            import pyperclip
            pyperclip.copy(self.script_content)
            status.update("Copied to clipboard!")
        except ImportError:
            # Fallback: platform-native clipboard command
            try:
                import subprocess
                cmd = ["clip.exe"] if _IS_WINDOWS else ["pbcopy"]
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    text=True,
                )
                process.communicate(input=self.script_content)
                if process.returncode == 0:
                    status.update("Copied to clipboard!")
                else:
                    save_path = self._default_script_path()
                    status.update(f"Failed to copy. Script saved to ~/{save_path.name}")
                    self._save_to_file(save_path)
            except Exception:
                save_path = self._default_script_path()
                status.update(f"Clipboard not available. Script saved to ~/{save_path.name}")
                self._save_to_file(save_path)
        except Exception as e:
            status.update(f"Copy failed: {str(e)}")

    def _save_to_file(self, path: Optional[Path] = None) -> None:
        """Save script to a file."""
        status = self.query_one("#status-msg", Static)

        if path is None:
            path = self._default_script_path()

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.script_content)

            # Set executable permission (not applicable on Windows)
            if not _IS_WINDOWS:
                path.chmod(0o755)

            self._save_path = path
            status.update(f"Saved to: {path}")
        except Exception as e:
            status.update(f"Save failed: {str(e)}")

    def _show_run_instructions(self) -> None:
        """Show instructions for running the script."""
        status = self.query_one("#status-msg", Static)

        if self._save_path and self._save_path.exists():
            run_cmd = f"powershell -File {self._save_path}" if _IS_WINDOWS else f"bash {self._save_path}"
            status.update(f"Run with: {run_cmd}")
        else:
            # Save first, then show instructions
            self._save_to_file()
            if self._save_path:
                run_cmd = f"powershell -File {self._save_path}" if _IS_WINDOWS else f"bash {self._save_path}"
                status.update(f"Saved! Run with: {run_cmd}")
            else:
                status.update("Please save the script first, then run it manually.")
