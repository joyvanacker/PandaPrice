"""SettingsDialog — Instellingendialoog voor de Bambu Price Calculator.

Biedt een modaal formulier voor het configureren van de gcode-map en taal.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from bambu_price_calculator.core.settings_manager import SettingsManager


class SettingsDialog(tk.Toplevel):
    """Modaal instellingendialoog.

    Laat de gebruiker de gcode-bewakingsmap en taal instellen.
    Wijzigingen worden opgeslagen via SettingsManager.update().
    """

    def __init__(
        self,
        parent: tk.Tk,
        settings_manager: SettingsManager,
        on_path_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._sm = settings_manager
        self._on_path_changed = on_path_changed

        settings = self._sm.get()

        self.title("Instellingen")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Tkinter variabelen
        self._path_var = tk.StringVar(value=settings.gcode_watch_path)
        self._lang_var = tk.StringVar(value=settings.language)

        self._build_ui()

        # Centreer t.o.v. parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.wait_window(self)

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        # --- G-code map ---
        ttk.Label(outer, text="G-code map:").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4)
        )
        path_frame = ttk.Frame(outer)
        path_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        outer.columnconfigure(0, weight=1)

        self._path_entry = ttk.Entry(path_frame, textvariable=self._path_var, width=40)
        self._path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(path_frame, text="Bladeren...", command=self._browse_path).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        # --- Taal ---
        ttk.Label(outer, text="Taal:").grid(
            row=2, column=0, sticky=tk.W, pady=(0, 4)
        )
        lang_cb = ttk.Combobox(
            outer,
            textvariable=self._lang_var,
            values=self._available_languages(),
            state="readonly",
            width=20,
        )
        lang_cb.grid(row=3, column=0, sticky=tk.W, pady=(0, 16))

        # --- Knoppen ---
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky=tk.E)

        ttk.Button(btn_frame, text="Opslaan", command=self._save).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Annuleren", command=self.destroy).pack(
            side=tk.LEFT
        )

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------

    def _browse_path(self) -> None:
        """Open een mapkiezer en sla het geselecteerde pad op."""
        current = self._path_var.get() or "/"
        chosen = filedialog.askdirectory(
            parent=self,
            title="Selecteer G-code map",
            initialdir=current,
        )
        if chosen:
            self._path_var.set(chosen)

    def _save(self) -> None:
        """Sla de instellingen op en sluit de dialoog."""
        old_path = self._sm.get().gcode_watch_path
        new_path = self._path_var.get()
        new_lang = self._lang_var.get()

        self._sm.update(gcode_watch_path=new_path, language=new_lang)

        if self._on_path_changed and new_path != old_path:
            self._on_path_changed(new_path)

        self.destroy()

    # ------------------------------------------------------------------
    # Hulpmethoden
    # ------------------------------------------------------------------

    def _available_languages(self) -> list[str]:
        """Geef de beschikbare talen terug."""
        try:
            from bambu_price_calculator.core.i18n_manager import I18nManager
            mgr = I18nManager()
            return ["auto"] + mgr.available_locales()
        except Exception:
            return ["auto", "nl", "en"]
