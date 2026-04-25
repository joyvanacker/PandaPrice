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
        """Wacht kort op bestandsstabiliteit en parseert het gcode-bestand."""
        time.sleep(_FILE_SETTLE_DELAY)
        try:
            result = self._parser.parse(filepath)
        except ParseError as exc:
            logger.error("Fout bij parsen van %s: %s", filepath, exc)
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("Onverwachte fout bij parsen van %s: %s", filepath, exc)
            return

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

        Maakt een PollingObserver aan (geschikt voor netwerk- en tijdelijke mappen)
        met een polling-interval van 1 seconde. De observer draait in een daemon-thread.

        Args:
            path: Pad naar de te bewaken map.
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
