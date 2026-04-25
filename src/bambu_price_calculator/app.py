"""App — Hoofd-applicatieklasse voor de Bambu Price Calculator.

Initialiseert en verbindt alle componenten: SettingsManager, I18nManager,
GcodeWatcher, PriceCalculator, UpdateManager, MainWindow en TrayIcon.
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

from bambu_price_calculator.core.gcode_parser import ParseResult, FilamentMeta
from bambu_price_calculator.core.gcode_watcher import GcodeWatcher
from bambu_price_calculator.core.i18n_manager import I18nManager
from bambu_price_calculator.core.price_calculator import CalculationResult, PriceCalculator
from bambu_price_calculator.core.settings_manager import (
    FilamentProfile,
    HistoryRecord,
    SettingsManager,
)
from bambu_price_calculator.core.update_manager import UpdateManager
from bambu_price_calculator.ui.filament_dialog import FilamentDialog, show_unknown_filament_dialog
from bambu_price_calculator.ui.history_view import HistoryView
from bambu_price_calculator.ui.main_window import MainWindow
from bambu_price_calculator.ui.settings_dialog import SettingsDialog
from bambu_price_calculator.ui.tray_icon import TrayIcon

logger = logging.getLogger(__name__)

_THEME_CHECK_INTERVAL_MS = 5000  # 5 seconden


class App:
    """Hoofd-applicatieklasse die alle componenten initialiseert en verbindt."""

    def __init__(self) -> None:
        # 1. SettingsManager
        self._sm = SettingsManager()

        # 2. I18nManager — laad taal uit settings
        settings = self._sm.get()
        self._i18n = I18nManager()
        lang = settings.language
        if lang and lang != "auto":
            self._i18n.load(lang)

        # 3. Tkinter root
        self._root = tk.Tk()

        # 4. MainWindow
        self._main_window = MainWindow(self._root, self._i18n, self._sm)

        # 5. TrayIcon
        self._tray = TrayIcon(self._root)

        # 6. GcodeWatcher
        self._watcher = GcodeWatcher()
        self._watcher_active = False

        # 7. PriceCalculator
        self._calculator = PriceCalculator()

        # 8. UpdateManager
        self._update_manager = UpdateManager("0.1.0", "joyvanacker", "PandaPrice")

        # Laatste berekeningsresultaat (voor herberekening bij instellingswijziging)
        self._last_parse_result: ParseResult | None = None

        # Huidig actief thema (voor systeemthema-detectie)
        self._current_sv_theme: str = self._main_window._resolve_sv_theme(settings.theme)

        # Verbindingen instellen
        self._connect_callbacks()

        # Venster-sluit protocol: minimaliseer naar tray (taak 11.3)
        self._root.protocol("WM_DELETE_WINDOW", self._hide_window)

    # ------------------------------------------------------------------
    # Verbindingen
    # ------------------------------------------------------------------

    def _connect_callbacks(self) -> None:
        """Verbind alle callbacks tussen componenten."""
        # GcodeWatcher callbacks
        self._watcher.on_parse_result = self._on_parse_result
        self._watcher.on_error = self._on_watcher_error

        # MainWindow callbacks
        self._main_window.on_toggle_watch = self._toggle_watch
        self._main_window.on_open_settings = self._open_settings
        self._main_window.on_open_filaments = self._open_filaments
        self._main_window.on_open_history = self._open_history
        self._main_window.on_check_update = self._check_update
        self._main_window.on_settings_changed = self._on_settings_changed
        self._main_window.on_quit = self._quit

        # TrayIcon callbacks
        self._tray.on_show = self._show_window
        self._tray.on_quit = self._quit

    # ------------------------------------------------------------------
    # run()
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start de applicatie: tray, watcher, update check en event loop."""
        # Start tray-icoon
        self._tray.start()

        # Start GcodeWatcher als pad geconfigureerd is
        settings = self._sm.get()
        if settings.gcode_watch_path:
            self._watcher.start(settings.gcode_watch_path)
            self._watcher_active = True
            self._main_window.set_watch_active(True)
            self._main_window.set_status(f"Bewaking actief: {settings.gcode_watch_path}")

        # Start update check asynchroon
        threading.Thread(
            target=self._async_check_update,
            daemon=True,
            name="UpdateCheckThread",
        ).start()

        # Start achtergrondthread voor systeemthema-detectie (taak 11.2)
        if settings.theme == "system":
            self._start_theme_watcher()

        # Start Tkinter event loop
        self._root.mainloop()

    # ------------------------------------------------------------------
    # Thema-ondersteuning (taak 11.2)
    # ------------------------------------------------------------------

    def _start_theme_watcher(self) -> None:
        """Start een periodieke controle van het Windows-systeemthema."""
        self._root.after(_THEME_CHECK_INTERVAL_MS, self._check_system_theme)

    def _check_system_theme(self) -> None:
        """Controleer het Windows-systeemthema en pas het toe als het gewijzigd is."""
        settings = self._sm.get()
        if settings.theme != "system":
            return  # Alleen actief in systeem-modus

        new_theme = MainWindow._detect_system_theme()
        if new_theme != self._current_sv_theme:
            self._current_sv_theme = new_theme
            self._main_window.apply_theme("system")

        # Plan de volgende controle
        self._root.after(_THEME_CHECK_INTERVAL_MS, self._check_system_theme)

    # ------------------------------------------------------------------
    # Venster minimaliseren naar tray (taak 11.3)
    # ------------------------------------------------------------------

    def _hide_window(self) -> None:
        """Verberg het venster (minimaliseer naar tray)."""
        self._root.withdraw()

    def _show_window(self) -> None:
        """Herstel het venster vanuit de tray."""
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    # ------------------------------------------------------------------
    # GcodeWatcher callbacks
    # ------------------------------------------------------------------

    def _on_parse_result(self, result: ParseResult) -> None:
        """Verwerk een parse-resultaat: bereken prijs per filament en update UI."""
        self._last_parse_result = result
        settings = self._sm.get()

        # Multi-filament: match elk filament afzonderlijk
        matched_profiles: list[FilamentProfile] = []
        weights = result.weight_per_filament

        for i, meta in enumerate(result.filament_metas):
            weight = weights[i] if i < len(weights) else 0.0
            if weight <= 0:
                continue  # dit filament wordt niet gebruikt

            profile = self._calculator.find_matching_profile(meta, settings.filament_profiles)
            if profile is None:
                profile = self._handle_unknown_filament_for_meta(meta)
                # Herlaad settings na eventueel nieuw profiel
                settings = self._sm.get()
            if profile is not None:
                matched_profiles.append(profile)
            else:
                # Gebruiker annuleerde — gebruik eerste beschikbaar profiel
                if settings.filament_profiles:
                    matched_profiles.append(settings.filament_profiles[0])

        # Fallback: als geen filamenten gematcht, gebruik eerste profiel
        if not matched_profiles:
            if result.filament_meta:
                profile = self._calculator.find_matching_profile(
                    result.filament_meta, settings.filament_profiles
                )
                if profile:
                    matched_profiles.append(profile)
            if not matched_profiles and settings.filament_profiles:
                matched_profiles.append(settings.filament_profiles[0])
            elif not matched_profiles:
                logger.warning("Geen filamentprofielen beschikbaar voor berekening.")
                return

        # Bereken totaalprijs: som van kosten per filament + bouw breakdown
        total_filament_cost = 0.0
        filament_breakdown: list[tuple[str, str, float, float]] = []
        used_weights: list[float] = []

        for i, profile in enumerate(matched_profiles):
            weight = weights[i] if i < len(weights) else 0.0
            if weight <= 0:
                continue
            used_weights.append(weight)
            prijs_per_gram = profile.purchase_price_eur / profile.spool_weight_grams
            slot_cost = weight * prijs_per_gram * (1 + settings.filament_margin_pct / 100)
            total_filament_cost += slot_cost
            filament_breakdown.append((
                f"{profile.brand} {profile.name}",
                profile.color_hex,
                weight,
                round(slot_cost, 2),
            ))

        uren = result.print_time_minutes / 60
        sale_price = round(
            (uren * settings.cost_per_hour + total_filament_cost) * (1 + settings.profit_margin_pct / 100),
            2,
        )

        # Maak een CalculationResult met het eerste profiel als referentie
        from bambu_price_calculator.core.price_calculator import CalculationResult
        from datetime import datetime

        calc_result = CalculationResult(
            filename=result.filename,
            timestamp=datetime.now().isoformat(),
            weight_grams=result.weight_grams,
            print_time_minutes=result.print_time_minutes,
            filament_profile=matched_profiles[0],
            cost_per_hour=settings.cost_per_hour,
            filament_margin_pct=settings.filament_margin_pct,
            profit_margin_pct=settings.profit_margin_pct,
            sale_price=sale_price,
        )

        self._root.after(0, lambda: self._update_ui(calc_result, filament_breakdown))

    def _handle_unknown_filament_for_meta(self, meta: FilamentMeta) -> FilamentProfile | None:
        """Maak een nieuw profiel aan voor een onbekend filament.

        Gebruikt profile_name, color_hex en cost_per_kg uit de gcode.
        Als cost_per_kg beschikbaar is, wordt het profiel automatisch aangemaakt.
        Controleert eerst of het profiel niet al eerder in deze sessie is aangemaakt.
        """
        # Herlaad settings — misschien is het profiel net aangemaakt door een ander slot
        settings = self._sm.get()
        profile = self._calculator.find_matching_profile(meta, settings.filament_profiles)
        if profile is not None:
            return profile

        # Gebruik de profielnaam uit de gcode, of maak een beschrijvende naam
        name = meta.profile_name or f"{meta.brand} {meta.material_type}".strip()
        if meta.color_hex:
            name = f"{name} ({meta.color_hex})"

        # Als Bambu Studio al een prijs per kg heeft, maak automatisch aan
        if meta.cost_per_kg > 0:
            new_profile = FilamentProfile(
                name=name,
                brand=meta.brand,
                material_type=meta.material_type,
                color_hex=meta.color_hex or "#FFFFFF",
                spool_weight_grams=1000.0,
                purchase_price_eur=meta.cost_per_kg,
                filament_id=meta.filament_id,
            )
            profiles = list(settings.filament_profiles)
            profiles.append(new_profile)
            self._sm.update(filament_profiles=profiles)
            return new_profile

        # Geen prijs beschikbaar: vraag de gebruiker
        price_holder: list[float | None] = [None]

        def _show_dialog() -> None:
            price = show_unknown_filament_dialog(
                self._root,
                filament_id=meta.filament_id,
                material_type=f"{name} ({meta.material_type})",
            )
            price_holder[0] = price

        event = threading.Event()

        def _run_and_signal() -> None:
            _show_dialog()
            event.set()

        self._root.after(0, _run_and_signal)
        event.wait(timeout=300)

        price = price_holder[0]
        if price is None:
            return None

        new_profile = FilamentProfile(
            name=name,
            brand=meta.brand,
            material_type=meta.material_type,
            color_hex=meta.color_hex or "#FFFFFF",
            spool_weight_grams=1000.0,
            purchase_price_eur=price,
            filament_id=meta.filament_id,
        )

        settings = self._sm.get()
        profiles = list(settings.filament_profiles)
        profiles.append(new_profile)
        self._sm.update(filament_profiles=profiles)

        return new_profile

    def _on_watcher_error(self, msg: str) -> None:
        """Update de statusbalk met een foutmelding van de watcher."""
        self._root.after(
            0,
            lambda: self._main_window.set_status(msg, is_error=True),
        )

    # ------------------------------------------------------------------
    # UI-acties
    # ------------------------------------------------------------------

    def _toggle_watch(self) -> None:
        """Toggle de GcodeWatcher aan/uit."""
        settings = self._sm.get()

        if self._watcher_active:
            self._watcher.stop()
            self._watcher_active = False
            self._main_window.set_watch_active(False)
            self._main_window.set_status("Bewaking gestopt.")
        else:
            path = settings.gcode_watch_path
            if not path:
                messagebox.showwarning(
                    "Geen map ingesteld",
                    "Stel eerst een gcode-map in via Bestand → Instellingen.",
                    parent=self._root,
                )
                return
            self._watcher.start(path)
            self._watcher_active = True
            self._main_window.set_watch_active(True)
            self._main_window.set_status(f"Bewaking actief: {path}")

    def _open_settings(self) -> None:
        """Open de instellingendialoog."""
        SettingsDialog(
            self._root,
            self._sm,
            on_path_changed=self._on_path_changed,
        )

    def _on_path_changed(self, new_path: str) -> None:
        """Herstart de watcher op het nieuwe pad."""
        if self._watcher_active:
            self._watcher.set_path(new_path)
            self._main_window.set_status(f"Bewaking actief: {new_path}")

    def _open_filaments(self) -> None:
        """Open de filamentprofiel-dialoog."""
        FilamentDialog(self._root, self._sm)

    def _open_history(self) -> None:
        """Open de geschiedenis-weergave."""
        HistoryView(self._root, self._sm)

    def _check_update(self) -> None:
        """Controleer op updates in een achtergrondthread."""
        threading.Thread(
            target=self._async_check_update,
            daemon=True,
            name="ManualUpdateCheckThread",
        ).start()

    def _async_check_update(self) -> None:
        """Voer de updatecontrole uit in een achtergrondthread."""
        try:
            update_info = self._update_manager.check_for_updates()
        except Exception as exc:
            logger.warning("Updatecontrole mislukt: %s", exc)
            return

        if update_info is None:
            return

        # Toon dialoog in main thread
        self._root.after(0, lambda: self._show_update_dialog(update_info))

    def _show_update_dialog(self, update_info: Any) -> None:
        """Toon een dialoog als er een update beschikbaar is."""
        from pathlib import Path
        import tempfile

        msg = (
            f"Versie {update_info.version} is beschikbaar.\n\n"
            f"{update_info.release_notes[:500] if update_info.release_notes else ''}\n\n"
            "Wil je nu updaten?"
        )
        if messagebox.askyesno("Update beschikbaar", msg, parent=self._root):
            if not update_info.asset_url:
                messagebox.showerror(
                    "Update mislukt",
                    "Geen installer-URL gevonden in de release.",
                    parent=self._root,
                )
                return
            threading.Thread(
                target=self._download_and_install,
                args=(update_info.asset_url,),
                daemon=True,
            ).start()

    def _download_and_install(self, asset_url: str) -> None:
        """Download en start de installer."""
        import tempfile
        from pathlib import Path

        dest_dir = Path(tempfile.mkdtemp())
        try:
            installer_path = self._update_manager.download_installer(asset_url, dest_dir)
            self._update_manager.launch_installer(installer_path)
        except Exception as exc:
            self._root.after(
                0,
                lambda: messagebox.showerror(
                    "Download mislukt",
                    f"De installer kon niet worden gedownload:\n{exc}\n\n"
                    "Probeer het later opnieuw.",
                    parent=self._root,
                ),
            )

    def _on_settings_changed(self, field: str, value: float) -> None:
        """Herbereken als een prijs-gerelateerd veld gewijzigd is."""
        price_fields = {"cost_per_hour", "filament_margin_pct", "profit_margin_pct"}
        if field in price_fields and self._last_parse_result is not None:
            self._on_parse_result(self._last_parse_result)

    # ------------------------------------------------------------------
    # UI update helpers
    # ------------------------------------------------------------------

    def _update_ui(
        self,
        calc_result: CalculationResult,
        filament_breakdown: list[tuple[str, str, float, float]] | None = None,
    ) -> None:
        """Update de MainWindow met het berekeningsresultaat en sla op in history."""
        self._main_window.update_result(calc_result)
        if filament_breakdown:
            self._main_window.update_filament_breakdown(filament_breakdown)

        # Voeg toe aan history
        record = HistoryRecord(
            timestamp=calc_result.timestamp,
            filename=calc_result.filename,
            weight_grams=calc_result.weight_grams,
            print_time_minutes=calc_result.print_time_minutes,
            filament_profile_id=calc_result.filament_profile.id,
            sale_price=calc_result.sale_price,
        )
        self._sm.append_history(record)

        # Toon notificatie als venster verborgen is
        if not self._root.winfo_viewable():
            self._tray.show_notification(
                title="Bambu Price Calculator",
                message=f"{calc_result.filename}: € {calc_result.sale_price:.2f}",
            )

    # ------------------------------------------------------------------
    # Afsluiten
    # ------------------------------------------------------------------

    def _quit(self) -> None:
        """Stop alle componenten en sluit de applicatie."""
        self._watcher.stop()
        self._tray.stop()
        try:
            self._root.destroy()
        except Exception:
            pass
