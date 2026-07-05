from __future__ import annotations

from datetime import datetime
from pathlib import Path
from queue import Empty
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from .adapters import AdapterRegistry
from .models import (
    AppSettings,
    DanmakuMessage,
    STATUS_ERROR,
    STATUS_LABELS,
    STATUS_LIVE,
    STATUS_OFFLINE,
    STATUS_UNKNOWN,
    ReminderRecord,
    Streamer,
)
from .monitor import MonitorEvent, MonitorService
from .notifier import Notifier
from .storage import JsonStore


APP_TITLE = "\u4e3b\u64ad\u5f00\u64ad\u76d1\u6d4b\u63d0\u9192"
PLATFORM_ALL = "\u5168\u90e8\u5e73\u53f0"
GROUP_ALL = "\u5168\u90e8\u5206\u7ec4"
GROUP_UNGROUPED = "\u672a\u5206\u7ec4"

PLATFORM_HINTS = {
    "Mock": "\u793a\u4f8b\uff1amock://live\u3001mock://offline\u3001mock://toggle?period=60",
    "Generic HTTP": "\u586b\u5199\u8fd4\u56de JSON \u6216\u6587\u672c\u72b6\u6001\u7684 HTTP/HTTPS \u63a5\u53e3\u5730\u5740",
    "Bilibili": "\u53ef\u76f4\u63a5\u586b\u623f\u95f4\u53f7\uff0c\u4f8b\u5982 123456\uff1b\u4e5f\u53ef\u586b https://live.bilibili.com/123456",
    "\u6296\u97f3": "\u53ef\u5148\u4fdd\u5b58\u623f\u95f4\u53f7\u6216\u76f4\u64ad\u95f4\u94fe\u63a5\uff0c\u771f\u5b9e\u68c0\u6d4b\u5f85\u63a5\u5165\u5408\u89c4\u63a5\u53e3",
    "\u5feb\u624b": "\u53ef\u5148\u4fdd\u5b58\u623f\u95f4\u53f7\u6216\u76f4\u64ad\u95f4\u94fe\u63a5\uff0c\u771f\u5b9e\u68c0\u6d4b\u5f85\u63a5\u5165\u5408\u89c4\u63a5\u53e3",
    "\u6597\u9c7c": "\u53ef\u586b\u623f\u95f4\u53f7\u6216\u76f4\u64ad\u95f4\u94fe\u63a5\uff0c\u6253\u5f00\u65f6\u4f1a\u5c1d\u8bd5\u62fc\u63a5\u5e73\u53f0\u94fe\u63a5",
    "\u864e\u7259": "\u53ef\u586b\u623f\u95f4\u53f7\u6216\u76f4\u64ad\u95f4\u94fe\u63a5\uff0c\u4f1a\u5c1d\u8bd5\u8bc6\u522b\u516c\u5f00\u9875\u9762\u72b6\u6001",
    "Twitch": "\u586b\u9891\u9053\u540d\u6216\u94fe\u63a5\uff1b\u53ef\u5728\u201c\u5e73\u53f0\u914d\u7f6e\u201d\u586b client_id/app_token",
    "YouTube": "\u586b\u89c6\u9891\u94fe\u63a5\u6216\u5907\u6ce8 channel_id=...\uff1b\u53ef\u5728\u201c\u5e73\u53f0\u914d\u7f6e\u201d\u586b api_key",
}

DEFAULT_PLATFORM_HINT = "\u586b\u5199\u76f4\u64ad\u95f4\u5730\u5740\u6216\u623f\u95f4\u53f7"


