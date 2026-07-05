from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from .adapters import create_default_registry
from .monitor import MonitorService
from .storage import JsonStore
from .ui import LiveMonitorApp


def main() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    store = JsonStore(root_dir / "data" / "app_state.json")
    registry = create_default_registry()
    monitor = MonitorService(store, registry)

    root = tk.Tk()
    try:
        LiveMonitorApp(root, store, registry, monitor)
        monitor.start()
        root.mainloop()
    except Exception as exc:
        messagebox.showerror("\u542f\u52a8\u5931\u8d25", str(exc))
        monitor.stop()
        raise
