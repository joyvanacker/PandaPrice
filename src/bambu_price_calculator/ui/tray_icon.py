"""TrayIcon — Systeem-tray icoon voor de Bambu Price Calculator.

Gebruikt pystray voor het systeem-tray icoon met een groen Bambu-icoon.
Biedt contextmenu met "Calculator openen" en "Afsluiten".
"""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable

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
    """Maak een 64x64 PIL Image met een groene cirkel (Bambu-stijl)."""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = _hex_to_rgb(BAMBU_GREEN)
    margin = 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(r, g, b, 255),
    )
    return img


class TrayIcon:
    """Systeem-tray icoon voor de Bambu Price Calculator.

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

        menu = Menu(
            MenuItem(
                "Calculator openen",
                self._on_show_clicked,
                default=True,
            ),
            MenuItem(
                "Afsluiten",
                self._on_quit_clicked,
            ),
        )

        self._icon = pystray.Icon(
            name="BambuPriceCalculator",
            icon=image,
            title="Bambu Price Calculator",
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
        """Callback voor 'Calculator openen' in het contextmenu."""
        if self.on_show:
            self._root.after(0, self.on_show)

    def _on_quit_clicked(self, icon: object, item: object) -> None:
        """Callback voor 'Afsluiten' in het contextmenu."""
        self.stop()
        if self.on_quit:
            self._root.after(0, self.on_quit)
