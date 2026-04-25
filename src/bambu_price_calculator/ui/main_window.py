"""MainWindow — Hoofdvenster van PandaPrice.

Bambu Studio-geïnspireerd design met carousel voor meerdere resultaten.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import sv_ttk

from bambu_price_calculator.core.i18n_manager import I18nManager
from bambu_price_calculator.core.price_calculator import CalculationResult
from bambu_price_calculator.core.settings_manager import SettingsManager
from bambu_price_calculator.platform.dwm import set_titlebar_color

BAMBU_GREEN = "#00AE42"
BAMBU_GREEN_HOVER = "#00C94D"
BAMBU_GREEN_DIM = "#008A35"
TEXT_SECONDARY = "#888888"

_THEME_OPTIONS = ["Licht", "Donker", "Systeem"]
_THEME_MAP = {"Licht": "light", "Donker": "dark", "Systeem": "system"}
_THEME_MAP_INV = {v: k for k, v in _THEME_MAP.items()}
_WINDOW_WIDTH = 380


class _Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tw: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event: tk.Event) -> None:
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tw = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)
        tk.Label(tw, text=self._text, background="#333", foreground="#eee",
                 font=("Segoe UI", 8), padx=6, pady=3, relief=tk.SOLID, borderwidth=1).pack()

    def _hide(self, event: tk.Event) -> None:
        if self._tw:
            self._tw.destroy()
            self._tw = None


class MainWindow:
    def __init__(self, root: tk.Tk, i18n: I18nManager, settings_manager: SettingsManager) -> None:
        self._root = root
        self._i18n = i18n
        self._sm = settings_manager

        self.on_toggle_watch: Callable[[], None] | None = None
        self.on_open_settings: Callable[[], None] | None = None
        self.on_open_filaments: Callable[[], None] | None = None
        self.on_open_history: Callable[[], None] | None = None
        self.on_check_update: Callable[[], None] | None = None
        self.on_about: Callable[[], None] | None = None
        self.on_quit: Callable[[], None] | None = None

        settings = self._sm.get()
        self._root.title("PandaPrice")
        self._root.resizable(False, False)
        self._root.minsize(_WINDOW_WIDTH, 400)

        try:
            from pathlib import Path
            icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self._root.iconbitmap(str(icon_path))
        except Exception:
            pass

        sv_ttk.set_theme(self._resolve_sv_theme(settings.theme))
        self._apply_custom_styles()
        self._build_menubar()
        self._build_ui()
        self._update_titlebar(self._resolve_sv_theme(settings.theme))

    def _apply_custom_styles(self) -> None:
        s = ttk.Style()
        s.configure("Section.TLabel", font=("Segoe UI", 9, "bold"), foreground=TEXT_SECONDARY)
        s.configure("Price.TLabel", font=("Segoe UI", 28, "bold"), foreground=BAMBU_GREEN)
        s.configure("PriceHeader.TLabel", font=("Segoe UI", 10, "bold"), foreground=BAMBU_GREEN)
        s.configure("Filename.TLabel", font=("Segoe UI", 10, "bold"))
        s.configure("Info.TLabel", font=("Segoe UI", 9), foreground=TEXT_SECONDARY)
        s.configure("Filament.TLabel", font=("Segoe UI", 9))
        s.configure("Status.TLabel", font=("Segoe UI", 8), foreground=TEXT_SECONDARY)
        s.configure("StatusActive.TLabel", font=("Segoe UI", 8), foreground=BAMBU_GREEN)
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_menubar(self) -> None:
        from PIL import Image, ImageDraw, ImageTk
        self._root.config(menu=tk.Menu(self._root))
        self._toolbar_icons: list[ImageTk.PhotoImage] = []

        toolbar = ttk.Frame(self._root, padding=(10, 6, 10, 4))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(toolbar, text="PandaPrice", font=("Segoe UI", 11, "bold"),
                  foreground=BAMBU_GREEN).pack(side=tk.LEFT)

        self._status_label = ttk.Label(toolbar, text="", font=("Segoe UI", 9))
        self._status_label.pack(side=tk.LEFT, padx=(8, 0))
        self._status_tooltip: _Tooltip | None = None

        btn_style = "Toolbutton"
        sz = 18

        def _icon(fn) -> ImageTk.PhotoImage:
            img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            fn(ImageDraw.Draw(img), sz)
            p = ImageTk.PhotoImage(img)
            self._toolbar_icons.append(p)
            return p

        def _gear(d, s):
            c = s // 2
            d.ellipse([2, 2, s-3, s-3], outline="#aaa", width=3)
            d.ellipse([6, 6, s-7, s-7], fill=(0,0,0,0), outline="#aaa", width=1)
            d.line([(c, 1), (c, s-2)], fill="#aaa", width=2)
            d.line([(1, c), (s-2, c)], fill="#aaa", width=2)

        def _spool(d, s):
            c = s // 2
            d.rectangle([3, 1, s-4, s-2], outline=BAMBU_GREEN, width=2)
            d.line([(5, c), (s-6, c)], fill=BAMBU_GREEN, width=1)
            d.ellipse([c-2, c-2, c+2, c+2], outline=BAMBU_GREEN, width=1)

        def _list(d, s):
            for y in (4, 9, 14):
                d.line([(3, y), (s-4, y)], fill="#aaa", width=1)

        def _refresh(d, s):
            d.arc([3, 3, s-4, s-4], start=30, end=330, fill="#aaa", width=2)
            d.polygon([(s-5, 3), (s-2, 7), (s-8, 7)], fill="#aaa")

        def _info(d, s):
            c = s // 2
            d.ellipse([2, 2, s-3, s-3], outline="#aaa", width=2)
            d.line([(c, 7), (c, 7)], fill="#aaa", width=2)
            d.line([(c, 10), (c, s-5)], fill="#aaa", width=2)

        for img, tip, cmd in [
            (_icon(_info), "Over PandaPrice", lambda: self.on_about and self.on_about()),
            (_icon(_refresh), "Controleer op updates", lambda: self.on_check_update and self.on_check_update()),
            (_icon(_list), "Geschiedenis", lambda: self.on_open_history and self.on_open_history()),
            (_icon(_spool), "Filamentprofielen", lambda: self.on_open_filaments and self.on_open_filaments()),
            (_icon(_gear), "Instellingen", lambda: self.on_open_settings and self.on_open_settings()),
        ]:
            b = ttk.Button(toolbar, image=img, style=btn_style, command=cmd)
            b.pack(side=tk.RIGHT, padx=2)
            _Tooltip(b, tip)

        ttk.Separator(self._root, orient=tk.HORIZONTAL).pack(fill=tk.X)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self._root, padding=(16, 12, 16, 8))
        outer.pack(fill=tk.BOTH, expand=True)

        # Navigatie (verborgen tot >1 resultaat)
        nav = ttk.Frame(outer)
        self._nav_prev = ttk.Button(nav, text="◀", width=3, style="Toolbutton", command=self._prev_result)
        self._nav_prev.pack(side=tk.LEFT)
        self._nav_label = ttk.Label(nav, text="", font=("Segoe UI", 9), foreground=TEXT_SECONDARY)
        self._nav_label.pack(side=tk.LEFT, padx=8)
        self._nav_next = ttk.Button(nav, text="▶", width=3, style="Toolbutton", command=self._next_result)
        self._nav_next.pack(side=tk.LEFT)
        self._nav_frame = nav

        # Card container
        self._card_container = ttk.Frame(outer)
        self._card_container.pack(fill=tk.BOTH, expand=True)

        self._placeholder = ttk.Label(
            self._card_container, text="Wachten op G-code...",
            font=("Segoe UI", 10), foreground=TEXT_SECONDARY)
        self._placeholder.pack(anchor=tk.CENTER, pady=40)

        self._results: dict[str, dict] = {}
        self._result_order: list[str] = []
        self._current_index: int = 0

        # Statusbar
        self._statusbar = ttk.Label(
            self._root, text="", style="Status.TLabel", anchor=tk.W, padding=(16, 4))
        self._statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_result_card(self, session_id: str = "", **kwargs) -> None:
        """Voeg toe of update een resultaat per session_id."""
        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

        key = session_id or f"_anon_{len(self._results)}"

        if key in self._results:
            self._results[key] = kwargs
            self._result_order.remove(key)
        else:
            self._results[key] = kwargs

        self._result_order.insert(0, key)

        while len(self._result_order) > 20:
            self._results.pop(self._result_order.pop(), None)

        self._current_index = 0
        self._show_current_card()

    def _show_current_card(self) -> None:
        from bambu_price_calculator.ui.result_card import ResultCard
        for w in self._card_container.winfo_children():
            w.destroy()
        if not self._result_order:
            return

        data = self._results[self._result_order[self._current_index]]
        ResultCard(self._card_container, **data).pack(fill=tk.X)

        total = len(self._result_order)
        if total > 1:
            self._nav_frame.pack(fill=tk.X, pady=(0, 8), before=self._card_container)
            self._nav_label.config(text=f"{self._current_index + 1} / {total}")
            self._nav_prev.config(state=tk.NORMAL if self._current_index < total - 1 else tk.DISABLED)
            self._nav_next.config(state=tk.NORMAL if self._current_index > 0 else tk.DISABLED)
        else:
            self._nav_frame.pack_forget()

    def _prev_result(self) -> None:
        if self._current_index < len(self._result_order) - 1:
            self._current_index += 1
            self._show_current_card()

    def _next_result(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current_card()

    def set_status(self, text: str, is_error: bool = False) -> None:
        if is_error:
            self._status_label.config(text="Inactief", foreground="#E74C3C")
            if self._status_tooltip:
                self._status_tooltip._text = text
            else:
                self._status_tooltip = _Tooltip(self._status_label, text)
            self._statusbar.config(text=text, foreground="#E74C3C")
        else:
            self._statusbar.config(text=text, foreground=TEXT_SECONDARY)

    def set_watch_active(self, active: bool) -> None:
        if active:
            self._status_label.config(text="Actief", foreground=BAMBU_GREEN)
            self._status_tooltip = None
        else:
            self._status_label.config(text="", foreground=TEXT_SECONDARY)

    def apply_theme(self, theme: str) -> None:
        sv_ttk.set_theme(self._resolve_sv_theme(theme))
        self._apply_custom_styles()
        self._update_titlebar(self._resolve_sv_theme(theme))

    def _on_toggle_watch(self) -> None:
        if self.on_toggle_watch:
            self.on_toggle_watch()

    def _on_quit(self) -> None:
        if self.on_quit:
            self.on_quit()
        else:
            self._root.destroy()

    def _resolve_sv_theme(self, theme: str) -> str:
        if theme in ("dark", "light"):
            return theme
        return self._detect_system_theme()

    @staticmethod
    def _detect_system_theme() -> str:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value else "dark"
        except Exception:
            return "light"

    def _update_titlebar(self, sv_theme: str) -> None:
        try:
            self._root.update()
            set_titlebar_color(self._root.winfo_id(), dark=(sv_theme == "dark"))
        except Exception:
            pass
