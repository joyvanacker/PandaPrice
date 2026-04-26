"""I18n Manager — laadt taalbestanden en biedt vertalingen met terugval op Engels."""

from __future__ import annotations

import json
import locale
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Map van locales-map relatief aan dit bestand
_LOCALES_DIR = Path(__file__).parent.parent / "assets" / "locales"


class I18nManager:
    """Beheert meertalige teksten vanuit JSON-taalbestanden.

    Terugvalvolgorde:
      1. Geselecteerde taal
      2. Engels (en.json)
      3. De sleutel zelf
    """

    def __init__(self) -> None:
        self._translations: dict[str, str] = {}
        self._english: dict[str, str] = {}
        self._current_locale: str = "en"

        # Detecteer systeemtaal bij initialisatie
        detected = self._detect_system_locale()
        self.load(detected)

    # ------------------------------------------------------------------
    # Publieke API
    # ------------------------------------------------------------------

    def load(self, locale_code: str) -> None:
        """Laad het taalbestand voor *locale_code* (bijv. ``"nl"`` of ``"en"``).

        Als het bestand niet bestaat, wordt teruggevallen op Engels.
        Het Engelse bestand wordt altijd geladen als terugvalwaarden.
        """
        # Laad altijd Engels als terugval
        self._english = self._load_file("en")

        available = self.available_locales()
        if locale_code in available:
            self._translations = self._load_file(locale_code)
            self._current_locale = locale_code
        else:
            logger.warning(
                "Taalbestand voor '%s' niet gevonden, terugval op Engels.", locale_code
            )
            self._translations = self._english
            self._current_locale = "en"

    def t(self, key: str, **kwargs: object) -> str:
        """Geef de vertaling voor *key* terug.

        Ondersteunt format-placeholders via ``str.format(**kwargs)``.
        Terugvalvolgorde: geselecteerde taal → Engels → sleutel zelf.
        """
        raw = self._translations.get(key) or self._english.get(key)
        if raw is None:
            logger.debug("Vertaalsleutel '%s' niet gevonden.", key)
            return key
        if kwargs:
            try:
                return raw.format(**kwargs)
            except (KeyError, ValueError) as exc:
                logger.warning("Fout bij formatteren van sleutel '%s': %s", key, exc)
                return raw
        return raw

    def available_locales(self) -> list[str]:
        """Geef een gesorteerde lijst van beschikbare taalcodes terug."""
        if not _LOCALES_DIR.is_dir():
            return []
        return sorted(
            p.stem
            for p in _LOCALES_DIR.glob("*.json")
        )

    # ------------------------------------------------------------------
    # Interne hulpfuncties
    # ------------------------------------------------------------------

    def _load_file(self, locale_code: str) -> dict[str, str]:
        path = _LOCALES_DIR / f"{locale_code}.json"
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            return {k: str(v) for k, v in data.items()}
        except FileNotFoundError:
            logger.warning("Taalbestand niet gevonden: %s", path)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("Ongeldig JSON in taalbestand %s: %s", path, exc)
            return {}

    @staticmethod
    def _detect_system_locale() -> str:
        """Detecteer de systeemtaal en geef een twee-letter taalcode terug."""
        # Windows geeft bijv. "English_United Kingdom" of "Dutch_Netherlands"
        # We moeten dit mappen naar "en" of "nl"
        _LANG_MAP = {
            "english": "en", "dutch": "nl", "german": "de", "french": "fr",
            "spanish": "es", "italian": "it", "portuguese": "pt",
            "japanese": "ja", "chinese": "zh", "korean": "ko",
            "polish": "pl", "swedish": "sv", "danish": "da",
            "norwegian": "no", "finnish": "fi", "czech": "cs",
            "turkish": "tr", "russian": "ru",
        }
        try:
            lang = locale.getlocale()[0]
            if lang:
                # Probeer eerst split op _ (bijv. "en_GB" → "en")
                code = lang.split("_")[0].lower()
                # Als het een volledige naam is (bijv. "english"), map het
                if len(code) > 3:
                    code = _LANG_MAP.get(code, code[:2])
                return code
        except Exception:
            pass
        return "en"


_instance: I18nManager | None = None


def get_i18n() -> I18nManager:
    """Return the global I18nManager singleton, creating it if needed."""
    global _instance
    if _instance is None:
        _instance = I18nManager()
    return _instance
