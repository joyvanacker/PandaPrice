"""FilamentDialog — Filamentprofiel beheer voor PandaPrice.

Biedt een modaal venster voor het aanmaken, bewerken en verwijderen van
filamentprofielen. Bevat ook show_unknown_filament_dialog() als standalone
functie voor het invoeren van een prijs voor een onbekend filament.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from bambu_price_calculator.core.settings_manager import FilamentProfile, SettingsManager
from bambu_price_calculator.core.i18n_manager import get_i18n


# ---------------------------------------------------------------------------
# Standalone hulpfunctie
# ---------------------------------------------------------------------------

def show_unknown_filament_dialog(
    parent: tk.Tk | tk.Toplevel,
    filament_id: str,
    material_type: str,
) -> float | None:
    """Vraag de gebruiker om een aankoopprijs per kg voor een onbekend filament.

    Args:
        parent: Het bovenliggende venster.
        filament_id: Het filament-ID uit de gcode-metadata.
        material_type: Het materiaaltype uit de gcode-metadata.

    Returns:
        De ingevoerde prijs per kg als float, of None als geannuleerd.
    """
    i18n = get_i18n()
    prompt = i18n.t("filament.unknown_body", filament_id=filament_id, material=material_type)
    result = simpledialog.askfloat(
        title=i18n.t("filament.unknown_title"),
        prompt=prompt,
        parent=parent,
        minvalue=0.0,
    )
    return result


# ---------------------------------------------------------------------------
# FilamentFormDialog — inner formulier voor aanmaken/bewerken
# ---------------------------------------------------------------------------

class _FilamentFormDialog(tk.Toplevel):
    """Formulierdialoog voor het aanmaken of bewerken van een filamentprofiel."""

    def __init__(
        self,
        parent: tk.Toplevel,
        profile: FilamentProfile | None = None,
    ) -> None:
        super().__init__(parent)
        self._profile = profile
        self.result: FilamentProfile | None = None

        i18n = get_i18n()
        self.title(i18n.t("filament.edit_title") if profile else i18n.t("filament.add_title"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Vul velden in met bestaande waarden of lege standaarden
        p = profile
        self._name_var = tk.StringVar(value=p.name if p else "")
        self._brand_var = tk.StringVar(value=p.brand if p else "")
        self._color_var = tk.StringVar(value=p.color_hex if p else "#FFFFFF")
        self._material_var = tk.StringVar(value=p.material_type if p else "")
        self._weight_var = tk.StringVar(value=str(p.spool_weight_grams) if p else "1000")
        self._price_var = tk.StringVar(value=str(p.purchase_price_eur) if p else "25.0")

        self._build_ui()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        from bambu_price_calculator.ui.theme_utils import apply_dialog_titlebar
        apply_dialog_titlebar(self)

        self.wait_window(self)

    def _build_ui(self) -> None:
        i18n = get_i18n()
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        fields: list[tuple[str, tk.StringVar]] = [
            (i18n.t("filament.name"), self._name_var),
            (i18n.t("filament.brand"), self._brand_var),
            (i18n.t("filament.color"), self._color_var),
            (i18n.t("filament.material"), self._material_var),
            (i18n.t("filament.spool_weight"), self._weight_var),
            (i18n.t("filament.price"), self._price_var),
        ]

        for row, (label, var) in enumerate(fields):
            ttk.Label(outer, text=label).grid(
                row=row, column=0, sticky=tk.W, pady=3, padx=(0, 8)
            )
            ttk.Entry(outer, textvariable=var, width=28).grid(
                row=row, column=1, sticky=tk.EW, pady=3
            )

        outer.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, sticky=tk.E, pady=(12, 0))

        ttk.Button(btn_frame, text=i18n.t("filament.save"), command=self._save).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_frame, text=i18n.t("filament.cancel"), command=self.destroy).pack(
            side=tk.LEFT
        )

    def _save(self) -> None:
        """Valideer en sla het profiel op."""
        i18n = get_i18n()
        name = self._name_var.get().strip()
        brand = self._brand_var.get().strip()
        color = self._color_var.get().strip()
        material = self._material_var.get().strip()

        if not name:
            messagebox.showwarning("Validatie", i18n.t("filament.validation_name"), parent=self)
            return

        try:
            weight = float(self._weight_var.get())
            if weight <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Validatie", i18n.t("filament.validation_weight"), parent=self
            )
            return

        try:
            price = float(self._price_var.get())
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Validatie", i18n.t("filament.validation_price"), parent=self
            )
            return

        if self._profile:
            # Bewerk bestaand profiel
            self._profile.name = name
            self._profile.brand = brand
            self._profile.color_hex = color
            self._profile.material_type = material
            self._profile.spool_weight_grams = weight
            self._profile.purchase_price_eur = price
            self.result = self._profile
        else:
            # Nieuw profiel
            self.result = FilamentProfile(
                name=name,
                brand=brand,
                color_hex=color,
                material_type=material,
                spool_weight_grams=weight,
                purchase_price_eur=price,
            )

        self.destroy()


# ---------------------------------------------------------------------------
# FilamentDialog
# ---------------------------------------------------------------------------

class FilamentDialog(tk.Toplevel):
    """Modaal venster voor het beheren van filamentprofielen.

    Toont een lijst van bestaande profielen met knoppen voor toevoegen,
    bewerken en verwijderen.
    """

    def __init__(
        self,
        parent: tk.Tk,
        settings_manager: SettingsManager,
    ) -> None:
        super().__init__(parent)
        self._sm = settings_manager
        self._parent = parent

        self.title(get_i18n().t("filament.title"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh_list()

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
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        # Linker paneel: listbox
        list_frame = ttk.Frame(outer)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(
            list_frame,
            width=40,
            height=14,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
        )
        scrollbar.config(command=self._listbox.yview)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Rechter paneel: knoppen
        btn_frame = ttk.Frame(outer, padding=(12, 0, 0, 0))
        btn_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Button(btn_frame, text=i18n.t("filament.add"), command=self._add, width=12).pack(
            pady=(0, 6)
        )
        ttk.Button(btn_frame, text=i18n.t("filament.edit"), command=self._edit, width=12).pack(
            pady=(0, 6)
        )
        ttk.Button(btn_frame, text=i18n.t("filament.delete"), command=self._delete, width=12).pack()

    # ------------------------------------------------------------------
    # Lijst beheer
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        """Ververs de listbox met de huidige filamentprofielen."""
        self._listbox.delete(0, tk.END)
        profiles = self._sm.get().filament_profiles
        for p in profiles:
            self._listbox.insert(tk.END, f"{p.name}  [{p.material_type}]")

    def _selected_index(self) -> int | None:
        """Geef de geselecteerde index terug, of None als niets geselecteerd."""
        sel = self._listbox.curselection()
        return sel[0] if sel else None

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------

    def _add(self) -> None:
        """Open het formulier voor een nieuw profiel."""
        dlg = _FilamentFormDialog(self)
        if dlg.result:
            profiles = list(self._sm.get().filament_profiles)
            profiles.append(dlg.result)
            self._sm.update(filament_profiles=profiles)
            self._refresh_list()

    def _edit(self) -> None:
        """Open het formulier voor het bewerken van het geselecteerde profiel."""
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo(get_i18n().t("filament.edit"), get_i18n().t("filament.select_first"), parent=self)
            return

        profiles = list(self._sm.get().filament_profiles)
        profile = profiles[idx]
        dlg = _FilamentFormDialog(self, profile=profile)
        if dlg.result:
            profiles[idx] = dlg.result
            self._sm.update(filament_profiles=profiles)
            self._refresh_list()

    def _delete(self) -> None:
        """Verwijder het geselecteerde profiel."""
        i18n = get_i18n()
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo(i18n.t("filament.delete"), i18n.t("filament.select_first"), parent=self)
            return

        profiles = list(self._sm.get().filament_profiles)
        profile = profiles[idx]
        confirm = messagebox.askyesno(
            i18n.t("filament.delete"),
            i18n.t("filament.confirm_delete", name=profile.name),
            parent=self,
        )
        if confirm:
            profiles.pop(idx)
            self._sm.update(filament_profiles=profiles)
            self._refresh_list()
