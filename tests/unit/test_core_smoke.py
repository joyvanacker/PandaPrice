"""Smoke tests voor de core modules van PandaPrice.

Geen externe dependencies vereist (geen watchdog, geen requests, geen tkinter).
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Data modellen: FilamentProfile, HistoryRecord, Settings
# ---------------------------------------------------------------------------

class TestDataModels:
    def test_filament_profile_aanmaken(self):
        from bambu_price_calculator.core.settings_manager import FilamentProfile

        profile = FilamentProfile(name="PLA Wit", brand="Bambu Lab", material_type="PLA")
        assert profile.name == "PLA Wit"
        assert profile.brand == "Bambu Lab"
        assert profile.material_type == "PLA"
        assert profile.color_hex == "#FFFFFF"
        assert profile.spool_weight_grams == 1000.0
        assert profile.purchase_price_eur == 25.0
        assert profile.filament_id == ""
        # id moet een geldige UUID-string zijn
        assert uuid.UUID(profile.id)

    def test_history_record_aanmaken(self):
        from bambu_price_calculator.core.settings_manager import HistoryRecord

        record = HistoryRecord(
            timestamp="2024-01-01T12:00:00",
            filename="test.gcode",
            weight_grams=15.5,
            print_time_minutes=90.0,
            filament_profile_id=str(uuid.uuid4()),
            sale_price=3.50,
        )
        assert record.filename == "test.gcode"
        assert record.weight_grams == 15.5
        assert record.print_time_minutes == 90.0
        assert record.sale_price == 3.50
        assert uuid.UUID(record.id)

    def test_settings_aanmaken_met_standaardwaarden(self):
        from bambu_price_calculator.core.settings_manager import Settings

        settings = Settings()
        assert settings.version == 1
        assert settings.gcode_watch_path == ""
        assert settings.cost_per_hour == 2.50
        assert settings.filament_margin_pct == 10.0
        assert settings.profit_margin_pct == 20.0
        assert settings.theme == "system"
        assert settings.language == "auto"
        assert settings.filament_profiles == []
        assert settings.history == []


# ---------------------------------------------------------------------------
# GcodeParser: ParseError bij niet-bestaand bestand
# ---------------------------------------------------------------------------

class TestGcodeParser:
    def test_parse_error_bij_niet_bestaand_bestand(self):
        from bambu_price_calculator.core.gcode_parser import GcodeParser, ParseError

        parser = GcodeParser()
        with pytest.raises(ParseError):
            parser.parse("/niet/bestaand/bestand.gcode")

    def test_parse_error_bij_ontbrekend_gewicht(self, tmp_path):
        from bambu_price_calculator.core.gcode_parser import GcodeParser, ParseError

        gcode = tmp_path / "test.gcode"
        gcode.write_text(
            "; estimated printing time = 1h 23m 45s\n"
            "; filament_type = PLA\n",
            encoding="utf-8",
        )
        parser = GcodeParser()
        with pytest.raises(ParseError):
            parser.parse(str(gcode))

    def test_parse_error_bij_ontbrekende_printtijd(self, tmp_path):
        from bambu_price_calculator.core.gcode_parser import GcodeParser, ParseError

        gcode = tmp_path / "test.gcode"
        gcode.write_text(
            "; filament used [g] = 12.34\n"
            "; filament_type = PLA\n",
            encoding="utf-8",
        )
        parser = GcodeParser()
        with pytest.raises(ParseError):
            parser.parse(str(gcode))

    def test_parse_volledig_gcode_bestand(self, tmp_path):
        from bambu_price_calculator.core.gcode_parser import GcodeParser

        gcode = tmp_path / "print.gcode"
        gcode.write_text(
            "; filament used [g] = 15.50\n"
            "; estimated printing time = 1h 23m 45s\n"
            "; filament_ids = GFL99\n"
            "; filament_type = PLA\n"
            "; filament_colour = #FF5733\n"
            "; filament_vendor = Bambu Lab\n",
            encoding="utf-8",
        )
        parser = GcodeParser()
        result = parser.parse(str(gcode))
        assert result.weight_grams == 15.50
        # 1h 23m 45s = 60 + 23 + 45/60 = 83.75 minuten
        assert abs(result.print_time_minutes - 83.75) < 0.01
        assert result.filament_meta is not None
        assert result.filament_meta.filament_id == "GFL99"
        assert result.filament_meta.material_type == "PLA"


# ---------------------------------------------------------------------------
# PriceCalculator: formule en profiel-matching
# ---------------------------------------------------------------------------

class TestPriceCalculator:
    def _make_profile(self, purchase_price=25.0, spool_weight=1000.0):
        from bambu_price_calculator.core.settings_manager import FilamentProfile
        return FilamentProfile(
            name="PLA Wit",
            brand="Bambu Lab",
            material_type="PLA",
            purchase_price_eur=purchase_price,
            spool_weight_grams=spool_weight,
        )

    def _make_settings(self, cost_per_hour=2.50, filament_margin=10.0, profit_margin=20.0):
        from bambu_price_calculator.core.settings_manager import Settings
        return Settings(
            cost_per_hour=cost_per_hour,
            filament_margin_pct=filament_margin,
            profit_margin_pct=profit_margin,
        )

    def _make_parse_result(self, weight_grams=10.0, print_time_minutes=60.0):
        from bambu_price_calculator.core.gcode_parser import ParseResult
        return ParseResult(
            filename="test.gcode",
            weight_grams=weight_grams,
            print_time_minutes=print_time_minutes,
            filament_meta=None,
        )

    def test_prijsberekening_bekende_waarden(self):
        """
        Bekende waarden:
          uren = 60 / 60 = 1
          prijs_per_gram = 25 / 1000 = 0.025
          sale_price = (1 * 2.50 + 10 * 0.025 * 1.10) * 1.20
                     = (2.50 + 0.275) * 1.20
                     = 2.775 * 1.20
                     = 3.33
        """
        from bambu_price_calculator.core.price_calculator import PriceCalculator

        calc = PriceCalculator()
        result = calc.calculate(
            self._make_parse_result(weight_grams=10.0, print_time_minutes=60.0),
            self._make_profile(purchase_price=25.0, spool_weight=1000.0),
            self._make_settings(cost_per_hour=2.50, filament_margin=10.0, profit_margin=20.0),
        )
        assert result.sale_price == 3.33

    def test_prijsberekening_nul_marges(self):
        """
        Zonder marges:
          uren = 60 / 60 = 1
          prijs_per_gram = 25 / 1000 = 0.025
          sale_price = (1 * 2.50 + 10 * 0.025 * 1.0) * 1.0
                     = (2.50 + 0.25) * 1.0
                     = 2.75
        """
        from bambu_price_calculator.core.price_calculator import PriceCalculator

        calc = PriceCalculator()
        result = calc.calculate(
            self._make_parse_result(weight_grams=10.0, print_time_minutes=60.0),
            self._make_profile(purchase_price=25.0, spool_weight=1000.0),
            self._make_settings(cost_per_hour=2.50, filament_margin=0.0, profit_margin=0.0),
        )
        assert result.sale_price == 2.75

    def test_sale_price_afgerond_op_twee_decimalen(self):
        from bambu_price_calculator.core.price_calculator import PriceCalculator

        calc = PriceCalculator()
        result = calc.calculate(
            self._make_parse_result(weight_grams=7.0, print_time_minutes=45.0),
            self._make_profile(purchase_price=22.0, spool_weight=750.0),
            self._make_settings(cost_per_hour=3.0, filament_margin=15.0, profit_margin=25.0),
        )
        # Controleer dat het resultaat maximaal 2 decimalen heeft
        assert result.sale_price == round(result.sale_price, 2)

    def test_find_matching_profile_op_filament_id(self):
        from bambu_price_calculator.core.settings_manager import FilamentProfile
        from bambu_price_calculator.core.gcode_parser import FilamentMeta
        from bambu_price_calculator.core.price_calculator import PriceCalculator

        profiles = [
            FilamentProfile(name="PLA Wit", brand="Bambu Lab", material_type="PLA", filament_id="GFL99"),
            FilamentProfile(name="PETG Zwart", brand="Bambu Lab", material_type="PETG", filament_id="GFG00"),
        ]
        meta = FilamentMeta(filament_id="GFL99", brand="Bambu Lab", material_type="PLA", color_hex="#FFFFFF")

        calc = PriceCalculator()
        match = calc.find_matching_profile(meta, profiles)
        assert match is not None
        assert match.filament_id == "GFL99"

    def test_find_matching_profile_op_brand_en_material(self):
        from bambu_price_calculator.core.settings_manager import FilamentProfile
        from bambu_price_calculator.core.gcode_parser import FilamentMeta
        from bambu_price_calculator.core.price_calculator import PriceCalculator

        profiles = [
            FilamentProfile(name="PLA Wit", brand="Bambu Lab", material_type="PLA", filament_id=""),
        ]
        meta = FilamentMeta(filament_id="", brand="Bambu Lab", material_type="PLA", color_hex="#FFFFFF")

        calc = PriceCalculator()
        match = calc.find_matching_profile(meta, profiles)
        assert match is not None
        assert match.material_type == "PLA"

    def test_find_matching_profile_geen_match(self):
        from bambu_price_calculator.core.settings_manager import FilamentProfile
        from bambu_price_calculator.core.gcode_parser import FilamentMeta
        from bambu_price_calculator.core.price_calculator import PriceCalculator

        profiles = [
            FilamentProfile(name="PLA Wit", brand="Bambu Lab", material_type="PLA"),
        ]
        meta = FilamentMeta(filament_id="ONBEKEND", brand="Onbekend", material_type="ABS", color_hex="#000000")

        calc = PriceCalculator()
        match = calc.find_matching_profile(meta, profiles)
        assert match is None


# ---------------------------------------------------------------------------
# I18nManager: terugval op sleutelnaam
# ---------------------------------------------------------------------------

class TestI18nManager:
    def test_t_terugval_op_sleutelnaam(self):
        from bambu_price_calculator.core.i18n_manager import I18nManager

        manager = I18nManager()
        # Een sleutel die zeker niet bestaat
        key = "deze.sleutel.bestaat.zeker.niet.xyz"
        result = manager.t(key)
        assert result == key

    def test_t_bestaande_sleutel(self):
        from bambu_price_calculator.core.i18n_manager import I18nManager

        manager = I18nManager()
        manager.load("en")
        result = manager.t("app.title")
        assert result == "PandaPrice"

    def test_available_locales_bevat_en_en_nl(self):
        from bambu_price_calculator.core.i18n_manager import I18nManager

        manager = I18nManager()
        locales = manager.available_locales()
        assert "en" in locales
        assert "nl" in locales


# ---------------------------------------------------------------------------
# SettingsManager: _detect_bambu_paths geeft een string terug
# ---------------------------------------------------------------------------

class TestSettingsManager:
    def test_detect_bambu_paths_geeft_string_terug(self):
        from bambu_price_calculator.core.settings_manager import SettingsManager

        manager = SettingsManager.__new__(SettingsManager)
        result = manager._detect_bambu_paths()
        assert isinstance(result, str)

    def test_settings_manager_load_geeft_settings_terug(self, tmp_path, monkeypatch):
        """Test dat load() een Settings object teruggeeft, ook zonder bestaand bestand."""
        from bambu_price_calculator.core.settings_manager import SettingsManager, Settings

        # Stuur APPDATA naar een tijdelijke map zodat we geen echte AppData aanraken
        monkeypatch.setenv("APPDATA", str(tmp_path))
        manager = SettingsManager()
        settings = manager.get()
        assert isinstance(settings, Settings)

    def test_settings_manager_herstel_bij_corrupt_json(self, tmp_path, monkeypatch):
        """Test dat een corrupt JSON-bestand leidt tot standaardwaarden."""
        from bambu_price_calculator.core.settings_manager import SettingsManager, Settings

        monkeypatch.setenv("APPDATA", str(tmp_path))

        # Maak een corrupt settings.json aan
        settings_dir = tmp_path / "BambuPriceCalculator"
        settings_dir.mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text("GEEN GELDIG JSON {{{", encoding="utf-8")

        manager = SettingsManager()
        settings = manager.get()
        assert isinstance(settings, Settings)
        assert settings.version == 1
        assert settings.cost_per_hour == 2.50
