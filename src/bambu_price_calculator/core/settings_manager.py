"""Settings Manager voor PandaPrice.

Beheert persistentie van instellingen, filamentprofielen en berekeningsgeschiedenis
via een JSON-bestand in %APPDATA%\\BambuPriceCalculator\\settings.json.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data modellen
# ---------------------------------------------------------------------------

@dataclass
class FilamentProfile:
    """Een filamentprofiel met merk, kleur, materiaal en prijsinformatie."""

    name: str
    brand: str
    material_type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    color_hex: str = "#FFFFFF"
    spool_weight_grams: float = 1000.0
    purchase_price_eur: float = 25.0
    filament_id: str = ""


@dataclass
class HistoryRecord:
    """Een record in de berekeningsgeschiedenis."""

    timestamp: str
    filename: str
    weight_grams: float
    print_time_minutes: float
    filament_profile_id: str
    sale_price: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Settings:
    """Alle applicatie-instellingen."""

    version: int = 1
    gcode_watch_path: str = ""
    # Eenvoudige modus
    cost_per_hour: float = 2.50
    filament_margin_pct: float = 10.0
    profit_margin_pct: float = 20.0
    use_advanced_pricing: bool = False
    # Geavanceerde modus — machinekosten
    energy_watt: float = 120.0          # stroomverbruik printer in Watt
    energy_price_kwh: float = 0.25      # elektriciteitsprijs €/kWh
    machine_price: float = 1000.0       # aanschafprijs printer €
    machine_lifespan_hours: float = 5000.0  # verwachte levensduur in uren
    maintenance_per_hour: float = 0.10  # onderhoudskost €/uur
    # Geavanceerde modus — arbeidskosten
    prep_time_min: float = 5.0          # voorbewerkingstijd (min)
    post_time_min: float = 10.0         # nabewerkingstijd (min)
    labor_rate: float = 15.0            # uurtarief arbeid €/uur
    # Geavanceerde modus — vaste kosten per print
    setup_cost: float = 0.0             # opstartkosten per print €
    failure_rate_pct: float = 5.0       # faalpercentage %
    # Weergave
    theme: str = "system"
    language: str = "auto"
    currency_symbol: str = "€"
    filament_profiles: list[FilamentProfile] = field(default_factory=list)
    history: list[HistoryRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hulpfuncties voor serialisatie
# ---------------------------------------------------------------------------

def _filament_profile_from_dict(data: dict[str, Any]) -> FilamentProfile:
    """Reconstrueer een FilamentProfile uit een dict, met standaardwaarden voor ontbrekende velden."""
    return FilamentProfile(
        id=str(data.get("id") or uuid.uuid4()),
        name=str(data.get("name") or ""),
        brand=str(data.get("brand") or ""),
        color_hex=str(data.get("color_hex") or "#FFFFFF"),
        material_type=str(data.get("material_type") or ""),
        spool_weight_grams=float(data.get("spool_weight_grams") or 1000.0),
        purchase_price_eur=float(data.get("purchase_price_eur") or 25.0),
        filament_id=str(data.get("filament_id") or ""),
    )


def _history_record_from_dict(data: dict[str, Any]) -> HistoryRecord:
    """Reconstrueer een HistoryRecord uit een dict, met standaardwaarden voor ontbrekende velden."""
    return HistoryRecord(
        id=str(data.get("id") or uuid.uuid4()),
        timestamp=str(data.get("timestamp") or ""),
        filename=str(data.get("filename") or ""),
        weight_grams=float(data.get("weight_grams") or 0.0),
        print_time_minutes=float(data.get("print_time_minutes") or 0.0),
        filament_profile_id=str(data.get("filament_profile_id") or ""),
        sale_price=float(data.get("sale_price") or 0.0),
    )


def _settings_from_dict(data: dict[str, Any]) -> Settings:
    """Reconstrueer een Settings object uit een dict, met standaardwaarden voor ontbrekende/ongeldige velden."""
    defaults = Settings()

    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _safe_str(value: Any, default: str) -> str:
        if value is None:
            return default
        return str(value)

    # Filamentprofielen reconstrueren
    raw_profiles = data.get("filament_profiles", [])
    if not isinstance(raw_profiles, list):
        raw_profiles = []
    filament_profiles = []
    for p in raw_profiles:
        if isinstance(p, dict):
            try:
                filament_profiles.append(_filament_profile_from_dict(p))
            except Exception:
                pass  # sla ongeldige profielen over

    # History records reconstrueren
    raw_history = data.get("history", [])
    if not isinstance(raw_history, list):
        raw_history = []
    history = []
    for h in raw_history:
        if isinstance(h, dict):
            try:
                history.append(_history_record_from_dict(h))
            except Exception:
                pass  # sla ongeldige records over

    return Settings(
        version=_safe_int(data.get("version"), defaults.version),
        gcode_watch_path=_safe_str(data.get("gcode_watch_path"), defaults.gcode_watch_path),
        cost_per_hour=_safe_float(data.get("cost_per_hour"), defaults.cost_per_hour),
        filament_margin_pct=_safe_float(data.get("filament_margin_pct"), defaults.filament_margin_pct),
        profit_margin_pct=_safe_float(data.get("profit_margin_pct"), defaults.profit_margin_pct),
        use_advanced_pricing=bool(data.get("use_advanced_pricing", defaults.use_advanced_pricing)),
        energy_watt=_safe_float(data.get("energy_watt"), defaults.energy_watt),
        energy_price_kwh=_safe_float(data.get("energy_price_kwh"), defaults.energy_price_kwh),
        machine_price=_safe_float(data.get("machine_price"), defaults.machine_price),
        machine_lifespan_hours=_safe_float(data.get("machine_lifespan_hours"), defaults.machine_lifespan_hours),
        maintenance_per_hour=_safe_float(data.get("maintenance_per_hour"), defaults.maintenance_per_hour),
        prep_time_min=_safe_float(data.get("prep_time_min"), defaults.prep_time_min),
        post_time_min=_safe_float(data.get("post_time_min"), defaults.post_time_min),
        labor_rate=_safe_float(data.get("labor_rate"), defaults.labor_rate),
        setup_cost=_safe_float(data.get("setup_cost"), defaults.setup_cost),
        failure_rate_pct=_safe_float(data.get("failure_rate_pct"), defaults.failure_rate_pct),
        theme=_safe_str(data.get("theme"), defaults.theme),
        language=_safe_str(data.get("language"), defaults.language),
        currency_symbol=_safe_str(data.get("currency_symbol"), defaults.currency_symbol),
        filament_profiles=filament_profiles,
        history=history,
    )


# ---------------------------------------------------------------------------
# SettingsManager
# ---------------------------------------------------------------------------

class SettingsManager:
    """Beheert het laden, opslaan en bijwerken van applicatie-instellingen.

    Instellingen worden opgeslagen in:
        %APPDATA%\\BambuPriceCalculator\\settings.json

    Schrijven is gedebounced: wijzigingen worden maximaal 1 seconde uitgesteld
    zodat snelle opeenvolgende updates worden samengevoegd tot één schrijfactie.
    """

    _SETTINGS_DIR_NAME = "BambuPriceCalculator"
    _SETTINGS_FILE_NAME = "settings.json"
    _DEBOUNCE_SECONDS = 1.0
    _MAX_HISTORY = 500

    # Bekende Bambu Studio gcode-paden
    _BAMBU_PATHS = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "bamboo_model"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Bambu Studio", "cache"),
    ]

    def __init__(self) -> None:
        self._settings_path = self._resolve_settings_path()
        self._settings: Settings = self.load()
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Pad-resolutie
    # ------------------------------------------------------------------

    def _resolve_settings_path(self) -> Path:
        """Geef het volledige pad naar het settings.json bestand terug."""
        appdata = os.environ.get("APPDATA", str(Path.home()))
        settings_dir = Path(appdata) / self._SETTINGS_DIR_NAME
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / self._SETTINGS_FILE_NAME

    # ------------------------------------------------------------------
    # Publieke interface
    # ------------------------------------------------------------------

    def load(self) -> Settings:
        """Lees het JSON-configuratiebestand en geef een Settings object terug.

        - Ontbrekende of ongeldige velden worden vervangen door standaardwaarden.
        - Bij een JSONDecodeError wordt het corrupte bestand hernoemd naar
          settings.json.bak en een nieuw bestand met standaardwaarden aangemaakt.
        - Als het bestand niet bestaat, wordt een nieuw bestand aangemaakt.
        """
        path = self._resolve_settings_path()

        if not path.exists():
            settings = Settings()
            # Detecteer Bambu Studio pad bij eerste opstart
            if not settings.gcode_watch_path:
                detected = self._detect_bambu_paths()
                if detected:
                    settings.gcode_watch_path = detected
            self._write_to_disk(settings, path)
            self._settings = settings
            return settings

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise json.JSONDecodeError("Root is not an object", raw, 0)
            settings = _settings_from_dict(data)
        except json.JSONDecodeError:
            # Hernoem corrupt bestand en herstel standaardwaarden
            bak_path = path.with_suffix(".json.bak")
            try:
                path.rename(bak_path)
            except OSError:
                pass
            settings = Settings()
            detected = self._detect_bambu_paths()
            if detected:
                settings.gcode_watch_path = detected
            self._write_to_disk(settings, path)

        self._settings = settings
        return settings

    def save(self, settings: Settings) -> None:
        """Sla de instellingen op met een debounce van 1 seconde.

        Snelle opeenvolgende aanroepen worden samengevoegd: alleen de laatste
        staat van `settings` wordt geschreven.
        """
        with self._lock:
            self._settings = settings
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                self._DEBOUNCE_SECONDS,
                self._flush,
            )
            self._timer.daemon = True
            self._timer.start()

    def get(self) -> Settings:
        """Geef de huidige in-memory instellingen terug."""
        return self._settings

    def update(self, **kwargs: Any) -> None:
        """Update één of meer velden van de huidige instellingen en sla op.

        Voorbeeld::

            manager.update(cost_per_hour=3.0, theme="dark")
        """
        settings = self._settings
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        self.save(settings)

    def append_history(self, record: HistoryRecord) -> None:
        """Voeg een record toe aan het begin van de geschiedenis.

        Als de lijst meer dan 500 records bevat, wordt het oudste record
        (het laatste element) verwijderd.
        """
        settings = self._settings
        settings.history.insert(0, record)
        if len(settings.history) > self._MAX_HISTORY:
            settings.history = settings.history[: self._MAX_HISTORY]
        self.save(settings)

    # ------------------------------------------------------------------
    # Interne hulpmethoden
    # ------------------------------------------------------------------

    def _flush(self) -> None:
        """Schrijf de huidige in-memory instellingen naar schijf (debounce callback)."""
        with self._lock:
            self._write_to_disk(self._settings, self._resolve_settings_path())
            self._timer = None

    def _write_to_disk(self, settings: Settings, path: Path) -> None:
        """Serialiseer en schrijf het Settings object naar het opgegeven pad."""
        data = asdict(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _detect_bambu_paths(self) -> str:
        """Controleer bekende Bambu Studio paden en geef het eerste gevonden pad terug.

        Gecontroleerde paden:
        - %LOCALAPPDATA%\\Temp\\bamboo_model
        - %LOCALAPPDATA%\\Bambu Studio\\cache

        Geeft een lege string terug als geen pad gevonden wordt.
        """
        for candidate in self._BAMBU_PATHS:
            if candidate and Path(candidate).exists():
                return candidate
        return ""
