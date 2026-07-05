from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

from .models import Streamer


class Notifier:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

    def notify(self, streamer: Streamer, sound_enabled: bool = True) -> None:
        if sound_enabled:
            self._play_sound()
        self._show_toast(streamer, f"{streamer.nickname} \u5f00\u64ad\u4e86")

    def notify_title_changed(self, streamer: Streamer, old_title: str = "", sound_enabled: bool = True) -> None:
        if sound_enabled:
            self._play_sound()
        title = f"{streamer.nickname} \u6807\u9898\u66f4\u65b0"
        detail = streamer.live_title or old_title or streamer.platform
        self._show_toast(streamer, title, detail)

    def _play_sound(self) -> None:
        if sys.platform.startswith("win"):
            try:
                import winsound

                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                return
            except RuntimeError:
                pass
        self.root.bell()

    def _show_toast(self, streamer: Streamer, title: str, detail: str | None = None) -> None:
        toast = tk.Toplevel(self.root)
        toast.title("\u5f00\u64ad\u63d0\u9192")
        toast.attributes("-topmost", True)
        toast.resizable(False, False)
        toast.configure(background="#f7f7f5")

        frame = ttk.Frame(toast, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text=title, font=("", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        detail = detail or streamer.live_title or streamer.platform
        ttk.Label(frame, text=detail, foreground="#555555").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 10))

        open_button = ttk.Button(frame, text="\u6253\u5f00\u76f4\u64ad\u95f4", command=lambda: webbrowser.open(streamer.room_url))
        open_button.grid(row=2, column=0, sticky="w")

        close_button = ttk.Button(frame, text="\u5173\u95ed", command=toast.destroy)
        close_button.grid(row=2, column=1, sticky="e", padx=(8, 0))

        toast.update_idletasks()
        width = toast.winfo_width()
        height = toast.winfo_height()
        screen_width = toast.winfo_screenwidth()
        screen_height = toast.winfo_screenheight()
        x = max(0, screen_width - width - 24)
        y = max(0, screen_height - height - 72)
        toast.geometry(f"+{x}+{y}")

        timer = threading.Timer(8, lambda: self.root.after(0, self._safe_destroy, toast))
        timer.daemon = True
        timer.start()

    @staticmethod
    def _safe_destroy(window: tk.Toplevel) -> None:
        try:
            window.destroy()
        except tk.TclError:
            pass
