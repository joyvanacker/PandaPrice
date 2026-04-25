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

        # Instance navigatie (verborgen tot >1 instance)
        inst_nav = ttk.Frame(outer)
        self._inst_prev = ttk.Button(inst_nav, text="◀", width=3, style="Toolbutton", command=self._prev_instance)
        self._inst_prev.pack(side=tk.LEFT)
        self._inst_label = ttk.Label(inst_nav, text="", font=("Segoe UI", 9), foreground=TEXT_SECONDARY)
        self._inst_label.pack(side=tk.LEFT, padx=8)
        self._inst_next = ttk.Button(inst_nav, text="▶", width=3, style="Toolbutton", command=self._next_instance)
        self._inst_next.pack(side=tk.LEFT)
        self._inst_nav = inst_nav

        # Card container (toont 1 plate card)
        self._card_container = ttk.Frame(outer)
        self._card_container.pack(fill=tk.BOTH, expand=True)

        # Plate navigatie (verborgen tot >1 plate)
        plate_nav = ttk.Frame(outer)
        self._plate_prev = ttk.Button(plate_nav, text="◀", width=3, style="Toolbutton", command=self._prev_plate)
        self._plate_prev.pack(side=tk.LEFT)
        self._plate_label = ttk.Label(plate_nav, text="", font=("Segoe UI", 8), foreground=TEXT_SECONDARY)
        self._plate_label.pack(side=tk.LEFT, padx=8)
        self._plate_next = ttk.Button(plate_nav, text="▶", width=3, style="Toolbutton", command=self._next_plate)
        self._plate_next.pack(side=tk.LEFT)
        self._plate_nav = plate_nav

        self._placeholder = ttk.Label(
            self._card_container, text="Wachten op G-code...",
            font=("Segoe UI", 10), foreground=TEXT_SECONDARY)
        self._placeholder.pack(anchor=tk.CENTER, pady=40)

        # Data: session_id → list of plate dicts (index 0 = totaal)
        self._sessions: dict[str, list[dict]] = {}
        self._session_order: list[str] = []
        self._inst_index: int = 0
        self._plate_index: int = 0

        # Statusbar
        self._statusbar = ttk.Label(
            self._root, text="", style="Status.TLabel", anchor=tk.W, padding=(16, 4))
        self._statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_result_card(self, session_id: str = "", plate_index: int = 0, **kwargs) -> None:
        """Voeg een plate-resultaat toe aan een session. Herberekent het totaal."""
        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

        key = session_id or f"_anon_{len(self._sessions)}"

        if key not in self._sessions:
            self._sessions[key] = [{}]  # index 0 = totaal placeholder
            self._session_order.insert(0, key)
        elif key in self._session_order:
            self._session_order.remove(key)
            self._session_order.insert(0, key)

        # Zorg dat de lijst groot genoeg is (plate_index + 1 voor plates, +1 voor totaal)
        plates = self._sessions[key]
        needed = plate_index + 2  # +1 voor totaal op index 0, +1 voor deze plate
        while len(plates) < needed:
            plates.append({})

        # Sla plate data op (index 0 = totaal, index 1+ = plates)
        plates[plate_index + 1] = kwargs

        # Herbereken totaal
        self._recalc_total(key)

        # Beperk sessions
        while len(self._session_order) > 20:
            old = self._session_order.pop()
            self._sessions.pop(old, None)

        self._inst_index = 0
        self._plate_index = 0
        self._show_current()

    def _recalc_total(self, session_id: str) -> None:
        """Herbereken het totaal van alle plates in een session."""
        plates = self._sessions[session_id]
        real_plates = [p for p in plates[1:] if p]  # skip index 0 (totaal) en lege

        if len(real_plates) <= 1:
            # Maar 1 plate: totaal = die plate
            if real_plates:
                plates[0] = dict(real_plates[0])
            return

        # Meerdere plates: som van prijs en tijd
        total_price = 0.0
        total_weight = 0.0
        total_time_min = 0.0
        all_filaments: list[tuple[str, str, float, float]] = []

        for p in real_plates:
            # Parse prijs uit string "€ 1.23"
            price_str = p.get("price", "€ 0.00")
            try:
                total_price += float(price_str.replace("€", "").strip())
            except ValueError:
                pass
            # Parse gewicht
            weight_str = p.get("weight_str", "0g")
            try:
                total_weight += float(weight_str.replace("g", "").strip())
            except ValueError:
                pass
            # Parse tijd
            time_str = p.get("time_str", "0m")
            try:
                parts = time_str.replace("u", "h ").replace("m", "").split()
                mins = 0.0
                for part in parts:
                    if "h" in part:
                        mins += float(part.replace("h", "")) * 60
                    else:
                        mins += float(part)
                total_time_min += mins
            except ValueError:
                pass
            # Filamenten
            if p.get("filament_items"):
                all_filaments.extend(p["filament_items"])

        hours = int(total_time_min // 60)
        minutes = int(total_time_min % 60)
        time_display = f"{hours}u {minutes:02d}m" if hours else f"{minutes}m"

        plates[0] = dict(
            price=f"€ {total_price:.2f}",
            time_str=time_display,
            weight_str=f"{total_weight:.1f}g",
            object_name=f"Totaal ({len(real_plates)} plates)",
            thumbnail_data=real_plates[0].get("thumbnail_data", b""),
            filament_items=all_filaments if all_filaments else None,
            details=None,
        )

    def _show_current(self) -> None:
        """Toon de huidige instance + plate."""
        from bambu_price_calculator.ui.result_card import ResultCard
        for w in self._card_container.winfo_children():
            w.destroy()

        if not self._session_order:
            return

        session_id = self._session_order[self._inst_index]
        plates = self._sessions[session_id]
        real_plates = [p for p in plates if p]

        if not real_plates:
            return

        # Clamp plate index
        if self._plate_index >= len(real_plates):
            self._plate_index = 0

        data = real_plates[self._plate_index]
        if data:
            ResultCard(self._card_container, **data).pack(fill=tk.X)

        # Instance navigatie
        total_inst = len(self._session_order)
        if total_inst > 1:
            self._inst_nav.pack(fill=tk.X, pady=(0, 6), before=self._card_container)
            self._inst_label.config(text=f"Instance {self._inst_index + 1} / {total_inst}")
            self._inst_prev.config(state=tk.NORMAL if self._inst_index < total_inst - 1 else tk.DISABLED)
            self._inst_next.config(state=tk.NORMAL if self._inst_index > 0 else tk.DISABLED)
        else:
            self._inst_nav.pack_forget()

        # Plate navigatie (alleen als >1 plate, dwz totaal + minstens 2 echte plates)
        num_real = len(real_plates)
        if num_real > 2:  # totaal + 2+ plates
            self._plate_nav.pack(fill=tk.X, pady=(6, 0))
            if self._plate_index == 0:
                label = "Totaal"
            else:
                label = f"Plate {self._plate_index}"
            self._plate_label.config(text=f"{label}  ({self._plate_index + 1}/{num_real})")
            self._plate_prev.config(state=tk.NORMAL if self._plate_index > 0 else tk.DISABLED)
            self._plate_next.config(state=tk.NORMAL if self._plate_index < num_real - 1 else tk.DISABLED)
        else:
            self._plate_nav.pack_forget()

    def _prev_instance(self) -> None:
        if self._inst_index < len(self._session_order) - 1:
            self._inst_index += 1
            self._plate_index = 0
            self._show_current()

    def _next_instance(self) -> None:
        if self._inst_index > 0:
            self._inst_index -= 1
            self._plate_index = 0
            self._show_current()

    def _prev_plate(self) -> None:
        if self._plate_index > 0:
            self._plate_index -= 1
            self._show_current()

    def _next_plate(self) -> None:
        session_id = self._session_order[self._inst_index]
        plates = [p for p in self._sessions[session_id] if p]
        if self._plate_index < len(plates) - 1:
            self._plate_index += 1
            self._show_current()

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
