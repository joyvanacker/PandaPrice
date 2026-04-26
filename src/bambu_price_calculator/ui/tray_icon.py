"""TrayIcon — Systeem-tray icoon voor PandaPrice.

Gebruikt pystray voor het systeem-tray icoon met een groen Bambu-icoon.
Biedt contextmenu met "Calculator openen" en "Afsluiten".
"""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable

from bambu_price_calculator.core.i18n_manager import get_i18n

BAMBU_GREEN = "#00ae42"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Zet een hex-kleurcode om naar een RGB-tuple."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _create_icon_image() -> "PIL.Image.Image":  # type: ignore[name-defined]
    """Laad het PandaPrice icoon, of maak een fallback."""
    from PIL import Image
    from pathlib import Path

    # Probeer het gegenereerde icoon te laden
    icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
    try:
        if icon_path.exists():
            img = Image.open(icon_path)
            img = img.resize((64, 64), Image.LANCZOS)
            return img.convert("RGBA")
    except Exception:
        pass

    # Fallback: groene cirkel
    from PIL import ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = _hex_to_rgb(BAMBU_GREEN)
    draw.ellipse([4, 4, size - 4, size - 4], fill=(r, g, b, 255))
    return img


class TrayIcon:
    """Systeem-tray icoon voor PandaPrice.

    Gebruik:
        tray = TrayIcon(root)
        tray.on_show = lambda: root.deiconify()
        tray.on_quit = lambda: root.destroy()
        tray.start()
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._icon: "pystray.Icon | None" = None  # type: ignore[name-defined]
        self._thread: threading.Thread | None = None

        self.on_show: Callable[[], None] | None = None
        self.on_open_settings: Callable[[], None] | None = None
        self.on_open_filaments: Callable[[], None] | None = None
        self.on_open_history: Callable[[], None] | None = None
        self.on_check_update: Callable[[], None] | None = None
        self.on_about: Callable[[], None] | None = None
        self.on_quit: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Publieke interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start het tray-icoon in een daemon-thread."""
        try:
            import pystray
            from pystray import MenuItem, Menu
        except ImportError:
            return  # pystray niet beschikbaar — stilzwijgend uitschakelen

        image = _create_icon_image()

        i18n = get_i18n()
        menu = Menu(
            MenuItem(
                i18n.t("tray.open"),
                self._on_show_clicked,
                default=True,
            ),
            Menu.SEPARATOR,
            MenuItem(
                i18n.t("tray.settings"),
                self._on_settings_clicked,
            ),
            MenuItem(
                i18n.t("tray.filaments"),
                self._on_filaments_clicked,
            ),
            MenuItem(
                i18n.t("tray.history"),
                self._on_history_clicked,
            ),
            Menu.SEPARATOR,
            MenuItem(
                i18n.t("tray.update"),
                self._on_update_clicked,
            ),
            MenuItem(
                i18n.t("tray.about"),
                self._on_about_clicked,
            ),
            Menu.SEPARATOR,
            MenuItem(
                i18n.t("tray.quit"),
                self._on_quit_clicked,
            ),
        )

        self._icon = pystray.Icon(
            name="BambuPriceCalculator",
            icon=image,
            title="PandaPrice",
            menu=menu,
        )

        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
            name="TrayIconThread",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop het tray-icoon."""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def show_notification(self, title: str, message: str) -> None:
        """Toon een notificatie via het tray-icoon.

        Args:
            title: De titel van de notificatie.
            message: De berichttekst.
        """
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Interne callbacks
    # ------------------------------------------------------------------

    def _on_show_clicked(self, icon: object, item: object) -> None:
        if self.on_show:
            self._root.after(0, self.on_show)

    def _on_settings_clicked(self, icon: object, item: object) -> None:
        if self.on_show:
            self._root.after(0, self.on_show)
        if self.on_open_settings:
            self._root.after(100, self.on_open_settings)

    def _on_filaments_clicked(self, icon: object, item: object) -> None:
        if self.on_show:
            self._root.after(0, self.on_show)
        if self.on_open_filaments:
            self._root.after(100, self.on_open_filaments)

    def _on_history_clicked(self, icon: object, item: object) -> None:
        if self.on_show:
            self._root.after(0, self.on_show)
        if self.on_open_history:
            self._root.after(100, self.on_open_history)

    def _on_update_clicked(self, icon: object, item: object) -> None:
        if self.on_check_update:
            self._root.after(0, self.on_check_update)

    def _on_about_clicked(self, icon: object, item: object) -> None:
        if self.on_show:
            self._root.after(0, self.on_show)
        if self.on_about:
            self._root.after(100, self.on_about)

    def _on_quit_clicked(self, icon: object, item: object) -> None:
        self.stop()
        if self.on_quit:
            self._root.after(0, self.on_quit)
