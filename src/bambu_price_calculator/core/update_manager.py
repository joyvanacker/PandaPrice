"""
UpdateManager: controleert op nieuwe versies via GitHub Releases API
en beheert het downloaden en starten van de installer.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests
import semver


def _get_update_logger() -> logging.Logger:
    """Maak een logger aan die schrijft naar %APPDATA%\\BambuPriceCalculator\\update.log."""
    logger = logging.getLogger("bambu_price_calculator.update_manager")
    if logger.handlers:
        return logger

    log_dir = Path(os.environ.get("APPDATA", Path.home())) / "BambuPriceCalculator"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "update.log"

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1 * 1024 * 1024,  # 1 MB
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


_logger = _get_update_logger()


@dataclass
class UpdateInfo:
    """Informatie over een beschikbare update."""

    version: str        # bijv. "1.2.0"
    release_notes: str  # body van de GitHub release
    asset_url: str      # download URL van de installer


class UpdateManager:
    """Beheert auto-updates via GitHub Releases."""

    def __init__(
        self,
        current_version: str,
        github_owner: str,
        github_repo: str,
    ) -> None:
        self._current_version = current_version
        self._owner = github_owner
        self._repo = github_repo

    # ------------------------------------------------------------------
    # Publieke API
    # ------------------------------------------------------------------

    def check_for_updates(self) -> UpdateInfo | None:
        """
        Raadpleeg de GitHub Releases API en geef UpdateInfo terug als er
        een nieuwere versie beschikbaar is, anders None.

        Fouten worden stilzwijgend gelogd; er wordt nooit een exception
        naar de aanroeper gepropageerd.
        """
        url = (
            f"https://api.github.com/repos/{self._owner}/{self._repo}"
            "/releases/latest"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            _logger.warning("Updatecontrole mislukt: %s", exc)
            return None

        tag_name: str = data.get("tag_name", "")
        latest_version = tag_name.lstrip("v")

        try:
            is_newer = semver.compare(latest_version, self._current_version) > 0
        except ValueError as exc:
            _logger.warning(
                "Ongeldige semver-string '%s' of '%s': %s",
                latest_version,
                self._current_version,
                exc,
            )
            return None

        if not is_newer:
            _logger.info(
                "Geen update beschikbaar (huidig: %s, nieuwste: %s)",
                self._current_version,
                latest_version,
            )
            return None

        # Zoek de eerste .exe asset op als installer-URL
        asset_url = ""
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".exe"):
                asset_url = asset.get("browser_download_url", "")
                break

        _logger.info(
            "Update beschikbaar: %s → %s", self._current_version, latest_version
        )
        return UpdateInfo(
            version=latest_version,
            release_notes=data.get("body", ""),
            asset_url=asset_url,
        )

    def download_installer(self, asset_url: str, dest_dir: Path) -> Path:
        """
        Download de installer naar dest_dir/installer.exe via streaming.

        Verwijdert gedeeltelijk gedownloade bestanden bij een fout.
        Gooit requests.RequestException of IOError bij mislukking.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "installer.exe"

        try:
            with requests.get(asset_url, stream=True, timeout=60) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        except (requests.RequestException, IOError):
            # Verwijder gedeeltelijk gedownload bestand
            if dest_path.exists():
                try:
                    dest_path.unlink()
                except OSError:
                    pass
            raise

        _logger.info("Installer gedownload naar: %s", dest_path)
        return dest_path

    def launch_installer(self, installer_path: Path) -> None:
        """Start the installer with /SILENT flag and close the app.

        Uses a small batch script that waits for the app to exit before
        launching the installer, preventing file lock issues.
        """
        import tempfile
        import time

        _logger.info("Installer starten: %s", installer_path)

        # Create a batch script that waits for the app to exit, then runs the installer
        bat_content = f"""@echo off
timeout /t 3 /nobreak >nul
start "" "{installer_path}" /SILENT
"""
        bat_path = Path(tempfile.gettempdir()) / "pandaprice_update.bat"
        bat_path.write_text(bat_content, encoding="utf-8")

        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            close_fds=True,
            creationflags=(
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            if sys.platform == "win32"
            else 0,
        )
        sys.exit(0)
