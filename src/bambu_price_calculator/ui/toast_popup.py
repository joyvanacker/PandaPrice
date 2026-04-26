"""Toast popup — Rijke notificatie met thumbnail, prijs en details.

Verschijnt rechtsonder op het scherm wanneer de app geminimaliseerd is
en er een nieuwe berekening binnenkomt. Verdwijnt automatisch na een
instelbare tijd of bij klikken.
"""

from __future__ import annotations

import io
import tkinter as tk
from typing import Callable

from bambu_price_calculator.core.i18n_manager import get_i18n

BAMBU_GREEN = "#00AE42"
_POPUP_WIDTH = 320
_POPUP_HEIGHT = 140
_DISPLAY_SECONDS = 8
_BG_DARK = "#2D2D30"
_BG_LIGHT = "#F5F5F5"
_FG_DARK = "#E0E0E0"
_FG_LIGHT = "#1A1A1A"
_FG_SEC_DARK = "#999999"
_FG_SEC_LIGHT = "#666666"


class ToastPopup:
    """Rijke toast-notificatie met thumbnail."""

    def __init__(
        self,
        price: str,
        time_str: str,
        weight_str: str,
        object_name: str = "",
        thumbnail_data: bytes = b"",
        on_click: Callable[[], None] | None = None,
        dark: bool = True,
    ) -> None:
        self._on_click = on_click
        self._win = win = tk.Toplevel()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.95)

        bg = _BG_DARK if dark else _BG_LIGHT
        fg = _FG_DARK if dark else _FG_LIGHT
        fg_sec = _FG_SEC_DARK if dark else _FG_SEC_LIGHT

        win.configure(bg=bg)

        # Positie: rechtsonder
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = screen_w - _POPUP_WIDTH - 16
        y = screen_h - _POPUP_HEIGHT - 60  # boven de taakbalk
        win.geometry(f"{_POPUP_WIDTH}x{_POPUP_HEIGHT}+{x}+{y}")

        # Bewaar referenties
        self._photo = None

        # Main frame
        frame = tk.Frame(win, bg=bg, padx=10, pady=8)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.bind("<Button-1>", self._clicked)

        # Top row: thumbnail + info
        top = tk.Frame(frame, bg=bg)
        top.pack(fill=tk.X)

        # Thumbnail
        if thumbnail_data:
            try:
                from PIL import Image, ImageTk
                img = Image.open(io.BytesIO(thumbnail_data))
                img.thumbnail((80, 80))
                self._photo = ImageTk.PhotoImage(img)
                thumb_lbl = tk.Label(top, image=self._photo, bg=bg, borderwidth=0)
                thumb_lbl.pack(side=tk.LEFT, padx=(0, 10))
                thumb_lbl.bind("<Button-1>", self._clicked)
            except Exception:
                pass

        # Info rechts
        info = tk.Frame(top, bg=bg)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # App naam
        tk.Label(
            info, text=get_i18n().t("app.title"), bg=bg, fg=BAMBU_GREEN,
            font=("Segoe UI", 8, "bold"), anchor=tk.W,
        ).pack(anchor=tk.W)

        # Object naam
        if object_name:
            tk.Label(
                info, text=object_name, bg=bg, fg=fg,
                font=("Segoe UI", 9, "bold"), anchor=tk.W,
            ).pack(anchor=tk.W, pady=(2, 0))

        # Prijs — groot en groen
        tk.Label(
            info, text=price, bg=bg, fg=BAMBU_GREEN,
            font=("Segoe UI", 18, "bold"), anchor=tk.W,
        ).pack(anchor=tk.W, pady=(2, 0))

        # Tijd + gewicht
        tk.Label(
            info, text=f"{time_str}  |  {weight_str}", bg=bg, fg=fg_sec,
            font=("Segoe UI", 8), anchor=tk.W,
        ).pack(anchor=tk.W)

        # Klik hint
        tk.Label(
            frame, text=get_i18n().t("toast.click_to_open"), bg=bg, fg=fg_sec,
            font=("Segoe UI", 7), anchor=tk.E,
        ).pack(anchor=tk.E)

        # Auto-sluiten
        win.after(_DISPLAY_SECONDS * 1000, self.close)

    def _clicked(self, event: tk.Event = None) -> None:
        self.close()
        if self._on_click:
            self._on_click()

    def close(self) -> None:
        try:
            self._win.destroy()
        except Exception:
            pass
