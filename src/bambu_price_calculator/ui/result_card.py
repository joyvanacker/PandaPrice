"""ResultCard — Compacte kaart met alle info van één berekening.

Toont thumbnail, modelnaam, prijs, filament breakdown en print details.
Meerdere cards worden gestapeld in de MainWindow.
"""

from __future__ import annotations

import io
import tkinter as tk
from tkinter import ttk

BAMBU_GREEN = "#00AE42"
TEXT_SECONDARY = "#888888"


class ResultCard(ttk.Frame):
    """Eén berekeningsresultaat als compacte card."""

    def __init__(
        self,
        parent: tk.Widget,
        price: str,
        time_str: str,
        weight_str: str,
        object_name: str = "",
        thumbnail_data: bytes = b"",
        filament_items: list[tuple[str, str, float, float]] | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent, padding=(10, 8))
        self._photo = None  # bewaar referentie

        # Top row: thumbnail + prijs info
        top = ttk.Frame(self)
        top.pack(fill=tk.X)

        # Thumbnail links
        if thumbnail_data:
            try:
                from PIL import Image, ImageTk
                img = Image.open(io.BytesIO(thumbnail_data))
                img.thumbnail((120, 120))
                self._photo = ImageTk.PhotoImage(img)
                ttk.Label(top, image=self._photo).pack(side=tk.LEFT, padx=(0, 10))
            except Exception:
                pass

        # Info rechts
        info = ttk.Frame(top)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        if object_name:
            ttk.Label(
                info, text=object_name,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor=tk.W)

        ttk.Label(
            info, text=f"{time_str}  |  {weight_str}",
            font=("Segoe UI", 9), foreground=TEXT_SECONDARY,
        ).pack(anchor=tk.W, pady=(2, 6))

        ttk.Label(
            info, text="TOTAALPRIJS",
            font=("Segoe UI", 10, "bold"), foreground=BAMBU_GREEN,
        ).pack(anchor=tk.W)

        ttk.Label(
            info, text=price,
            font=("Segoe UI", 28, "bold"),
        ).pack(anchor=tk.W, pady=(2, 0))

        # Filament breakdown
        if filament_items:
            ttk.Label(
                self, text="FILAMENTEN",
                font=("Segoe UI", 9, "bold"), foreground=TEXT_SECONDARY,
            ).pack(anchor=tk.W, pady=(8, 4))

            fil_frame = ttk.Frame(self)
            fil_frame.pack(fill=tk.X, pady=(6, 0))

            for name, color_hex, weight, cost in filament_items:
                row = ttk.Frame(fil_frame)
                row.pack(fill=tk.X, pady=1)

                canvas = tk.Canvas(row, width=16, height=16, highlightthickness=0, borderwidth=0)
                canvas.pack(side=tk.LEFT, padx=(0, 8), pady=1)
                canvas.create_oval(1, 1, 15, 15, fill=color_hex, outline=color_hex)

                ttk.Label(row, text=name, font=("Segoe UI", 9)).pack(side=tk.LEFT)
                ttk.Label(
                    row, text=f"€ {cost:.2f}",
                    font=("Segoe UI", 9), foreground=BAMBU_GREEN,
                ).pack(side=tk.RIGHT)
                ttk.Label(
                    row, text=f"{weight:.1f}g",
                    font=("Segoe UI", 9), foreground=TEXT_SECONDARY,
                ).pack(side=tk.RIGHT, padx=(0, 12))

        # Print details
        if details:
            ttk.Label(
                self, text="PRINT DETAILS",
                font=("Segoe UI", 9, "bold"), foreground=TEXT_SECONDARY,
            ).pack(anchor=tk.W, pady=(8, 4))

            detail_parts = [f"{v}" for k, v in details.items()]
            if detail_parts:
                ttk.Label(
                    self,
                    text="  •  ".join(detail_parts),
                    font=("Segoe UI", 7), foreground=TEXT_SECONDARY,
                ).pack(anchor=tk.W, pady=(4, 0))
