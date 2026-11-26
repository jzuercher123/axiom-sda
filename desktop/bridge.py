import os
import pathlib
import subprocess
import webview


class DesktopBridge:
    def __init__(self, data_dir: pathlib.Path, window_getter):
        self.data_dir = data_dir
        self._get_window = window_getter

    def pick_file(self, file_types: tuple[str, ...] = ("All files (*.*)",)) -> str | None:
        win = self._get_window()
        if win is None:
            return None
        result = win.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=file_types,
        )
        return result[0] if result else None

    def pick_folder(self) -> str | None:
        win = self._get_window()
        if win is None:
            return None
        result = win.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None

    def open_folder(self, subfolder: str = "") -> bool:
        target = (self.data_dir / subfolder).resolve()
        if not str(target).startswith(str(self.data_dir.resolve())):
            return False
        target.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return True