class LiveMonitorApp:
    def __init__(self, root: tk.Tk, store: JsonStore, registry: AdapterRegistry, monitor: MonitorService) -> None:
        self.root = root
        self.store = store
        self.registry = registry
        self.monitor = monitor
        self.notifier = Notifier(root)
        self.selected_streamer_id: str | None = None
        self.history_window: tk.Toplevel | None = None
        self.history_tree: ttk.Treeview | None = None
        self.status_log_window: tk.Toplevel | None = None
        self.status_log_tree: ttk.Treeview | None = None
        self.platform_config_window: tk.Toplevel | None = None
        self.platform_config_vars: dict[tuple[str, str], tk.StringVar] = {}
        self.danmaku_window: tk.Toplevel | None = None
        self.danmaku_tree: ttk.Treeview | None = None
        self.danmaku_streamer_id: str | None = None
        self.danmaku_seen_ids: set[str] = set()
        self.danmaku_last_message_id = ""
        self.danmaku_cursor = ""
        self.danmaku_after_id: str | None = None

        self.nickname_var = tk.StringVar()
        self.platform_var = tk.StringVar(value=self.registry.names()[0])
        self.platform_filter_var = tk.StringVar(value=PLATFORM_ALL)
        self.group_filter_var = tk.StringVar(value=GROUP_ALL)
        self.favorite_filter_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        self.room_url_var = tk.StringVar()
        self.group_var = tk.StringVar()
        self.favorite_var = tk.BooleanVar(value=False)
        self.custom_interval_var = tk.IntVar(value=0)
        self.enabled_var = tk.BooleanVar(value=True)
        self.remind_var = tk.BooleanVar(value=True)
        self.interval_var = tk.IntVar(value=self.store.get_settings().check_interval_seconds)
        self.notifications_var = tk.BooleanVar(value=self.store.get_settings().notifications_enabled)
        self.sound_var = tk.BooleanVar(value=self.store.get_settings().sound_enabled)
        self.backoff_var = tk.BooleanVar(value=self.store.get_settings().retry_backoff_enabled)
        self.title_change_var = tk.BooleanVar(value=self.store.get_settings().title_change_notifications_enabled)
        self.status_var = tk.StringVar(value="\u51c6\u5907\u5c31\u7eea")
        self.platform_hint_var = tk.StringVar()
        self.selection_var = tk.StringVar(value="\u672a\u9009\u62e9\u4e3b\u64ad")
        self.filter_count_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="\u9009\u4e2d\u4e3b\u64ad\u540e\u663e\u793a\u68c0\u6d4b\u8be6\u60c5")
        self.danmaku_status_var = tk.StringVar(value="\u9009\u4e2d\u4e3b\u64ad\u540e\u53ef\u67e5\u770b\u5f39\u5e55")
        self.danmaku_auto_refresh_var = tk.BooleanVar(value=True)
        self.summary_values: dict[str, tk.StringVar] = {}

        self._build_window()
        self._update_platform_hint()
        self._sync_action_buttons()
        self.refresh_streamer_list()
        self._poll_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("1180x740")
        self.root.minsize(720, 540)

        self._configure_style()

        container = ttk.Frame(self.root, padding=12, style="App.TFrame")
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        self._build_header(container)
        self._build_tabs(container)
        self._build_footer(container)

    def _configure_style(self) -> None:
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.style.configure("App.TFrame", background="#f7f7f5")
        self.style.configure("Title.TLabel", background="#f7f7f5", foreground="#202124", font=("", 16, "bold"))
        self.style.configure("Subtitle.TLabel", background="#f7f7f5", foreground="#5f6368")
        self.style.configure("Muted.TLabel", foreground="#5f6368")
        self.style.configure("Hint.TLabel", foreground="#5f6368", font=("", 9))
        self.style.configure("StatusBar.TLabel", foreground="#3c4043")
        self.style.configure("SummaryName.TLabel", foreground="#5f6368", font=("", 9))
        self.style.configure("SummaryValue.TLabel", foreground="#202124", font=("", 13, "bold"))
        self.style.configure("Empty.TLabel", foreground="#5f6368", font=("", 11))
        self.style.configure("Treeview", rowheight=28)
        self.style.configure("Treeview.Heading", font=("", 9, "bold"))

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_area = ttk.Frame(header, style="App.TFrame")
        title_area.grid(row=0, column=0, sticky="w")
        ttk.Label(title_area, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            title_area,
            text="\u7edf\u4e00\u7ba1\u7406\u4e3b\u64ad\u3001\u5b9a\u65f6\u68c0\u6d4b\u3001\u5f00\u64ad\u5373\u63d0\u9192",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        summary = ttk.Frame(header, style="App.TFrame")
        summary.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        summary_items = [
            ("enabled", "\u76d1\u6d4b\u4e2d"),
            ("live", "\u76f4\u64ad\u4e2d"),
            ("offline", "\u672a\u5f00\u64ad"),
            ("error", "\u5931\u8d25"),
            ("unknown", "\u672a\u77e5"),
        ]
        for column, (key, label) in enumerate(summary_items):
            block = ttk.Frame(summary, padding=(0, 2, 18, 2), style="App.TFrame")
            block.grid(row=0, column=column, sticky="w")
            value = tk.StringVar(value="0")
            self.summary_values[key] = value
            ttk.Label(block, textvariable=value, style="SummaryValue.TLabel").grid(row=0, column=0)
            ttk.Label(block, text=label, style="SummaryName.TLabel").grid(row=1, column=0)

    def _build_tabs(self, parent: ttk.Frame) -> None:
        tabs = ttk.Notebook(parent)
        tabs.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        streamer_tab = ttk.Frame(tabs, padding=(0, 8, 0, 0))
        monitor_tab = ttk.Frame(tabs, padding=(0, 8, 0, 0))
        settings_tab = ttk.Frame(tabs, padding=(0, 8, 0, 0))

        for tab in (streamer_tab, monitor_tab, settings_tab):
            tab.columnconfigure(0, weight=1)
        monitor_tab.rowconfigure(0, weight=1)

        tabs.add(streamer_tab, text="\u4e3b\u64ad\u4fe1\u606f")
        tabs.add(monitor_tab, text="\u76d1\u6d4b\u5217\u8868")
        tabs.add(settings_tab, text="\u8fd0\u884c\u8bbe\u7f6e")

        self._build_form(streamer_tab)
        self._build_table(monitor_tab)
        self._build_settings(settings_tab)

    def _build_form(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="\u4e3b\u64ad\u4fe1\u606f", padding=10)
        form.grid(row=0, column=0, sticky="new")
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="\u4e3b\u64ad\u540d\u79f0").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.nickname_var).grid(row=0, column=1, sticky="ew", padx=(8, 14))

        ttk.Label(form, text="\u5e73\u53f0").grid(row=0, column=2, sticky="w")
        self.platform_box = ttk.Combobox(
            form,
            textvariable=self.platform_var,
            values=self.registry.names(),
            state="readonly",
            width=18,
        )
        self.platform_box.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        self.platform_box.bind("<<ComboboxSelected>>", lambda _event: self._update_platform_hint())

        ttk.Label(form, text="\u76f4\u64ad\u95f4\u5730\u5740 / \u623f\u95f4\u53f7").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.room_url_var).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Label(form, textvariable=self.platform_hint_var, style="Hint.TLabel", wraplength=620).grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="w",
            padx=(8, 0),
            pady=(3, 0),
        )

        ttk.Label(form, text="\u5206\u7ec4").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.group_var).grid(row=3, column=1, sticky="ew", padx=(8, 14), pady=(8, 0))
        ttk.Checkbutton(form, text="\u6536\u85cf", variable=self.favorite_var).grid(
            row=3,
            column=2,
            columnspan=2,
            sticky="w",
            padx=(8, 14),
            pady=(8, 0),
        )

        ttk.Label(form, text="\u5907\u6ce8").grid(row=4, column=0, sticky="nw", pady=(8, 0))
        self.remark_text = tk.Text(form, height=3, wrap="word", relief="solid", bd=1)
        self.remark_text.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=(8, 0))

        options = ttk.Frame(form)
        options.grid(row=5, column=1, columnspan=3, sticky="ew", pady=(8, 0), padx=(8, 0))
        ttk.Checkbutton(options, text="\u542f\u7528\u68c0\u6d4b", variable=self.enabled_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="\u542f\u7528\u63d0\u9192", variable=self.remind_var).grid(row=0, column=1, sticky="w", padx=(18, 0))
        ttk.Label(options, text="\u5355\u72ec\u95f4\u9694").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(options, from_=0, to=3600, increment=10, textvariable=self.custom_interval_var, width=8).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 0),
            pady=(8, 0),
        )
        ttk.Label(options, text="\u79d2\uff080=\u5168\u5c40\uff09", style="Muted.TLabel").grid(row=1, column=2, sticky="w", padx=(4, 0), pady=(8, 0))

        detail = ttk.Frame(form)
        detail.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        detail.columnconfigure(1, weight=1)
        ttk.Label(detail, text="\u68c0\u6d4b\u8be6\u60c5", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(detail, textvariable=self.detail_var, style="Muted.TLabel", wraplength=640).grid(row=0, column=1, sticky="w", padx=(8, 0))

        actions = ttk.Frame(form)
        actions.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        for column in range(4):
            actions.columnconfigure(column, weight=1)
        self.save_button = ttk.Button(actions, text="\u4fdd\u5b58\u4e3b\u64ad", command=self._save_streamer)
        self.save_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="\u65b0\u5efa", command=self._clear_form).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.delete_button = ttk.Button(actions, text="\u5220\u9664", command=self._delete_selected)
        self.delete_button.grid(row=0, column=2, sticky="ew", padx=(0, 6))
        self.open_button = ttk.Button(actions, text="\u6253\u5f00\u76f4\u64ad\u95f4", command=self._open_selected_room)
        self.open_button.grid(row=0, column=3, sticky="ew")

    def _build_table(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="\u76d1\u6d4b\u5217\u8868", padding=10)
        section.grid(row=0, column=0, sticky="nsew")
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(section)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(
            toolbar,
            textvariable=self.selection_var,
            style="Muted.TLabel",
            wraplength=640,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            toolbar,
            text="\u53cc\u51fb\u884c\u53ef\u6253\u5f00\u76f4\u64ad\u95f4",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        filter_area = ttk.Frame(toolbar)
        filter_area.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        filter_area.columnconfigure(1, weight=1)
        ttk.Label(filter_area, text="\u641c\u7d22", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        search_entry = ttk.Entry(filter_area, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_streamer_list())

        ttk.Label(filter_area, text="\u5e73\u53f0", style="Muted.TLabel").grid(row=0, column=2, sticky="e")
        self.platform_filter_box = ttk.Combobox(
            filter_area,
            textvariable=self.platform_filter_var,
            values=[PLATFORM_ALL, *self.registry.names()],
            state="readonly",
            width=14,
        )
        self.platform_filter_box.grid(row=0, column=3, sticky="e", padx=(6, 10))
        self.platform_filter_box.bind("<<ComboboxSelected>>", self._on_platform_filter_change)

        ttk.Label(filter_area, text="\u5206\u7ec4", style="Muted.TLabel").grid(row=0, column=4, sticky="e")
        self.group_filter_box = ttk.Combobox(
            filter_area,
            textvariable=self.group_filter_var,
            values=[GROUP_ALL, GROUP_UNGROUPED],
            state="readonly",
            width=12,
        )
        self.group_filter_box.grid(row=0, column=5, sticky="e", padx=(6, 10))
        self.group_filter_box.bind("<<ComboboxSelected>>", self._on_table_filter_change)

        ttk.Checkbutton(
            filter_area,
            text="\u53ea\u770b\u6536\u85cf",
            variable=self.favorite_filter_var,
            command=self._on_table_filter_change,
        ).grid(row=0, column=6, sticky="e", padx=(0, 10))

        ttk.Label(filter_area, textvariable=self.filter_count_var, style="Muted.TLabel").grid(
            row=0,
            column=7,
            sticky="e",
        )

        table_area = ttk.Frame(section)
        table_area.grid(row=1, column=0, sticky="nsew")
        table_area.columnconfigure(0, weight=1)
        table_area.rowconfigure(0, weight=1)

        columns = (
            "status",
            "favorite",
            "streamer_name",
            "platform",
            "group",
            "live_title",
            "enabled",
            "remind",
            "last_checked",
            "room_url",
        )
        self.tree = ttk.Treeview(table_area, columns=columns, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        headings = {
            "status": "\u72b6\u6001",
            "favorite": "\u6536\u85cf",
            "streamer_name": "\u4e3b\u64ad\u540d\u79f0",
            "platform": "\u5e73\u53f0",
            "group": "\u5206\u7ec4",
            "live_title": "\u5f00\u64ad\u6807\u9898",
            "enabled": "\u68c0\u6d4b",
            "remind": "\u63d0\u9192",
            "last_checked": "\u6700\u540e\u68c0\u6d4b",
            "room_url": "\u76f4\u64ad\u95f4\u5730\u5740 / \u623f\u95f4\u53f7",
        }
        widths = {
            "status": 100,
            "favorite": 58,
            "streamer_name": 180,
            "platform": 120,
            "group": 100,
            "live_title": 240,
            "enabled": 76,
            "remind": 76,
            "last_checked": 170,
            "room_url": 300,
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], minwidth=64, anchor="w")

        self.tree.tag_configure("live", foreground="#0f7b45")
        self.tree.tag_configure("error", foreground="#b42318")
        self.tree.tag_configure("offline", foreground="#5f6368")
        self.tree.tag_configure("unknown", foreground="#6f6f6f")
        self.tree.tag_configure("disabled", foreground="#8a8a8a")

        scrollbar = ttk.Scrollbar(table_area, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar = ttk.Scrollbar(table_area, orient="horizontal", command=self.tree.xview)
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=x_scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda _event: self._open_selected_room())

        self.empty_label = ttk.Label(
            table_area,
            text="\u8fd8\u6ca1\u6709\u4e3b\u64ad\uff0c\u53ef\u70b9\u51fb\u201c\u6dfb\u52a0\u793a\u4f8b\u201d\u6216\u5728\u4e0a\u65b9\u4fdd\u5b58\u4e00\u4e2a\u4e3b\u64ad",
            style="Empty.TLabel",
            anchor="center",
        )

    def _build_settings(self, parent: ttk.Frame) -> None:
        settings = ttk.LabelFrame(parent, text="\u8fd0\u884c\u8bbe\u7f6e", padding=10)
        settings.grid(row=0, column=0, sticky="new")
        settings.columnconfigure(7, weight=1)

        ttk.Label(settings, text="\u68c0\u6d4b\u95f4\u9694").grid(row=0, column=0, sticky="w")
        interval = ttk.Spinbox(settings, from_=10, to=3600, increment=10, textvariable=self.interval_var, width=8)
        interval.grid(row=0, column=1, sticky="w", padx=(8, 4))
        ttk.Label(settings, text="\u79d2", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 18))

        ttk.Checkbutton(settings, text="\u901a\u77e5", variable=self.notifications_var).grid(row=0, column=3, sticky="w")
        ttk.Checkbutton(settings, text="\u58f0\u97f3", variable=self.sound_var).grid(row=0, column=4, sticky="w", padx=(12, 18))
        ttk.Checkbutton(settings, text="\u5931\u8d25\u9000\u907f", variable=self.backoff_var).grid(row=0, column=5, sticky="w", padx=(0, 18))
        ttk.Checkbutton(settings, text="\u6807\u9898\u53d8\u5316\u63d0\u9192", variable=self.title_change_var).grid(
            row=0,
            column=6,
            sticky="w",
            padx=(0, 18),
        )

        actions = ttk.Frame(settings)
        actions.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(10, 0))
        for column in range(4):
            actions.columnconfigure(column, weight=1)

        ttk.Button(actions, text="\u4fdd\u5b58\u8bbe\u7f6e", command=self._save_settings).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.check_selected_button = ttk.Button(actions, text="\u68c0\u6d4b\u9009\u4e2d", command=self._check_selected)
        self.check_selected_button.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="\u7acb\u5373\u68c0\u6d4b", command=self._manual_check).grid(row=0, column=2, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="\u63d0\u9192\u5386\u53f2", command=self._open_history_window).grid(row=0, column=3, sticky="ew")
        ttk.Button(actions, text="\u72b6\u6001\u65e5\u5fd7", command=self._open_status_log_window).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(6, 0))
        ttk.Button(actions, text="\u5e73\u53f0\u914d\u7f6e", command=self._open_platform_config_window).grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(6, 0))
        self.danmaku_button = ttk.Button(actions, text="\u5f39\u5e55", command=self._open_danmaku_window)
        self.danmaku_button.grid(row=1, column=2, sticky="ew", padx=(0, 6), pady=(6, 0))
        ttk.Button(actions, text="\u6dfb\u52a0\u793a\u4f8b", command=self._add_example).grid(row=1, column=3, sticky="ew", pady=(6, 0))

    def _build_footer(self, parent: ttk.Frame) -> None:
        footer = ttk.Frame(parent, style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="StatusBar.TLabel", wraplength=640).grid(row=0, column=0, sticky="w")
        data_path = Path(self.store.path).resolve()
        try:
            data_path_text = str(data_path.relative_to(Path.cwd()))
        except ValueError:
            data_path_text = data_path.name
        ttk.Label(
            footer,
            text=f"\u6570\u636e\u6587\u4ef6\uff1a{data_path_text}",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def refresh_streamer_list(self) -> None:
        selected = self.selected_streamer_id
        for item in self.tree.get_children():
            self.tree.delete(item)

        all_streamers = self.store.list_streamers()
        self._refresh_group_filter_options(all_streamers)
        streamers = self._sort_streamers(self._filter_streamers(all_streamers))
        for streamer in streamers:
            self.tree.insert(
                "",
                "end",
                iid=streamer.id,
                values=(
                    STATUS_LABELS.get(streamer.status, streamer.status),
                    "\u2605" if streamer.favorite else "",
                    streamer.nickname,
                    streamer.platform,
                    streamer.group or GROUP_UNGROUPED,
                    streamer.live_title,
                    "\u542f\u7528" if streamer.enabled else "\u505c\u7528",
                    "\u542f\u7528" if streamer.remind_enabled else "\u505c\u7528",
                    self._format_time(streamer.last_checked_at),
                    streamer.room_url,
                ),
                tags=self._row_tags(streamer),
            )

        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
            self._update_detail_panel(self._find_streamer(selected))
        else:
            if selected:
                self.selected_streamer_id = None
            self.selection_var.set("\u672a\u9009\u62e9\u4e3b\u64ad")
            self._update_detail_panel(None)

        self._toggle_empty_state(not streamers)
        self._update_summary(streamers)
        self._update_filter_count(len(all_streamers), len(streamers))
        self._sync_action_buttons()

    def _update_summary(self, streamers: list[Streamer]) -> None:
        values = {
            "enabled": sum(1 for item in streamers if item.enabled),
            "live": sum(1 for item in streamers if item.status == STATUS_LIVE),
            "offline": sum(1 for item in streamers if item.status == STATUS_OFFLINE),
            "error": sum(1 for item in streamers if item.status == STATUS_ERROR),
            "unknown": sum(1 for item in streamers if item.status == STATUS_UNKNOWN),
        }
        for key, value in values.items():
            self.summary_values[key].set(str(value))

    def _save_streamer(self) -> None:
        nickname = self.nickname_var.get().strip()
        platform = self.platform_var.get().strip()
        room_url = self.room_url_var.get().strip()
        group = self.group_var.get().strip()
        remark = self.remark_text.get("1.0", "end").strip()
        custom_interval = self._read_custom_interval()

        if not nickname:
            messagebox.showwarning("\u7f3a\u5c11\u4e3b\u64ad\u540d\u79f0", "\u8bf7\u586b\u5199\u4e3b\u64ad\u540d\u79f0")
            return
        if not room_url:
            messagebox.showwarning(
                "\u7f3a\u5c11\u76f4\u64ad\u95f4\u5730\u5740 / \u623f\u95f4\u53f7",
                "\u8bf7\u586b\u5199\u76f4\u64ad\u95f4\u5730\u5740\u6216\u623f\u95f4\u53f7",
            )
            return

        if self.selected_streamer_id:
            streamer = self._find_streamer(self.selected_streamer_id)
            if streamer is None:
                messagebox.showerror("\u4fdd\u5b58\u5931\u8d25", "\u672a\u627e\u5230\u9009\u4e2d\u7684\u4e3b\u64ad")
                return
            streamer.nickname = nickname
            streamer.platform = platform
            streamer.room_url = room_url
            streamer.group = group
            streamer.favorite = self.favorite_var.get()
            streamer.remark = remark
            streamer.enabled = self.enabled_var.get()
            streamer.remind_enabled = self.remind_var.get()
            streamer.custom_interval_seconds = custom_interval
            self.store.update_streamer(streamer)
            self.status_var.set(f"\u5df2\u66f4\u65b0\uff1a{nickname}")
        else:
            streamer = Streamer(
                nickname=nickname,
                platform=platform,
                room_url=room_url,
                group=group,
                favorite=self.favorite_var.get(),
                remark=remark,
                enabled=self.enabled_var.get(),
                remind_enabled=self.remind_var.get(),
                custom_interval_seconds=custom_interval,
            )
            self.store.add_streamer(streamer)
            self.selected_streamer_id = streamer.id
            self.status_var.set(f"\u5df2\u6dfb\u52a0\uff1a{nickname}")

        self.refresh_streamer_list()

    def _delete_selected(self) -> None:
        if not self.selected_streamer_id:
            messagebox.showinfo("\u672a\u9009\u62e9\u4e3b\u64ad", "\u8bf7\u5148\u5728\u5217\u8868\u4e2d\u9009\u62e9\u4e00\u4e2a\u4e3b\u64ad")
            return
        streamer = self._find_streamer(self.selected_streamer_id)
        if streamer is None:
            return
        if not messagebox.askyesno("\u786e\u8ba4\u5220\u9664", f"\u786e\u5b9a\u5220\u9664 {streamer.nickname} \u5417\uff1f"):
            return
        self.store.delete_streamer(streamer.id)
        self._clear_form()
        self.refresh_streamer_list()
        self.status_var.set(f"\u5df2\u5220\u9664\uff1a{streamer.nickname}")

    def _clear_form(self) -> None:
        self.selected_streamer_id = None
        self.nickname_var.set("")
        self.platform_var.set(self.registry.names()[0])
        self.room_url_var.set("")
        self.group_var.set("")
        self.favorite_var.set(False)
        self.custom_interval_var.set(0)
        self.enabled_var.set(True)
        self.remind_var.set(True)
        self.remark_text.delete("1.0", "end")
        self.tree.selection_remove(*self.tree.selection())
        self.selection_var.set("\u672a\u9009\u62e9\u4e3b\u64ad")
        self._update_detail_panel(None)
        self._update_platform_hint()
        self._sync_action_buttons()

    def _on_tree_select(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        streamer_id = selection[0]
        streamer = self._find_streamer(streamer_id)
        if streamer is None:
            return

        self.selected_streamer_id = streamer.id
        self.nickname_var.set(streamer.nickname)
        self.platform_var.set(streamer.platform)
        self.room_url_var.set(streamer.room_url)
        self.group_var.set(streamer.group)
        self.favorite_var.set(streamer.favorite)
        self.custom_interval_var.set(streamer.custom_interval_seconds)
        self.enabled_var.set(streamer.enabled)
        self.remind_var.set(streamer.remind_enabled)
        self.remark_text.delete("1.0", "end")
        self.remark_text.insert("1.0", streamer.remark)
        self._update_platform_hint()

        status = STATUS_LABELS.get(streamer.status, streamer.status)
        error = f"\uff1a{streamer.last_error}" if streamer.last_error else ""
        self.selection_var.set(f"\u5df2\u9009\u62e9\uff1a{streamer.nickname} \u00b7 {streamer.platform} \u00b7 {status}")
        self.status_var.set(f"{streamer.nickname} \u5f53\u524d\u72b6\u6001\uff1a{status}{error}")
        self._update_detail_panel(streamer)
        self._sync_action_buttons()

    def _save_settings(self) -> None:
        try:
            interval = max(10, int(self.interval_var.get()))
        except (TypeError, ValueError, tk.TclError):
            interval = 60
            self.interval_var.set(interval)

        current = self.store.get_settings()
        settings = AppSettings(
            check_interval_seconds=interval,
            notifications_enabled=self.notifications_var.get(),
            sound_enabled=self.sound_var.get(),
            retry_backoff_enabled=self.backoff_var.get(),
            max_backoff_seconds=current.max_backoff_seconds,
            title_change_notifications_enabled=self.title_change_var.get(),
            platform_configs=current.platform_configs,
        )
        self.store.update_settings(settings)
        self.status_var.set("\u8bbe\u7f6e\u5df2\u4fdd\u5b58")

    def _manual_check(self) -> None:
        self._save_settings()
        self.status_var.set("\u6b63\u5728\u68c0\u6d4b...")
        self.monitor.check_once_async()

    def _check_selected(self) -> None:
        if not self.selected_streamer_id:
            messagebox.showinfo("\u672a\u9009\u62e9\u4e3b\u64ad", "\u8bf7\u5148\u5728\u5217\u8868\u4e2d\u9009\u62e9\u4e00\u4e2a\u4e3b\u64ad")
            return
        self._save_settings()
        self.status_var.set("\u6b63\u5728\u68c0\u6d4b\u9009\u4e2d\u4e3b\u64ad...")
        self.monitor.check_streamer_async(self.selected_streamer_id)

    def _add_example(self) -> None:
        example = Streamer(
            nickname="Mock \u5468\u671f\u5f00\u64ad\u793a\u4f8b",
            platform="Mock",
            room_url="mock://toggle?period=60",
            group="\u793a\u4f8b",
            favorite=True,
            remark="\u524d 30 \u79d2\u76f4\u64ad\u4e2d\uff0c\u540e 30 \u79d2\u672a\u5f00\u64ad",
            enabled=True,
            remind_enabled=True,
        )
        self.store.add_streamer(example)
        self.selected_streamer_id = example.id
        self.refresh_streamer_list()
        self.status_var.set("\u5df2\u6dfb\u52a0 Mock \u793a\u4f8b\u4e3b\u64ad")

    def _open_selected_room(self) -> None:
        if not self.selected_streamer_id:
            messagebox.showinfo("\u672a\u9009\u62e9\u4e3b\u64ad", "\u8bf7\u5148\u5728\u5217\u8868\u4e2d\u9009\u62e9\u4e00\u4e2a\u4e3b\u64ad")
            return
        streamer = self._find_streamer(self.selected_streamer_id)
        if not streamer:
            return

        url = self._build_open_url(streamer)
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)
        else:
            messagebox.showinfo(
                "\u65e0\u6cd5\u6253\u5f00",
                "\u5f53\u524d\u5185\u5bb9\u4e0d\u662f\u53ef\u76f4\u63a5\u6253\u5f00\u7684 HTTP/HTTPS \u94fe\u63a5",
            )

    def _build_open_url(self, streamer: Streamer) -> str:
        if streamer.room_url.startswith(("http://", "https://")):
            return streamer.room_url
        adapter = self.registry.get(streamer.platform)
        builder = getattr(adapter, "build_watch_url", None)
        if callable(builder):
            return str(builder(streamer))
        return streamer.room_url

    def _open_danmaku_window(self) -> None:
        if not self.selected_streamer_id:
            messagebox.showinfo("\u672a\u9009\u62e9\u4e3b\u64ad", "\u8bf7\u5148\u5728\u5217\u8868\u4e2d\u9009\u62e9\u4e00\u4e2a\u4e3b\u64ad")
            return
        streamer = self._find_streamer(self.selected_streamer_id)
        if streamer is None:
            return

        if self.danmaku_window and self.danmaku_window.winfo_exists():
            self.danmaku_window.lift()
            self._set_danmaku_streamer(streamer)
            self._request_danmaku_refresh()
            return

        window = tk.Toplevel(self.root)
        window.geometry("760x420")
        window.minsize(540, 300)
        self.danmaku_window = window

        container = ttk.Frame(window, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(container)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, textvariable=self.danmaku_status_var, style="Muted.TLabel", wraplength=500).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            toolbar,
            text="\u81ea\u52a8\u5237\u65b0",
            variable=self.danmaku_auto_refresh_var,
            command=self._on_danmaku_auto_toggle,
        ).grid(row=0, column=1, sticky="e")

        columns = ("sent_at", "author", "content")
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        tree.grid(row=1, column=0, sticky="nsew")
        self.danmaku_tree = tree

        headings = {
            "sent_at": "\u65f6\u95f4",
            "author": "\u7528\u6237",
            "content": "\u5f39\u5e55",
        }
        widths = {
            "sent_at": 170,
            "author": 130,
            "content": 520,
        }
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="w")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        x_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        x_scrollbar.grid(row=2, column=0, sticky="ew")
        tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=x_scrollbar.set)

        actions = ttk.Frame(container)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="\u5237\u65b0", command=self._request_danmaku_refresh).grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="\u6e05\u7a7a", command=self._clear_danmaku_messages).grid(row=0, column=2, sticky="e", padx=(8, 0))
        ttk.Button(actions, text="\u6253\u5f00\u76f4\u64ad\u95f4", command=self._open_danmaku_room).grid(
            row=0,
            column=3,
            sticky="e",
            padx=(8, 0),
        )

        window.protocol("WM_DELETE_WINDOW", self._close_danmaku_window)
        self._set_danmaku_streamer(streamer)
        self._request_danmaku_refresh()
        self._restart_danmaku_schedule()

    def _set_danmaku_streamer(self, streamer: Streamer) -> None:
        if self.danmaku_streamer_id == streamer.id:
            return
        self.danmaku_streamer_id = streamer.id
        self.danmaku_seen_ids.clear()
        self.danmaku_last_message_id = ""
        self.danmaku_cursor = ""
        if self.danmaku_tree:
            for item in self.danmaku_tree.get_children():
                self.danmaku_tree.delete(item)
        if self.danmaku_window and self.danmaku_window.winfo_exists():
            self.danmaku_window.title(f"\u5f39\u5e55 - {streamer.nickname}")
        self.danmaku_status_var.set(f"\u6b63\u5728\u67e5\u770b\uff1a{streamer.nickname} \u00b7 {streamer.platform}")

    def _request_danmaku_refresh(self) -> None:
        if not self.danmaku_window or not self.danmaku_window.winfo_exists():
            return
        if not self.danmaku_streamer_id:
            self.danmaku_status_var.set("\u8bf7\u5148\u9009\u62e9\u4e3b\u64ad")
            return
        streamer = self._find_streamer(self.danmaku_streamer_id)
        if streamer is None:
            self.danmaku_status_var.set("\u672a\u627e\u5230\u5f53\u524d\u5f39\u5e55\u4e3b\u64ad")
            return
        self.danmaku_status_var.set(f"\u6b63\u5728\u83b7\u53d6\u5f39\u5e55\uff1a{streamer.nickname}")
        since_id = self.danmaku_cursor or self.danmaku_last_message_id
        self.monitor.fetch_danmaku_async(streamer.id, since_id)

    def _handle_danmaku_event(self, event: MonitorEvent) -> None:
        if event.kind == "danmaku_busy":
            if self.danmaku_window and self.danmaku_window.winfo_exists():
                self.danmaku_status_var.set(event.message)
            return
        if not self.danmaku_window or not self.danmaku_window.winfo_exists():
            return
        if event.streamer and self.danmaku_streamer_id and event.streamer.id != self.danmaku_streamer_id:
            return

        if event.kind == "danmaku_error":
            self.danmaku_status_var.set(f"\u5f39\u5e55\u83b7\u53d6\u5931\u8d25\uff1a{event.message}")
            return
        if event.kind == "danmaku_unsupported":
            self.danmaku_status_var.set(event.message or "\u5f53\u524d\u5e73\u53f0\u6682\u4e0d\u652f\u6301\u5f39\u5e55")
            return

        added = self._append_danmaku_messages(event.danmaku_messages)
        if event.danmaku_cursor:
            self.danmaku_cursor = event.danmaku_cursor
        if added:
            self.danmaku_status_var.set(f"\u65b0\u589e {added} \u6761\u5f39\u5e55 \u00b7 {datetime.now().strftime('%H:%M:%S')}")
        elif event.message:
            self.danmaku_status_var.set(event.message)
        else:
            self.danmaku_status_var.set(f"\u6682\u65e0\u65b0\u5f39\u5e55 \u00b7 {datetime.now().strftime('%H:%M:%S')}")

    def _append_danmaku_messages(self, messages: list[DanmakuMessage]) -> int:
        if not self.danmaku_tree:
            return 0
        added = 0
        for message in messages:
            message_id = message.message_id or f"{message.sent_at}:{message.author}:{message.content}"
            if message_id in self.danmaku_seen_ids:
                continue
            self.danmaku_seen_ids.add(message_id)
            self.danmaku_last_message_id = message_id
            item_id = f"danmaku-{len(self.danmaku_seen_ids)}"
            self.danmaku_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    self._format_time(message.sent_at),
                    message.author or "\u533f\u540d",
                    message.content,
                ),
            )
            added += 1

        children = self.danmaku_tree.get_children()
        overflow = len(children) - 500
        if overflow > 0:
            for item in children[:overflow]:
                self.danmaku_tree.delete(item)
        children = self.danmaku_tree.get_children()
        if children:
            self.danmaku_tree.see(children[-1])
        if len(self.danmaku_seen_ids) > 2000:
            self.danmaku_seen_ids = set(list(self.danmaku_seen_ids)[-1000:])
        return added

    def _clear_danmaku_messages(self) -> None:
        if self.danmaku_tree:
            for item in self.danmaku_tree.get_children():
                self.danmaku_tree.delete(item)
        self.danmaku_seen_ids.clear()
        self.danmaku_last_message_id = ""
        self.danmaku_cursor = ""
        self.danmaku_status_var.set("\u5f39\u5e55\u5df2\u6e05\u7a7a")

    def _open_danmaku_room(self) -> None:
        if not self.danmaku_streamer_id:
            return
        streamer = self._find_streamer(self.danmaku_streamer_id)
        if not streamer:
            return
        url = self._build_open_url(streamer)
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)

    def _on_danmaku_auto_toggle(self) -> None:
        if self.danmaku_auto_refresh_var.get():
            self._request_danmaku_refresh()
            self._restart_danmaku_schedule()
        else:
            self._cancel_danmaku_schedule()

    def _restart_danmaku_schedule(self) -> None:
        self._cancel_danmaku_schedule()
        if self.danmaku_window and self.danmaku_window.winfo_exists() and self.danmaku_auto_refresh_var.get():
            self.danmaku_after_id = self.root.after(5000, self._danmaku_auto_refresh)

    def _danmaku_auto_refresh(self) -> None:
        self.danmaku_after_id = None
        if not self.danmaku_window or not self.danmaku_window.winfo_exists():
            return
        if self.danmaku_auto_refresh_var.get():
            self._request_danmaku_refresh()
            self._restart_danmaku_schedule()

    def _cancel_danmaku_schedule(self) -> None:
        if not self.danmaku_after_id:
            return
        try:
            self.root.after_cancel(self.danmaku_after_id)
        except tk.TclError:
            pass
        self.danmaku_after_id = None

    def _close_danmaku_window(self) -> None:
        self._cancel_danmaku_schedule()
        if self.danmaku_window:
            self.danmaku_window.destroy()
        self.danmaku_window = None
        self.danmaku_tree = None
        self.danmaku_streamer_id = None
        self.danmaku_seen_ids.clear()
        self.danmaku_last_message_id = ""
        self.danmaku_cursor = ""

    def _open_history_window(self) -> None:
        if self.history_window and self.history_window.winfo_exists():
            self.history_window.lift()
            self._refresh_history_window()
            return

        window = tk.Toplevel(self.root)
        window.title("\u63d0\u9192\u5386\u53f2")
        window.geometry("760x400")
        window.minsize(540, 300)
        self.history_window = window

        container = ttk.Frame(window, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("notified_at", "nickname", "platform", "title", "room_url")
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        tree.grid(row=0, column=0, sticky="nsew")
        self.history_tree = tree

        headings = {
            "notified_at": "\u63d0\u9192\u65f6\u95f4",
            "nickname": "\u4e3b\u64ad\u540d\u79f0",
            "platform": "\u5e73\u53f0",
            "title": "\u6807\u9898",
            "room_url": "\u76f4\u64ad\u95f4",
        }
        widths = {
            "notified_at": 170,
            "nickname": 130,
            "platform": 90,
            "title": 250,
            "room_url": 260,
        }
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="w")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=x_scrollbar.set)
        tree.bind("<Double-1>", lambda _event: self._open_history_selected())

        actions = ttk.Frame(container)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="\u6253\u5f00\u76f4\u64ad\u95f4", command=self._open_history_selected).grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="\u6e05\u7a7a\u5386\u53f2", command=self._clear_history).grid(row=0, column=2, sticky="e", padx=(8, 0))

        window.protocol("WM_DELETE_WINDOW", self._close_history_window)
        self._refresh_history_window()

    def _refresh_history_window(self) -> None:
        if not self.history_tree:
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        records = list(reversed(self.store.list_history(limit=200)))
        for record in records:
            self.history_tree.insert(
                "",
                "end",
                iid=record.id,
                values=(
                    self._format_time(record.notified_at),
                    record.nickname,
                    record.platform,
                    record.title,
                    record.room_url,
                ),
            )

    def _open_history_selected(self) -> None:
        if not self.history_tree:
            return
        selection = self.history_tree.selection()
        if not selection:
            return
        record_id = selection[0]
        record = next((item for item in self.store.list_history(limit=500) if item.id == record_id), None)
        if record is None:
            return
        streamer = Streamer(
            id=record.streamer_id,
            nickname=record.nickname,
            platform=record.platform,
            room_url=record.room_url,
        )
        url = self._build_open_url(streamer)
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)

    def _clear_history(self) -> None:
        if not messagebox.askyesno("\u786e\u8ba4\u6e05\u7a7a", "\u786e\u5b9a\u6e05\u7a7a\u6240\u6709\u63d0\u9192\u5386\u53f2\u5417\uff1f"):
            return
        self.store.clear_history()
        self._refresh_history_window()
        self.status_var.set("\u63d0\u9192\u5386\u53f2\u5df2\u6e05\u7a7a")

    def _close_history_window(self) -> None:
        if self.history_window:
            self.history_window.destroy()
        self.history_window = None
        self.history_tree = None

    def _open_status_log_window(self) -> None:
        if self.status_log_window and self.status_log_window.winfo_exists():
            self.status_log_window.lift()
            self._refresh_status_log_window()
            return

        window = tk.Toplevel(self.root)
        window.title("\u72b6\u6001\u65e5\u5fd7")
        window.geometry("820x420")
        window.minsize(560, 320)
        self.status_log_window = window

        container = ttk.Frame(window, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("logged_at", "nickname", "platform", "event", "old_status", "new_status", "old_title", "new_title", "room_url")
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        tree.grid(row=0, column=0, sticky="nsew")
        self.status_log_tree = tree

        headings = {
            "logged_at": "\u65f6\u95f4",
            "nickname": "\u4e3b\u64ad\u540d\u79f0",
            "platform": "\u5e73\u53f0",
            "event": "\u4e8b\u4ef6",
            "old_status": "\u539f\u72b6\u6001",
            "new_status": "\u65b0\u72b6\u6001",
            "old_title": "\u539f\u6807\u9898",
            "new_title": "\u65b0\u6807\u9898",
            "room_url": "\u76f4\u64ad\u95f4",
        }
        widths = {
            "logged_at": 170,
            "nickname": 130,
            "platform": 90,
            "event": 110,
            "old_status": 90,
            "new_status": 90,
            "old_title": 220,
            "new_title": 220,
            "room_url": 260,
        }
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="w")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=x_scrollbar.set)
        tree.bind("<Double-1>", lambda _event: self._open_status_log_selected())

        actions = ttk.Frame(container)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="\u5237\u65b0", command=self._refresh_status_log_window).grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="\u6253\u5f00\u76f4\u64ad\u95f4", command=self._open_status_log_selected).grid(row=0, column=2, sticky="e", padx=(8, 0))
        ttk.Button(actions, text="\u6e05\u7a7a\u65e5\u5fd7", command=self._clear_status_logs).grid(row=0, column=3, sticky="e", padx=(8, 0))

        window.protocol("WM_DELETE_WINDOW", self._close_status_log_window)
        self._refresh_status_log_window()

    def _refresh_status_log_window(self) -> None:
        if not self.status_log_tree:
            return
        for item in self.status_log_tree.get_children():
            self.status_log_tree.delete(item)
        records = list(reversed(self.store.list_status_logs(limit=300)))
        for record in records:
            self.status_log_tree.insert(
                "",
                "end",
                iid=record.id,
                values=(
                    self._format_time(record.logged_at),
                    record.nickname,
                    record.platform,
                    self._event_label(record.event_type, record.message),
                    STATUS_LABELS.get(record.old_status, record.old_status),
                    STATUS_LABELS.get(record.new_status, record.new_status),
                    record.old_title,
                    record.new_title,
                    record.room_url,
                ),
            )

    def _open_status_log_selected(self) -> None:
        if not self.status_log_tree:
            return
        selection = self.status_log_tree.selection()
        if not selection:
            return
        record_id = selection[0]
        record = next((item for item in self.store.list_status_logs(limit=1000) if item.id == record_id), None)
        if record is None:
            return
        streamer = Streamer(
            id=record.streamer_id,
            nickname=record.nickname,
            platform=record.platform,
            room_url=record.room_url,
        )
        url = self._build_open_url(streamer)
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)

    def _clear_status_logs(self) -> None:
        if not messagebox.askyesno("\u786e\u8ba4\u6e05\u7a7a", "\u786e\u5b9a\u6e05\u7a7a\u6240\u6709\u72b6\u6001\u65e5\u5fd7\u5417\uff1f"):
            return
        self.store.clear_status_logs()
        self._refresh_status_log_window()
        self.status_var.set("\u72b6\u6001\u65e5\u5fd7\u5df2\u6e05\u7a7a")

    def _close_status_log_window(self) -> None:
        if self.status_log_window:
            self.status_log_window.destroy()
        self.status_log_window = None
        self.status_log_tree = None

    def _open_platform_config_window(self) -> None:
        if self.platform_config_window and self.platform_config_window.winfo_exists():
            self.platform_config_window.lift()
            return

        window = tk.Toplevel(self.root)
        window.title("\u5e73\u53f0\u914d\u7f6e")
        window.geometry("600x340")
        window.minsize(500, 300)
        self.platform_config_window = window
        self.platform_config_vars = {}

        container = ttk.Frame(window, padding=12)
        container.grid(row=0, column=0, sticky="nsew")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        container.columnconfigure(2, weight=1)

        ttk.Label(container, text="\u5e73\u53f0", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(container, text="\u914d\u7f6e\u9879", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Label(container, text="\u503c", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(12, 0))

        settings = self.store.get_settings()
        fields = self._platform_config_fields()
        for row, (platform, key, label, secret) in enumerate(fields, start=1):
            value = settings.platform_configs.get(platform, {}).get(key, "")
            var = tk.StringVar(value=value)
            self.platform_config_vars[(platform, key)] = var
            ttk.Label(container, text=platform).grid(row=row, column=0, sticky="w", pady=(8, 0))
            ttk.Label(container, text=label).grid(row=row, column=1, sticky="w", padx=(12, 0), pady=(8, 0))
            entry = ttk.Entry(container, textvariable=var, show="*" if secret else "")
            entry.grid(row=row, column=2, sticky="ew", padx=(12, 0), pady=(8, 0))

        actions = ttk.Frame(container)
        actions.grid(row=len(fields) + 1, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="\u6e05\u7a7a\u914d\u7f6e", command=self._clear_platform_config).grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="\u4fdd\u5b58\u914d\u7f6e", command=self._save_platform_config).grid(row=0, column=2, sticky="e", padx=(8, 0))

        window.protocol("WM_DELETE_WINDOW", self._close_platform_config_window)

    def _save_platform_config(self) -> None:
        current = self.store.get_settings()
        configs = {platform: dict(values) for platform, values in current.platform_configs.items()}

        for platform, key, _label, _secret in self._platform_config_fields():
            var = self.platform_config_vars.get((platform, key))
            if var is None:
                continue
            value = var.get().strip()
            if value:
                configs.setdefault(platform, {})[key] = value
            elif platform in configs and key in configs[platform]:
                del configs[platform][key]

        configs = {platform: values for platform, values in configs.items() if values}
        settings = AppSettings(
            check_interval_seconds=current.check_interval_seconds,
            notifications_enabled=current.notifications_enabled,
            sound_enabled=current.sound_enabled,
            retry_backoff_enabled=current.retry_backoff_enabled,
            max_backoff_seconds=current.max_backoff_seconds,
            title_change_notifications_enabled=current.title_change_notifications_enabled,
            platform_configs=configs,
        )
        self.store.update_settings(settings)
        self.status_var.set("\u5e73\u53f0\u914d\u7f6e\u5df2\u4fdd\u5b58")

    def _clear_platform_config(self) -> None:
        if not messagebox.askyesno("\u786e\u8ba4\u6e05\u7a7a", "\u786e\u5b9a\u6e05\u7a7a Twitch \u548c YouTube \u7684\u5e73\u53f0\u914d\u7f6e\u5417\uff1f"):
            return
        for var in self.platform_config_vars.values():
            var.set("")
        self._save_platform_config()

    def _close_platform_config_window(self) -> None:
        if self.platform_config_window:
            self.platform_config_window.destroy()
        self.platform_config_window = None
        self.platform_config_vars = {}

    @staticmethod
    def _platform_config_fields() -> tuple[tuple[str, str, str, bool], ...]:
        return (
            ("Twitch", "client_id", "Client ID", False),
            ("Twitch", "app_token", "App Token", True),
            ("Twitch", "chat_nick", "Chat Nick", False),
            ("Twitch", "chat_oauth", "Chat OAuth", True),
            ("YouTube", "api_key", "API Key", True),
        )

    def _read_custom_interval(self) -> int:
        try:
            value = max(0, int(self.custom_interval_var.get()))
        except (TypeError, ValueError, tk.TclError):
            value = 0
        self.custom_interval_var.set(value)
        return value

    def _update_detail_panel(self, streamer: Streamer | None) -> None:
        if streamer is None:
            self.detail_var.set("\u9009\u4e2d\u4e3b\u64ad\u540e\u663e\u793a\u68c0\u6d4b\u8be6\u60c5")
            return

        parts = [f"\u72b6\u6001\uff1a{STATUS_LABELS.get(streamer.status, streamer.status)}"]
        if streamer.last_checked_at:
            parts.append(f"\u6700\u540e\u68c0\u6d4b\uff1a{self._format_time(streamer.last_checked_at)}")
        parts.append(f"\u8fde\u7eed\u5931\u8d25\uff1a{streamer.consecutive_failures}")
        if streamer.custom_interval_seconds > 0:
            parts.append(f"\u5355\u72ec\u95f4\u9694\uff1a{streamer.custom_interval_seconds}\u79d2")
        else:
            parts.append("\u68c0\u6d4b\u95f4\u9694\uff1a\u5168\u5c40")
        if streamer.next_check_after:
            parts.append(f"\u4e0b\u6b21\u68c0\u6d4b\u4e0d\u65e9\u4e8e\uff1a{self._format_time(streamer.next_check_after)}")
        if streamer.live_session_id:
            session_id = streamer.live_session_id
            if len(session_id) > 32:
                session_id = f"{session_id[:32]}..."
            parts.append(f"\u76f4\u64ad\u573a\u6b21\uff1a{session_id}")
        if streamer.last_error:
            error = streamer.last_error
            if len(error) > 80:
                error = f"{error[:80]}..."
            parts.append(f"\u6700\u8fd1\u9519\u8bef\uff1a{error}")
        elif streamer.live_title:
            title = streamer.live_title
            if len(title) > 80:
                title = f"{title[:80]}..."
            parts.append(f"\u6807\u9898\uff1a{title}")
        self.detail_var.set(" | ".join(parts))

    @staticmethod
    def _event_label(event_type: str, message: str) -> str:
        if message:
            return message
        labels = {
            "status_changed": "\u72b6\u6001\u53d8\u5316",
            "title_changed": "\u6807\u9898\u53d8\u5316",
        }
        return labels.get(event_type, event_type)

    def _find_streamer(self, streamer_id: str) -> Streamer | None:
        for streamer in self.store.list_streamers():
            if streamer.id == streamer_id:
                return streamer
        return None

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.monitor.events.get_nowait()
                self._handle_event(event)
        except Empty:
            pass
        self.root.after(400, self._poll_events)

    def _handle_event(self, event: MonitorEvent) -> None:
        if event.kind.startswith("danmaku_"):
            self._handle_danmaku_event(event)
            return

        if event.kind == "live_started" and event.streamer:
            settings = self.store.get_settings()
            self.store.add_history(
                ReminderRecord(
                    streamer_id=event.streamer.id,
                    nickname=event.streamer.nickname,
                    platform=event.streamer.platform,
                    room_url=event.streamer.room_url,
                    title=event.streamer.live_title,
                    live_session_id=event.streamer.live_session_id,
                )
            )
            self.notifier.notify(event.streamer, sound_enabled=settings.sound_enabled)
            self.status_var.set(f"\u5f00\u64ad\u63d0\u9192\uff1a{event.streamer.nickname}")
            self._refresh_history_window()
            self._refresh_status_log_window()
        elif event.kind == "title_changed" and event.streamer:
            settings = self.store.get_settings()
            self.notifier.notify_title_changed(event.streamer, old_title=event.message, sound_enabled=settings.sound_enabled)
            self.status_var.set(f"\u6807\u9898\u53d8\u5316\uff1a{event.streamer.nickname}")
            self._refresh_status_log_window()
        elif event.kind == "streamer_updated" and event.streamer:
            self.status_var.set(f"\u5df2\u68c0\u6d4b\uff1a{event.streamer.nickname}")
            self._refresh_status_log_window()
        elif event.kind == "check_finished":
            self.status_var.set("\u68c0\u6d4b\u5b8c\u6210")
        elif event.message:
            self.status_var.set(event.message)
        self.refresh_streamer_list()

    def _on_close(self) -> None:
        self._cancel_danmaku_schedule()
        self.monitor.stop()
        self.root.destroy()

    def _update_platform_hint(self) -> None:
        self.platform_hint_var.set(PLATFORM_HINTS.get(self.platform_var.get(), DEFAULT_PLATFORM_HINT))

    def _on_platform_filter_change(self, _event: tk.Event | None = None) -> None:
        self._on_table_filter_change(_event)

    def _on_table_filter_change(self, _event: tk.Event | None = None) -> None:
        self.selected_streamer_id = None
        self.tree.selection_remove(*self.tree.selection())
        self.selection_var.set("\u672a\u9009\u62e9\u4e3b\u64ad")
        self._update_detail_panel(None)
        self._sync_action_buttons()
        self.refresh_streamer_list()

    def _filter_streamers(self, streamers: list[Streamer]) -> list[Streamer]:
        platform = self.platform_filter_var.get()
        group = self.group_filter_var.get()
        query = self.search_var.get().strip().lower()

        filtered = streamers
        if platform != PLATFORM_ALL:
            filtered = [streamer for streamer in filtered if streamer.platform == platform]
        if group == GROUP_UNGROUPED:
            filtered = [streamer for streamer in filtered if not streamer.group.strip()]
        elif group != GROUP_ALL:
            filtered = [streamer for streamer in filtered if streamer.group == group]
        if self.favorite_filter_var.get():
            filtered = [streamer for streamer in filtered if streamer.favorite]
        if query:
            filtered = [streamer for streamer in filtered if self._matches_query(streamer, query)]
        return filtered

    def _refresh_group_filter_options(self, streamers: list[Streamer]) -> None:
        groups = sorted({streamer.group.strip() for streamer in streamers if streamer.group.strip()}, key=str.lower)
        values = [GROUP_ALL, GROUP_UNGROUPED, *groups]
        if hasattr(self, "group_filter_box"):
            self.group_filter_box.configure(values=values)
        if self.group_filter_var.get() not in values:
            self.group_filter_var.set(GROUP_ALL)

    @staticmethod
    def _matches_query(streamer: Streamer, query: str) -> bool:
        haystack = " ".join(
            [
                streamer.nickname,
                streamer.platform,
                streamer.group,
                streamer.room_url,
                streamer.remark,
                streamer.live_title,
                streamer.last_error,
            ]
        ).lower()
        return query in haystack

    @staticmethod
    def _sort_streamers(streamers: list[Streamer]) -> list[Streamer]:
        status_rank = {
            STATUS_LIVE: 0,
            STATUS_ERROR: 1,
            STATUS_UNKNOWN: 2,
            STATUS_OFFLINE: 3,
        }

        def sort_key(streamer: Streamer) -> tuple[int, int, str, str]:
            enabled_rank = 0 if streamer.enabled else 1
            return (
                enabled_rank,
                status_rank.get(streamer.status, 2),
                0 if streamer.favorite else 1,
                streamer.group.lower(),
                streamer.platform.lower(),
                "" if streamer.live_title else "z",
                streamer.nickname.lower(),
            )

        return sorted(streamers, key=sort_key)

    def _update_filter_count(self, total_count: int, visible_count: int) -> None:
        if self.platform_filter_var.get() == PLATFORM_ALL:
            self.filter_count_var.set(f"\u5171 {total_count} \u4e2a")
        else:
            self.filter_count_var.set(f"\u5339\u914d {visible_count} / {total_count}")

    def _sync_action_buttons(self) -> None:
        state = "normal" if self.selected_streamer_id else "disabled"
        if hasattr(self, "delete_button"):
            self.delete_button.configure(state=state)
        if hasattr(self, "open_button"):
            self.open_button.configure(state=state)
        if hasattr(self, "check_selected_button"):
            self.check_selected_button.configure(state=state)
        if hasattr(self, "danmaku_button"):
            self.danmaku_button.configure(state=state)

    def _toggle_empty_state(self, is_empty: bool) -> None:
        if is_empty:
            if self.platform_filter_var.get() == PLATFORM_ALL:
                text = "\u8fd8\u6ca1\u6709\u4e3b\u64ad\uff0c\u53ef\u70b9\u51fb\u201c\u6dfb\u52a0\u793a\u4f8b\u201d\u6216\u5728\u4e0a\u65b9\u4fdd\u5b58\u4e00\u4e2a\u4e3b\u64ad"
            else:
                text = "\u5f53\u524d\u5e73\u53f0\u6ca1\u6709\u5339\u914d\u4e3b\u64ad\uff0c\u53ef\u5207\u56de\u201c\u5168\u90e8\u5e73\u53f0\u201d\u67e5\u770b\u5168\u90e8"
            self.empty_label.configure(text=text)
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty_label.place_forget()

    @staticmethod
    def _row_tags(streamer: Streamer) -> tuple[str, ...]:
        tags: list[str] = []
        if streamer.status == STATUS_LIVE:
            tags.append("live")
        elif streamer.status == STATUS_ERROR:
            tags.append("error")
        elif streamer.status == STATUS_OFFLINE:
            tags.append("offline")
        else:
            tags.append("unknown")
        if not streamer.enabled:
            tags.append("disabled")
        return tuple(tags)

    @staticmethod
    def _format_time(value: str) -> str:
        if not value:
            return ""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
