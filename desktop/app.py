import threading
from PIL import Image, ImageDraw
import pystray
import webview

from desktop.bridge import DesktopBridge
from desktop.paths import get_app_data_dir, get_workspace_root
from desktop.process_manager import ProcessManager

DASHBOARD_URL = "http://127.0.0.1:8000"


def _make_tray_icon() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((12, 12, 52, 52), fill=(99, 102, 241, 255))
    draw.ellipse((24, 24, 40, 40), fill=(248, 250, 252, 255))
    return img


def main() -> None:
    data_dir = get_app_data_dir()
    workspace_root = get_workspace_root()
    manager = ProcessManager(data_dir, workspace_root)
    manager.start_all()
    manager.wait_for_http(DASHBOARD_URL, timeout_s=20.0)

    window_holder: dict[str, webview.Window | None] = {"win": None}
    bridge = DesktopBridge(data_dir, lambda: window_holder["win"])

    win = webview.create_window(
        title="Axiom SDA",
        url=DASHBOARD_URL,
        js_api=bridge,
        width=1360,
        height=860,
        min_size=(1024, 680),
    )
    window_holder["win"] = win

    shutting_down = threading.Event()

    def on_show(icon, item):
        if window_holder["win"] is not None:
            window_holder["win"].show()

    def on_restart(icon, item):
        manager.start_all()
        manager.wait_for_http(DASHBOARD_URL, timeout_s=15.0)
        if window_holder["win"] is not None:
            window_holder["win"].load_url(DASHBOARD_URL)

    def on_open_logs(icon, item):
        bridge.open_folder("logs")

    def on_quit(icon, item):
        shutting_down.set()
        manager.stop_all()
        icon.stop()
        if window_holder["win"] is not None:
            window_holder["win"].destroy()

    def on_closing():
        if shutting_down.is_set():
            return True
        if window_holder["win"] is not None:
            window_holder["win"].hide()
        return False

    win.events.closing += on_closing

    tray = pystray.Icon(
        "axiom_sda",
        _make_tray_icon(),
        "Axiom SDA",
        menu=pystray.Menu(
            pystray.MenuItem("Open Axiom SDA", on_show, default=True),
            pystray.MenuItem("Restart Pipeline", on_restart),
            pystray.MenuItem("Open Logs Folder", on_open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ),
    )

    tray_thread = threading.Thread(target=tray.run, daemon=True)
    tray_thread.start()

    try:
        webview.start()
    finally:
        shutting_down.set()
        manager.stop_all()
        tray.stop()


if __name__ == "__main__":
    main()