"""PriceCalculator voor PandaPrice.

Berekent de verkoopprijs van een 3D-print op basis van gewicht, printtijd,
filamentprofiel en instellingen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bambu_price_calculator.core.gcode_parser import FilamentMeta, ParseResult
from bambu_price_calculator.core.settings_manager import FilamentProfile, Settings


@dataclass
class CalculationResult:
    """Het resultaat van een prijsberekening."""

    filename: str
    timestamp: str  # ISO 8601
    weight_grams: float
    print_time_minutes: float
    filament_profile: FilamentProfile
    cost_per_hour: float
    filament_margin_pct: float
    profit_margin_pct: float
    sale_price: float  # berekend, afgerond op 2 decimalen


class PriceCalculator:
    """Berekent verkoopprijzen voor 3D-prints."""

    def calculate(
        self,
        parse_result: ParseResult,
        profile: FilamentProfile,
        settings: Settings,
    ) -> CalculationResult:
        """Bereken de verkoopprijs op basis van parse-resultaat, filamentprofiel en instellingen.

        Formule:
            uren = print_time_minutes / 60
            prijs_per_gram = purchase_price_eur / spool_weight_grams
            sale_price = round(
                (uren * cost_per_hour
                 + weight_grams * prijs_per_gram * (1 + filament_margin_pct / 100))
                * (1 + profit_margin_pct / 100),
                2
            )
        """
        uren = parse_result.print_time_minutes / 60
        prijs_per_gram = profile.purchase_price_eur / profile.spool_weight_grams
        sale_price = round(
            (
                uren * settings.cost_per_hour
                + parse_result.weight_grams * prijs_per_gram * (1 + settings.filament_margin_pct / 100)
            )
            * (1 + settings.profit_margin_pct / 100),
            2,
        )

        return CalculationResult(
            filename=parse_result.filename,
            timestamp=datetime.now().isoformat(),
            weight_grams=parse_result.weight_grams,
            print_time_minutes=parse_result.print_time_minutes,
            filament_profile=profile,
            cost_per_hour=settings.cost_per_hour,
            filament_margin_pct=settings.filament_margin_pct,
            profit_margin_pct=settings.profit_margin_pct,
            sale_price=sale_price,
        )

    def find_matching_profile(
        self,
        filament_meta: FilamentMeta,
        profiles: list[FilamentProfile],
    ) -> FilamentProfile | None:
        """Zoek een filamentprofiel dat overeenkomt met de gegeven filamentmetadata.

        Bij multicolor prints kan dezelfde filament_id (bijv. GFL01) meerdere keren
        voorkomen met verschillende kleuren. Daarom is filament_id + color_hex de
        primaire matchsleutel.

        Matchvolgorde:
        1. filament_id + color_hex (uniek per kleurvariant)
        2. profile_name + color_hex (filament_settings_id uit gcode)
        3. brand + material_type + color_hex
        4. filament_id alleen (fallback, zelfde materiaal andere kleur)
        5. brand + material_type alleen (fallback)

        Geeft None terug als geen match gevonden wordt.
        """
        meta_color = (filament_meta.color_hex or "").lower()
        meta_brand = filament_meta.brand.lower()
        meta_material = filament_meta.material_type.lower()

        # Stap 1: filament_id + color_hex — meest specifiek
        if filament_meta.filament_id and meta_color:
            for profile in profiles:
                if (
                    profile.filament_id == filament_meta.filament_id
                    and profile.color_hex.lower() == meta_color
                ):
                    return profile

        # Stap 2: profile_name + color_hex
        if filament_meta.profile_name and meta_color:
            meta_name = filament_meta.profile_name.lower()
            for profile in profiles:
                if (
                    profile.name.lower() == meta_name
                    and profile.color_hex.lower() == meta_color
                ):
                    return profile

        # Stap 3: brand + material_type + color_hex
        if meta_color:
            for profile in profiles:
                if (
                    profile.brand.lower() == meta_brand
                    and profile.material_type.lower() == meta_material
                    and profile.color_hex.lower() == meta_color
                ):
                    return profile

        # Stap 4: als er geen kleur beschikbaar is, match op filament_id alleen
        if not meta_color and filament_meta.filament_id:
            for profile in profiles:
                if profile.filament_id == filament_meta.filament_id:
                    return profile

        # Stap 5: als er geen kleur beschikbaar is, match op brand + material_type
        if not meta_color:
            for profile in profiles:
                if (
                    profile.brand.lower() == meta_brand
                    and profile.material_type.lower() == meta_material
                ):
                    return profile

        return None
