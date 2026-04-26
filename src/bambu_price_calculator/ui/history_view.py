"""HistoryView — Berekeningsgeschiedenis voor PandaPrice.

Toont een gesorteerde lijst van eerdere berekeningen en biedt de mogelijkheid
de geschiedenis te wissen.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from bambu_price_calculator.core.settings_manager import SettingsManager
from bambu_price_calculator.core.i18n_manager import get_i18n


class HistoryView(tk.Toplevel):
    """Modaal venster met de berekeningsgeschiedenis.

    Toont alle history-records gesorteerd op datum (meest recent bovenaan).
    Biedt een knop om de volledige geschiedenis te wissen na bevestiging.
    """

    _COLUMNS = ("filename", "timestamp", "weight", "time", "filament", "price")
    _HEADING_KEYS = {
        "filename": "history.col_file",
        "timestamp": "history.col_date",
        "weight": "history.col_weight",
        "time": "history.col_time",
        "filament": "history.col_filament",
        "price": "history.col_price",
    }
    _WIDTHS = {
        "filename": 180,
        "timestamp": 140,
        "weight": 80,
        "time": 70,
        "filament": 140,
        "price": 80,
    }

    def __init__(
        self,
        parent: tk.Tk,
        settings_manager: SettingsManager,
    ) -> None:
        super().__init__(parent)
        self._sm = settings_manager

        self.title(get_i18n().t("history.title"))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        from bambu_price_calculator.ui.theme_utils import apply_dialog_titlebar
        apply_dialog_titlebar(self)

        self.wait_window(self)

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        i18n = get_i18n()
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        # Treeview met scrollbars
        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self._COLUMNS,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=16,
        )
        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)

        for col in self._COLUMNS:
            self._tree.heading(col, text=i18n.t(self._HEADING_KEYS[col]))
            self._tree.column(col, width=self._WIDTHS[col], minwidth=50)

        self._tree.grid(row=0, column=0, sticky=tk.NSEW)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        hsb.grid(row=1, column=0, sticky=tk.EW)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Knop onderaan
        btn_frame = ttk.Frame(outer)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            btn_frame,
            text=i18n.t("history.clear"),
            command=self._clear_history,
        ).pack(side=tk.LEFT)

        ttk.Button(btn_frame, text=i18n.t("history.close"), command=self.destroy).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Ververs de treeview met de huidige geschiedenis."""
        # Verwijder bestaande rijen
        for item in self._tree.get_children():
            self._tree.delete(item)

        settings = self._sm.get()
        profiles_by_id = {p.id: p for p in settings.filament_profiles}

        # History is al gesorteerd: meest recent bovenaan (index 0)
        for record in settings.history:
            # Tijdstip: neem alleen de eerste 16 tekens (YYYY-MM-DDTHH:MM)
            ts = record.timestamp[:16].replace("T", " ") if record.timestamp else ""

            # Printtijd omzetten naar leesbaar formaat
            total_min = int(record.print_time_minutes)
            hours = total_min // 60
            minutes = total_min % 60
            time_str = f"{hours}u {minutes}m" if hours else f"{minutes}m"

            # Filamentnaam opzoeken
            profile = profiles_by_id.get(record.filament_profile_id)
            filament_str = (
                f"{profile.brand} {profile.name}" if profile else record.filament_profile_id[:8]
            )

            self._tree.insert(
                "",
                tk.END,
                values=(
                    record.filename,
                    ts,
                    f"{record.weight_grams:.1f}",
                    time_str,
                    filament_str,
                    f"{record.sale_price:.2f}",
                ),
            )

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------

    def _clear_history(self) -> None:
        """Wis de volledige geschiedenis na bevestiging."""
        i18n = get_i18n()
        confirm = messagebox.askyesno(
            i18n.t("history.clear"),
            i18n.t("history.clear_confirm"),
            parent=self,
        )
        if confirm:
            self._sm.update(history=[])
            self._refresh()
