"""MainWindow — Hoofdvenster van de Bambu Price Calculator.

Bevat de hoofd-UI met berekening-instellingen, monitor-status en resultaatweergave.
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

BAMBU_GREEN = "#00ae42"

# Thema-opties: weergavenaam → interne waarde
_THEME_OPTIONS = ["Licht", "Donker", "Systeem"]
_THEME_MAP = {"Licht": "light", "Donker": "dark", "Systeem": "system"}
_THEME_MAP_INV = {v: k for k, v in _THEME_MAP.items()}


class MainWindow:
    """Hoofdvenster van de Bambu Price Calculator.

    Wraps een tk.Tk root en bouwt de volledige UI op.
    """

    def __init__(
        self,
        root: tk.Tk,
        i18n: I18nManager,
        settings_manager: SettingsManager,
    ) -> None:
        self._root = root
        self._i18n = i18n
        self._sm = settings_manager

        # Callbacks — worden ingesteld door de App-klasse
        self.on_toggle_watch: Callable[[], None] | None = None
        self.on_open_settings: Callable[[], None] | None = None
        self.on_open_filaments: Callable[[], None] | None = None
        self.on_open_history: Callable[[], None] | None = None
        self.on_check_update: Callable[[], None] | None = None
        self.on_settings_changed: Callable[[str, float], None] | None = None
        self.on_quit: Callable[[], None] | None = None

        # Haal huidige instellingen op
        settings = self._sm.get()

        # Tkinter variabelen
        self._cost_per_hour = tk.DoubleVar(value=settings.cost_per_hour)
        self._filament_margin = tk.DoubleVar(value=settings.filament_margin_pct)
        self._profit_margin = tk.DoubleVar(value=settings.profit_margin_pct)
        self._theme_var = tk.StringVar(
            value=_THEME_MAP_INV.get(settings.theme, "Systeem")
        )

        # Venster configuratie
        self._root.title("Bambu Price Calculator")
        self._root.resizable(False, False)

        # sv_ttk styling
        sv_ttk.set_theme(self._resolve_sv_theme(settings.theme))

        # UI opbouwen
        self._build_menubar()
        self._build_ui()

        # Trace variabelen voor directe herberekening
        self._cost_per_hour.trace_add("write", self._on_cost_per_hour_changed)
        self._filament_margin.trace_add("write", self._on_filament_margin_changed)
        self._profit_margin.trace_add("write", self._on_profit_margin_changed)
        self._theme_var.trace_add("write", self._on_theme_changed)

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_menubar(self) -> None:
        """Bouw de menubalk op."""
        menubar = tk.Menu(self._root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Instellingen",
            command=lambda: self.on_open_settings and self.on_open_settings(),
        )
        file_menu.add_command(
            label="Filamentprofielen",
            command=lambda: self.on_open_filaments and self.on_open_filaments(),
        )
        file_menu.add_command(
            label="Geschiedenis",
            command=lambda: self.on_open_history and self.on_open_history(),
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Controleer op updates",
            command=lambda: self.on_check_update and self.on_check_update(),
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Afsluiten",
            command=self._on_quit,
        )

        menubar.add_cascade(label="Bestand", menu=file_menu)
        self._root.config(menu=menubar)

    def _build_ui(self) -> None:
        """Bouw de hoofd-UI op."""
        outer = ttk.Frame(self._root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_calculation_section(outer)
        self._build_monitor_section(outer)
        self._build_result_section(outer)
        self._build_statusbar()

    def _build_calculation_section(self, parent: ttk.Frame) -> None:
        """Bouw de 'Berekening' sectie."""
        frame = ttk.LabelFrame(parent, text="Berekening", padding=8)
        frame.pack(fill=tk.X, pady=(0, 6))

        # Kosten/uur
        ttk.Label(frame, text="Kosten/uur (€):").grid(
            row=0, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(frame, textvariable=self._cost_per_hour, width=10).grid(
            row=0, column=1, sticky=tk.W, padx=(6, 0), pady=2
        )

        # Filamentmarge
        ttk.Label(frame, text="Filamentmarge (%):").grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(frame, textvariable=self._filament_margin, width=10).grid(
            row=1, column=1, sticky=tk.W, padx=(6, 0), pady=2
        )

        # Winstmarge
        ttk.Label(frame, text="Winstmarge (%):").grid(
            row=2, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(frame, textvariable=self._profit_margin, width=10).grid(
            row=2, column=1, sticky=tk.W, padx=(6, 0), pady=2
        )

        # Thema
        ttk.Label(frame, text="Thema:").grid(
            row=3, column=0, sticky=tk.W, pady=2
        )
        theme_cb = ttk.Combobox(
            frame,
            textvariable=self._theme_var,
            values=_THEME_OPTIONS,
            state="readonly",
            width=9,
        )
        theme_cb.grid(row=3, column=1, sticky=tk.W, padx=(6, 0), pady=2)

    def _build_monitor_section(self, parent: ttk.Frame) -> None:
        """Bouw de 'Monitor' sectie."""
        frame = ttk.LabelFrame(parent, text="Monitor", padding=8)
        frame.pack(fill=tk.X, pady=(0, 6))

        self._watch_btn = ttk.Button(
            frame,
            text="START AUTO-UPDATE",
            command=self._on_toggle_watch,
        )
        self._watch_btn.pack(side=tk.LEFT, padx=(0, 10))

        self._status_label = ttk.Label(frame, text="Stand-by")
        self._status_label.pack(side=tk.LEFT)

    def _build_result_section(self, parent: ttk.Frame) -> None:
        """Bouw de 'Resultaat' sectie."""
        frame = ttk.LabelFrame(parent, text="Resultaat", padding=8)
        frame.pack(fill=tk.X, pady=(0, 6))

        # Bestandsnaam
        self._filename_label = ttk.Label(frame, text="—")
        self._filename_label.pack(anchor=tk.W)

        # Gewicht + Tijd
        self._weight_time_label = ttk.Label(frame, text="")
        self._weight_time_label.pack(anchor=tk.W)

        # Separator
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        # "TOTAALPRIJS" label
        ttk.Label(
            frame,
            text="TOTAALPRIJS",
            foreground=BAMBU_GREEN,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor=tk.W)

        # Prijs label
        self._price_label = ttk.Label(
            frame,
            text="€ 0.00",
            foreground=BAMBU_GREEN,
            font=("TkDefaultFont", 18, "bold"),
        )
        self._price_label.pack(anchor=tk.W)

        # Filament label
        self._filament_label = ttk.Label(frame, text="")
        self._filament_label.pack(anchor=tk.W)

    def _build_statusbar(self) -> None:
        """Bouw de statusbalk onderaan het venster."""
        self._statusbar = ttk.Label(
            self._root,
            text="",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(4, 2),
        )
        self._statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # Publieke methoden
    # ------------------------------------------------------------------

    def update_result(self, result: CalculationResult) -> None:
        """Update de resultaat-sectie met een nieuw CalculationResult."""
        self._filename_label.config(text=result.filename)

        hours = int(result.print_time_minutes // 60)
        minutes = int(result.print_time_minutes % 60)
        time_str = f"{hours}u {minutes}m" if hours else f"{minutes}m"
        self._weight_time_label.config(
            text=f"{result.weight_grams:.1f} g  •  {time_str}"
        )

        self._price_label.config(text=f"€ {result.sale_price:.2f}")

        profile = result.filament_profile
        self._filament_label.config(
            text=f"{profile.brand} {profile.name} ({profile.material_type})"
        )

    def set_status(self, text: str, is_error: bool = False) -> None:
        """Update de statusbalk. Bij is_error wordt de tekst rood weergegeven."""
        color = "red" if is_error else ""
        self._statusbar.config(text=text, foreground=color)

    def set_watch_active(self, active: bool) -> None:
        """Update de knoptekst op basis van de bewakingsstatus."""
        self._watch_btn.config(
            text="STOP AUTO-UPDATE" if active else "START AUTO-UPDATE"
        )

    def apply_theme(self, theme: str) -> None:
        """Pas het sv_ttk thema toe en update de titelbalkkleur.

        Args:
            theme: "light", "dark" of "system"
        """
        sv_theme = self._resolve_sv_theme(theme)
        sv_ttk.set_theme(sv_theme)
        self._update_titlebar(sv_theme)

    # ------------------------------------------------------------------
    # Interne callbacks
    # ------------------------------------------------------------------

    def _on_toggle_watch(self) -> None:
        if self.on_toggle_watch:
            self.on_toggle_watch()

    def _on_quit(self) -> None:
        if self.on_quit:
            self.on_quit()
        else:
            self._root.destroy()

    def _on_cost_per_hour_changed(self, *_: object) -> None:
        try:
            value = self._cost_per_hour.get()
            self._sm.update(cost_per_hour=value)
            if self.on_settings_changed:
                self.on_settings_changed("cost_per_hour", value)
        except tk.TclError:
            pass  # Ongeldige invoer — negeer

    def _on_filament_margin_changed(self, *_: object) -> None:
        try:
            value = self._filament_margin.get()
            self._sm.update(filament_margin_pct=value)
            if self.on_settings_changed:
                self.on_settings_changed("filament_margin_pct", value)
        except tk.TclError:
            pass

    def _on_profit_margin_changed(self, *_: object) -> None:
        try:
            value = self._profit_margin.get()
            self._sm.update(profit_margin_pct=value)
            if self.on_settings_changed:
                self.on_settings_changed("profit_margin_pct", value)
        except tk.TclError:
            pass

    def _on_theme_changed(self, *_: object) -> None:
        display = self._theme_var.get()
        internal = _THEME_MAP.get(display, "system")
        self._sm.update(theme=internal)
        self.apply_theme(internal)
        if self.on_settings_changed:
            self.on_settings_changed("theme", 0.0)  # theme is geen float, signaal sturen

    # ------------------------------------------------------------------
    # Hulpmethoden
    # ------------------------------------------------------------------

    def _resolve_sv_theme(self, theme: str) -> str:
        """Zet een interne thema-waarde om naar een sv_ttk thema-naam."""
        if theme == "dark":
            return "dark"
        if theme == "light":
            return "light"
        # "system": detecteer Windows-thema
        return self._detect_system_theme()

    @staticmethod
    def _detect_system_theme() -> str:
        """Detecteer het actieve Windows-thema via de registry."""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value else "dark"
        except Exception:
            return "light"

    def _update_titlebar(self, sv_theme: str) -> None:
        """Pas de Windows titelbalkkleur aan op basis van het actieve thema."""
        try:
            hwnd = self._root.winfo_id()
            set_titlebar_color(hwnd, dark=(sv_theme == "dark"))
        except Exception:
            pass
