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


@dataclass
class ParseResult:
    filename: str
    weight_grams: float
    print_time_minutes: float
    filament_meta: FilamentMeta | None
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
_RE_TIME_MODEL = re.compile(
    r";\s*model printing time\s*[=:]\s*(.+)", re.IGNORECASE
)
_RE_TIME_PARTS = re.compile(
    r"(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?", re.IGNORECASE
)

_RE_FILAMENT_ID = re.compile(r";\s*filament_id\s*=\s*(.+)", re.IGNORECASE)
_RE_MATERIAL_TYPE = re.compile(r";\s*filament_type\s*=\s*(.+)", re.IGNORECASE)
_RE_COLOR_HEX = re.compile(r";\s*filament_colour\s*=\s*(.+)", re.IGNORECASE)
_RE_BRAND = re.compile(r";\s*filament_vendor\s*=\s*(.+)", re.IGNORECASE)

_HEADER_LINES = 200


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
        weight_grams = self._extract_weight(lines, raw_metadata)
        print_time_minutes = self._extract_time(lines, raw_metadata)
        filament_meta = self._extract_filament_meta(lines, raw_metadata)

        if not weight_grams:
            raise ParseError(
                f"Geen geldig filamentgewicht gevonden in: {path.name}"
            )
        if not print_time_minutes:
            raise ParseError(
                f"Geen geldige printtijd gevonden in: {path.name}"
            )

        return ParseResult(
            filename=path.name,
            weight_grams=weight_grams,
            print_time_minutes=print_time_minutes,
            filament_meta=filament_meta,
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
    ) -> float:
        """Extraheert het totale filamentgewicht in gram."""
        for line in lines:
            # Formaat: "; filament used [g] = 12.34"
            m = _RE_WEIGHT_SINGLE.search(line)
            if m:
                raw["filament used [g]"] = m.group(1).strip()
                return float(m.group(1))

            # Formaat: "; total filament weight [g] : 12.34, 5.67"
            m = _RE_WEIGHT_MULTI.search(line)
            if m:
                raw["total filament weight [g]"] = m.group(1).strip()
                values = re.findall(r"[\d.]+", m.group(1))
                return sum(float(v) for v in values)

        return 0.0

    def _extract_time(
        self, lines: list[str], raw: dict[str, str]
    ) -> float:
        """Extraheert de geschatte printtijd in minuten."""
        for line in lines:
            # Formaat: "; estimated printing time = 1h 23m 45s"
            m = _RE_TIME_ESTIMATED.search(line)
            if m:
                time_str = m.group(1).strip()
                raw["estimated printing time"] = time_str
                return _parse_time_to_minutes(time_str)

            # Formaat: "; model printing time: 1h 23m 45s"
            m = _RE_TIME_MODEL.search(line)
            if m:
                time_str = m.group(1).strip()
                raw["model printing time"] = time_str
                return _parse_time_to_minutes(time_str)

        return 0.0

    def _extract_filament_meta(
        self, lines: list[str], raw: dict[str, str]
    ) -> FilamentMeta | None:
        """Extraheert optionele filamentmetadata. Geeft None als niet aanwezig."""
        filament_id: str | None = None
        brand: str | None = None
        material_type: str | None = None
        color_hex: str | None = None

        for line in lines:
            if filament_id is None:
                m = _RE_FILAMENT_ID.search(line)
                if m:
                    filament_id = m.group(1).strip()
                    raw["filament_id"] = filament_id

            if material_type is None:
                m = _RE_MATERIAL_TYPE.search(line)
                if m:
                    material_type = m.group(1).strip()
                    raw["filament_type"] = material_type

            if color_hex is None:
                m = _RE_COLOR_HEX.search(line)
                if m:
                    color_hex = m.group(1).strip()
                    raw["filament_colour"] = color_hex

            if brand is None:
                m = _RE_BRAND.search(line)
                if m:
                    brand = m.group(1).strip()
                    raw["filament_vendor"] = brand

        if any(v is not None for v in (filament_id, brand, material_type, color_hex)):
            return FilamentMeta(
                filament_id=filament_id or "",
                brand=brand or "",
                material_type=material_type or "",
                color_hex=color_hex or "",
            )

        return None
