"""SettingsDialog — Instellingendialoog met eenvoudige en geavanceerde modus.

Eenvoudig: kosten/uur, filamentmarge, winstmarge
Geavanceerd: uitgesplitste machinekosten, arbeidskosten, vaste kosten
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from bambu_price_calculator.core.settings_manager import SettingsManager

_THEME_OPTIONS = ["Licht", "Donker", "Systeem"]
_THEME_MAP = {"Licht": "light", "Donker": "dark", "Systeem": "system"}
_THEME_MAP_INV = {v: k for k, v in _THEME_MAP.items()}


class SettingsDialog(tk.Toplevel):
    """Modaal instellingendialoog met tabbladen."""

    def __init__(
        self,
        parent: tk.Tk,
        settings_manager: SettingsManager,
        on_path_changed: Callable[[str], None] | None = None,
        on_settings_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._sm = settings_manager
        self._on_path_changed = on_path_changed
        self._on_settings_changed = on_settings_changed
        self._s = self._sm.get()

        self.title("Instellingen")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._vars: dict[str, tk.Variable] = {}
        self._build_ui()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        from bambu_price_calculator.ui.theme_utils import apply_dialog_titlebar
        apply_dialog_titlebar(self)

        self.wait_window(self)

    def _sv(self, key: str, default) -> tk.StringVar:
        """Maak een StringVar aan en bewaar in _vars."""
        v = tk.StringVar(value=str(default))
        self._vars[key] = v
        return v

    def _bv(self, key: str, default: bool) -> tk.BooleanVar:
        v = tk.BooleanVar(value=default)
        self._vars[key] = v
        return v

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        nb = ttk.Notebook(outer)
        nb.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        # Tab 1: Algemeen
        tab_general = ttk.Frame(nb, padding=12)
        nb.add(tab_general, text="Algemeen")
        self._build_general_tab(tab_general)

        # Tab 2: Eenvoudig
        tab_simple = ttk.Frame(nb, padding=12)
        nb.add(tab_simple, text="Eenvoudig")
        self._build_simple_tab(tab_simple)

        # Tab 3: Geavanceerd
        tab_adv = ttk.Frame(nb, padding=12)
        nb.add(tab_adv, text="Geavanceerd")
        self._build_advanced_tab(tab_adv)

        # Knoppen
        btn_frame = ttk.Frame(outer)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Opslaan", command=self._save).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Annuleren", command=self.destroy).pack(side=tk.LEFT)

    def _build_general_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(parent, text="G-code map:", font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))
        row += 1

        pf = ttk.Frame(parent)
        pf.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=(0, 12))
        path_var = self._sv("gcode_watch_path", self._s.gcode_watch_path)
        ttk.Entry(pf, textvariable=path_var, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(pf, text="...", width=3, command=lambda: self._browse(path_var)).pack(side=tk.LEFT, padx=(6, 0))
        row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=8)
        row += 1

        ttk.Label(parent, text="Thema").grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(parent, textvariable=self._sv("theme", _THEME_MAP_INV.get(self._s.theme, "Systeem")),
                      values=_THEME_OPTIONS, state="readonly", width=9).grid(row=row, column=1, sticky=tk.E, pady=3)
        row += 1

        ttk.Label(parent, text="Taal").grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(parent, textvariable=self._sv("language", self._s.language),
                      values=self._available_languages(), state="readonly", width=9).grid(row=row, column=1, sticky=tk.E, pady=3)
        row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=8)
        row += 1

        adv_var = self._bv("use_advanced_pricing", self._s.use_advanced_pricing)
        ttk.Checkbutton(parent, text="Geavanceerde prijsberekening gebruiken", variable=adv_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=3)

    def _build_simple_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        fields = [
            ("Kosten per uur (€)", "cost_per_hour", self._s.cost_per_hour),
            ("Filamentmarge (%)", "filament_margin_pct", self._s.filament_margin_pct),
            ("Winstmarge (%)", "profit_margin_pct", self._s.profit_margin_pct),
        ]
        for row, (label, key, val) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
            ttk.Entry(parent, textvariable=self._sv(key, val), width=10, justify="right").grid(
                row=row, column=1, sticky=tk.E, pady=3)

        ttk.Label(parent, text="Wordt gebruikt als 'Geavanceerd' uitstaat.",
                  font=("Segoe UI", 8), foreground="#888").grid(
            row=len(fields), column=0, columnspan=2, sticky=tk.W, pady=(12, 0))

    def _build_advanced_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        row = 0

        sections = [
            ("Machinekosten", [
                ("Stroomverbruik (W)", "energy_watt", self._s.energy_watt),
                ("Elektriciteitsprijs (€/kWh)", "energy_price_kwh", self._s.energy_price_kwh),
                ("Aanschafprijs printer (€)", "machine_price", self._s.machine_price),
                ("Levensduur printer (uren)", "machine_lifespan_hours", self._s.machine_lifespan_hours),
                ("Onderhoudskost (€/uur)", "maintenance_per_hour", self._s.maintenance_per_hour),
            ]),
            ("Arbeidskosten", [
                ("Voorbewerkingstijd (min)", "prep_time_min", self._s.prep_time_min),
                ("Nabewerkingstijd (min)", "post_time_min", self._s.post_time_min),
                ("Uurtarief arbeid (€/uur)", "labor_rate", self._s.labor_rate),
            ]),
            ("Vaste kosten per print", [
                ("Opstartkosten (€)", "setup_cost", self._s.setup_cost),
                ("Faalpercentage (%)", "failure_rate_pct", self._s.failure_rate_pct),
            ]),
            ("Marges", [
                ("Filamentmarge (%)", "filament_margin_pct_adv", self._s.filament_margin_pct),
                ("Winstmarge (%)", "profit_margin_pct_adv", self._s.profit_margin_pct),
            ]),
        ]

        for section_name, fields in sections:
            ttk.Label(parent, text=section_name, font=("Segoe UI", 9, "bold")).grid(
                row=row, column=0, columnspan=2, sticky=tk.W, pady=(8, 4))
            row += 1
            for label, key, val in fields:
                ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2, padx=(8, 0))
                ttk.Entry(parent, textvariable=self._sv(key, val), width=10, justify="right").grid(
                    row=row, column=1, sticky=tk.E, pady=2)
                row += 1

        ttk.Label(parent, text="Wordt gebruikt als 'Geavanceerd' aanstaat.",
                  font=("Segoe UI", 8), foreground="#888").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(12, 0))

    def _browse(self, var: tk.StringVar) -> None:
        chosen = filedialog.askdirectory(parent=self, title="Selecteer G-code map", initialdir=var.get() or "/")
        if chosen:
            var.set(chosen)

    def _get_float(self, key: str, default: float) -> float:
        try:
            return float(self._vars[key].get())
        except (KeyError, ValueError):
            return default

    def _save(self) -> None:
        old_path = self._s.gcode_watch_path
        new_path = self._vars["gcode_watch_path"].get()
        use_adv = self._vars["use_advanced_pricing"].get()

        updates = dict(
            gcode_watch_path=new_path,
            theme=_THEME_MAP.get(self._vars["theme"].get(), "system"),
            language=self._vars["language"].get(),
            use_advanced_pricing=use_adv,
            # Eenvoudig
            cost_per_hour=self._get_float("cost_per_hour", self._s.cost_per_hour),
            # Geavanceerd
            energy_watt=self._get_float("energy_watt", self._s.energy_watt),
            energy_price_kwh=self._get_float("energy_price_kwh", self._s.energy_price_kwh),
            machine_price=self._get_float("machine_price", self._s.machine_price),
            machine_lifespan_hours=self._get_float("machine_lifespan_hours", self._s.machine_lifespan_hours),
            maintenance_per_hour=self._get_float("maintenance_per_hour", self._s.maintenance_per_hour),
            prep_time_min=self._get_float("prep_time_min", self._s.prep_time_min),
            post_time_min=self._get_float("post_time_min", self._s.post_time_min),
            labor_rate=self._get_float("labor_rate", self._s.labor_rate),
            setup_cost=self._get_float("setup_cost", self._s.setup_cost),
            failure_rate_pct=self._get_float("failure_rate_pct", self._s.failure_rate_pct),
        )

        # Marges: gebruik geavanceerde waarden als geavanceerd actief
        if use_adv:
            updates["filament_margin_pct"] = self._get_float("filament_margin_pct_adv", self._s.filament_margin_pct)
            updates["profit_margin_pct"] = self._get_float("profit_margin_pct_adv", self._s.profit_margin_pct)
        else:
            updates["filament_margin_pct"] = self._get_float("filament_margin_pct", self._s.filament_margin_pct)
            updates["profit_margin_pct"] = self._get_float("profit_margin_pct", self._s.profit_margin_pct)

        self._sm.update(**updates)

        if self._on_path_changed and new_path != old_path:
            self._on_path_changed(new_path)
        if self._on_settings_changed:
            self._on_settings_changed()

        self.destroy()

    def _available_languages(self) -> list[str]:
        try:
            from bambu_price_calculator.core.i18n_manager import I18nManager
            return ["auto"] + I18nManager().available_locales()
        except Exception:
            return ["auto", "nl", "en"]
