"""
GcodeParser: extraheert filamentgewicht, printtijd en filamentmetadata
uit Bambu Studio gcode-bestanden.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


class ParseError(Exception):
    """Wordt gegooid als een gcode-bestand niet correct geparsed kan worden."""


@dataclass
class FilamentMeta:
    filament_id: str
    brand: str
    material_type: str
    color_hex: str
    profile_name: str = ""      # uit filament_settings_id
    cost_per_kg: float = 0.0    # uit filament_cost


@dataclass
class ParseResult:
    filename: str
    weight_grams: float          # totaal gewicht (som van alle filamenten)
    print_time_minutes: float
    filament_meta: FilamentMeta | None       # eerste filament (backward compat)
    filament_metas: list[FilamentMeta] = field(default_factory=list)  # alle filamenten
    weight_per_filament: list[float] = field(default_factory=list)    # gewicht per filament
    raw_metadata: dict[str, str] = field(default_factory=dict)


# Regex patronen voor metadata-extractie
_RE_WEIGHT_SINGLE = re.compile(
    r";\s*filament used \[g\]\s*=\s*([\d.]+)", re.IGNORECASE
)
_RE_WEIGHT_MULTI = re.compile(
    r";\s*total filament weight \[g\]\s*[=:]\s*([\d.,\s]+)", re.IGNORECASE
)
_RE_TIME_ESTIMATED = re.compile(
    r";\s*estimated printing time\s*=\s*(.+)", re.IGNORECASE
)
_RE_TIME_TOTAL_ESTIMATED = re.compile(
    r"total estimated time\s*[=:]\s*(.+?)(?:;|$)", re.IGNORECASE
)
_RE_TIME_MODEL = re.compile(
    r";\s*model printing time\s*[=:]\s*(.+?)(?:;|$)", re.IGNORECASE
)
_RE_TIME_PARTS = re.compile(
    r"(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?", re.IGNORECASE
)

_RE_FILAMENT_ID = re.compile(r";\s*filament_ids\s*=\s*(.+)", re.IGNORECASE)
_RE_MATERIAL_TYPE = re.compile(r";\s*filament_type\s*=\s*(.+)", re.IGNORECASE)
_RE_COLOR_HEX = re.compile(r";\s*filament_colour\s*=\s*(.+)", re.IGNORECASE)
_RE_BRAND = re.compile(r";\s*filament_vendor\s*=\s*(.+)", re.IGNORECASE)
_RE_SETTINGS_ID = re.compile(r";\s*filament_settings_id\s*=\s*(.+)", re.IGNORECASE)
_RE_FILAMENT_COST = re.compile(r";\s*filament_cost\s*=\s*([\d.,\s]+)", re.IGNORECASE)
_RE_ACTIVE_FILAMENTS = re.compile(r";\s*filament\s*[:=]\s*([\d,\s]+)", re.IGNORECASE)

_HEADER_LINES = 300


def _parse_time_to_minutes(time_str: str) -> float:
    """Converteert een tijdstring zoals '1h 23m 45s' naar minuten."""
    match = _RE_TIME_PARTS.search(time_str)
    if not match:
        return 0.0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 60 + minutes + seconds / 60


class GcodeParser:
    """Parseert Bambu Studio gcode-bestanden en extraheert metadata."""

    def parse(self, filepath: str) -> ParseResult:
        """
        Leest de header van een gcode-bestand en extraheert metadata.

        Args:
            filepath: Pad naar het gcode-bestand.

        Returns:
            ParseResult met gewicht, printtijd en optionele filamentmetadata.

        Raises:
            ParseError: Als het bestand niet gelezen kan worden, of als
                        weight_grams of print_time_minutes ontbreekt/nul is.
        """
        path = Path(filepath)
        if not path.exists():
            raise ParseError(f"Bestand niet gevonden: {filepath}")

        try:
            lines = self._read_header(path)
        except OSError as exc:
            raise ParseError(f"Kan bestand niet lezen: {filepath}: {exc}") from exc

        raw_metadata: dict[str, str] = {}
        weight_grams, weight_per_filament = self._extract_weight(lines, raw_metadata)
        print_time_minutes = self._extract_time(lines, raw_metadata)
        all_filament_metas = self._extract_filament_meta(lines, raw_metadata)
        active_slots = self._extract_active_slots(lines, raw_metadata)

        if not weight_grams:
            raise ParseError(
                f"Geen geldig filamentgewicht gevonden in: {path.name}"
            )
        if not print_time_minutes:
            raise ParseError(
                f"Geen geldige printtijd gevonden in: {path.name}"
            )

        # Map gewichten op de juiste metadata-slots
        # active_slots bevat 1-indexed slot nummers (bijv. [1, 2, 3])
        # weight_per_filament bevat gewichten in dezelfde volgorde als active_slots
        used_metas: list[FilamentMeta] = []
        used_weights: list[float] = []

        if active_slots and all_filament_metas:
            for i, slot_num in enumerate(active_slots):
                slot_idx = slot_num - 1  # 1-indexed → 0-indexed
                if slot_idx < len(all_filament_metas):
                    used_metas.append(all_filament_metas[slot_idx])
                weight = weight_per_filament[i] if i < len(weight_per_filament) else 0.0
                used_weights.append(weight)
        elif all_filament_metas:
            # Geen active_slots info: neem alle metas, map gewichten 1:1
            used_metas = all_filament_metas
            used_weights = weight_per_filament
        else:
            used_weights = weight_per_filament

        return ParseResult(
            filename=path.name,
            weight_grams=weight_grams,
            print_time_minutes=print_time_minutes,
            filament_meta=used_metas[0] if used_metas else None,
            filament_metas=used_metas,
            weight_per_filament=used_weights,
            raw_metadata=raw_metadata,
        )

    def _read_header(self, path: Path) -> list[str]:
        """Leest de eerste _HEADER_LINES regels van het bestand."""
        lines: list[str] = []
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= _HEADER_LINES:
                    break
                lines.append(line)
        return lines

    def _extract_weight(
        self, lines: list[str], raw: dict[str, str]
    ) -> tuple[float, list[float]]:
        """Extraheert het totale filamentgewicht en per-filament gewichten."""
        for line in lines:
            m = _RE_WEIGHT_SINGLE.search(line)
            if m:
                raw["filament used [g]"] = m.group(1).strip()
                w = float(m.group(1))
                return w, [w]

            m = _RE_WEIGHT_MULTI.search(line)
            if m:
                raw["total filament weight [g]"] = m.group(1).strip()
                values = [float(v) for v in re.findall(r"[\d.]+", m.group(1))]
                return sum(values), values

        return 0.0, []

    def _extract_time(
        self, lines: list[str], raw: dict[str, str]
    ) -> float:
        """Extraheert de totale geschatte printtijd in minuten.

        Prioriteit: total estimated time > estimated printing time > model printing time
        """
        for line in lines:
            # Prioriteit 1: "total estimated time: 3h 34m 34s"
            m = _RE_TIME_TOTAL_ESTIMATED.search(line)
            if m:
                time_str = m.group(1).strip()
                raw["total estimated time"] = time_str
                return _parse_time_to_minutes(time_str)

        for line in lines:
            # Prioriteit 2: "estimated printing time = 3h 34m 34s"
            m = _RE_TIME_ESTIMATED.search(line)
            if m:
                time_str = m.group(1).strip()
                raw["estimated printing time"] = time_str
                return _parse_time_to_minutes(time_str)

        for line in lines:
            # Prioriteit 3: "model printing time: 3h 28m 7s"
            m = _RE_TIME_MODEL.search(line)
            if m:
                time_str = m.group(1).strip()
                raw["model printing time"] = time_str
                return _parse_time_to_minutes(time_str)

        return 0.0

    def _extract_active_slots(
        self, lines: list[str], raw: dict[str, str]
    ) -> list[int]:
        """Extraheert de actieve filament-slots uit '; filament: 1,2,3'.

        Geeft een lijst van 1-indexed slot nummers terug.
        Leeg als de regel niet gevonden wordt.
        """
        for line in lines:
            m = _RE_ACTIVE_FILAMENTS.search(line)
            if m:
                raw_val = m.group(1).strip()
                raw["filament"] = raw_val
                try:
                    return [int(v.strip()) for v in raw_val.split(",") if v.strip()]
                except ValueError:
                    pass
        return []

    def _extract_filament_meta(
        self, lines: list[str], raw: dict[str, str]
    ) -> list[FilamentMeta]:
        """Extraheert filamentmetadata voor alle filamenten.

        Bambu Studio gebruikt puntkomma's als scheidingsteken voor meerdere filamenten,
        en komma's voor numerieke waarden zoals filament_cost.
        """
        filament_ids_raw: str | None = None
        brands_raw: str | None = None
        types_raw: str | None = None
        colors_raw: str | None = None
        settings_id_raw: str | None = None
        cost_raw: str | None = None

        for line in lines:
            if filament_ids_raw is None:
                m = _RE_FILAMENT_ID.search(line)
                if m:
                    filament_ids_raw = m.group(1).strip()
                    raw["filament_ids"] = filament_ids_raw

            if types_raw is None:
                m = _RE_MATERIAL_TYPE.search(line)
                if m:
                    types_raw = m.group(1).strip()
                    raw["filament_type"] = types_raw

            if colors_raw is None:
                m = _RE_COLOR_HEX.search(line)
                if m:
                    colors_raw = m.group(1).strip()
                    raw["filament_colour"] = colors_raw

            if brands_raw is None:
                m = _RE_BRAND.search(line)
                if m:
                    brands_raw = m.group(1).strip()
                    raw["filament_vendor"] = brands_raw

            if settings_id_raw is None:
                m = _RE_SETTINGS_ID.search(line)
                if m:
                    settings_id_raw = m.group(1).strip()
                    raw["filament_settings_id"] = settings_id_raw

            if cost_raw is None:
                m = _RE_FILAMENT_COST.search(line)
                if m:
                    cost_raw = m.group(1).strip()
                    raw["filament_cost"] = cost_raw

        if not any(v is not None for v in (filament_ids_raw, brands_raw, types_raw, colors_raw)):
            return []

        # Split op puntkomma (Bambu Studio multi-filament formaat)
        ids = [s.strip() for s in (filament_ids_raw or "").split(";")] if filament_ids_raw else []
        types = [s.strip() for s in (types_raw or "").split(";")] if types_raw else []
        colors = [s.strip() for s in (colors_raw or "").split(";")] if colors_raw else []
        brands = [s.strip() for s in (brands_raw or "").split(";")] if brands_raw else []

        # filament_settings_id: puntkomma-gescheiden, met aanhalingstekens
        names: list[str] = []
        if settings_id_raw:
            names = [s.strip().strip('"') for s in settings_id_raw.split(";")]

        # filament_cost: komma-gescheiden numerieke waarden
        costs: list[float] = []
        if cost_raw:
            for v in cost_raw.split(","):
                v = v.strip()
                try:
                    costs.append(float(v))
                except ValueError:
                    costs.append(0.0)

        # Bepaal het maximale aantal filamenten
        count = max(len(ids), len(types), len(colors), len(brands), len(names), 1)

        metas: list[FilamentMeta] = []
        for i in range(count):
            metas.append(FilamentMeta(
                filament_id=ids[i] if i < len(ids) else "",
                brand=brands[i] if i < len(brands) else "",
                material_type=types[i] if i < len(types) else "",
                color_hex=colors[i] if i < len(colors) else "",
                profile_name=names[i] if i < len(names) else "",
                cost_per_kg=costs[i] if i < len(costs) else 0.0,
            ))

        return metas
