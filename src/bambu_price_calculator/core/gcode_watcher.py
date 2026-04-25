"""
GcodeWatcher: bewaakt een map op nieuwe of gewijzigde gcode-bestanden
en roept de GcodeParser aan bij detectie.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from bambu_price_calculator.core.gcode_parser import GcodeParser, ParseError, ParseResult

logger = logging.getLogger(__name__)

_POLLING_INTERVAL = 1  # seconden
_FILE_SETTLE_DELAY = 0.5  # seconden wachten na event voor bestandsstabiliteit


class _GcodeEventHandler(FileSystemEventHandler):
    """Reageert op bestandssysteem-events voor *.gcode bestanden."""

    def __init__(self, on_parse_result: Callable[[ParseResult], None] | None) -> None:
        super().__init__()
        self._parser = GcodeParser()
        self._on_parse_result = on_parse_result

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".gcode"):
            self._handle_gcode_event(event.src_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".gcode"):
            self._handle_gcode_event(event.src_path)

    def _handle_gcode_event(self, filepath: str) -> None:
        """Wacht kort op bestandsstabiliteit, parseert gcode en 3MF."""
        time.sleep(_FILE_SETTLE_DELAY)
        try:
            result = self._parser.parse(filepath)
        except ParseError as exc:
            logger.error("Fout bij parsen van %s: %s", filepath, exc)
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("Onverwachte fout bij parsen van %s: %s", filepath, exc)
            return

        # Probeer bijbehorend 3MF bestand te vinden en metadata te mergen
        try:
            from bambu_price_calculator.core.threemf_parser import (
                find_threemf_for_gcode,
                find_project_threemf,
                extract_model_name,
                parse_threemf,
            )
            threemf_path = find_threemf_for_gcode(filepath)
            if threemf_path:
                info = parse_threemf(threemf_path)
                if info:
                    result.thumbnail_data = info.thumbnail_data
                    result.object_name = info.object_name
                    result.printer_model_id = info.printer_model_id

            # Haal modelnaam uit de project-3MF (betere naam dan "Assembly")
            project_path = find_project_threemf(filepath)
            if project_path:
                model_name = extract_model_name(project_path)
                if model_name:
                    result.object_name = model_name
        except Exception as exc:  # noqa: BLE001
            logger.debug("3MF parsing overgeslagen: %s", exc)

        if self._on_parse_result is not None:
            self._on_parse_result(result)


class GcodeWatcher:
    """
    Bewaakt een map op nieuwe of gewijzigde gcode-bestanden via watchdog.

    Gebruik:
        watcher = GcodeWatcher()
        watcher.on_parse_result = lambda result: print(result)
        watcher.on_error = lambda msg: print("Fout:", msg)
        watcher.start("/pad/naar/gcode-map")
    """

    def __init__(self) -> None:
        self.on_parse_result: Callable[[ParseResult], None] | None = None
        self.on_error: Callable[[str], None] | None = None
        self._observer: PollingObserver | None = None

    def start(self, path: str) -> None:
        """
        Start de bestandssysteem-bewaking op het opgegeven pad.

        Scant eerst de map op het nieuwste bestaande gcode-bestand,
        en bewaakt daarna op nieuwe/gewijzigde bestanden.
        """
        self.stop()

        handler = _GcodeEventHandler(on_parse_result=self.on_parse_result)

        observer = PollingObserver(timeout=_POLLING_INTERVAL)
        try:
            observer.schedule(handler, path=path, recursive=True)
            observer.daemon = True
            observer.start()
        except (OSError, PermissionError) as exc:
            msg = f"Kan map niet bewaken '{path}': {exc}"
            logger.error(msg)
            if self.on_error is not None:
                self.on_error(msg)
            return

        self._observer = observer
        logger.info("GcodeWatcher gestart op: %s", path)

        # Initiële scan: verwerk het nieuwste bestaande gcode bestand
        self._scan_existing(path, handler)

    def stop(self) -> None:
        """Stopt de actieve observer als die draait."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Fout bij stoppen van observer: %s", exc)
            finally:
                self._observer = None
            logger.info("GcodeWatcher gestopt.")

    def set_path(self, path: str) -> None:
        """
        Stopt de huidige observer en start een nieuwe op het opgegeven pad.

        Args:
            path: Nieuw pad om te bewaken.
        """
        self.stop()
        self.start(path)

    def _scan_existing(self, path: str, handler: _GcodeEventHandler) -> None:
        """Zoek het nieuwste gcode bestand in de map en verwerk het."""
        import os

        newest_path: str | None = None
        newest_mtime: float = 0

        try:
            for dirpath, _, filenames in os.walk(path):
                for name in filenames:
                    if name.endswith(".gcode"):
                        full = os.path.join(dirpath, name)
                        try:
                            mt = os.path.getmtime(full)
                            if mt > newest_mtime:
                                newest_mtime = mt
                                newest_path = full
                        except OSError:
                            pass
        except OSError:
            return

        if newest_path:
            logger.info("Initiële scan: verwerk %s", newest_path)
            handler._handle_gcode_event(newest_path)
