"""About dialoog voor PandaPrice."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from bambu_price_calculator.core.i18n_manager import get_i18n

BAMBU_GREEN = "#00AE42"


class AboutDialog(tk.Toplevel):
    """Modaal about-venster met app-info en icoon."""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        i18n = get_i18n()
        self.title(i18n.t("about.title"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)

        # Icoon
        self._photo = None
        try:
            from PIL import Image, ImageTk
            # Gebruik de hoge-resolutie PNG
            png_path = Path(__file__).parent.parent / "assets" / "icon_256.png"
            icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
            src = png_path if png_path.exists() else icon_path
            if src.exists():
                img = Image.open(src).resize((96, 96), Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                ttk.Label(frame, image=self._photo).pack(pady=(0, 12))
        except Exception:
            pass

        # Naam
        ttk.Label(
            frame, text="PandaPrice",
            font=("Segoe UI", 16, "bold"), foreground=BAMBU_GREEN,
        ).pack()

        # Versie
        try:
            from bambu_price_calculator import __version__
            version = __version__
        except Exception:
            version = "0.1.0"

        ttk.Label(
            frame, text=i18n.t("about.version", version=version),
            font=("Segoe UI", 9), foreground="#888",
        ).pack(pady=(2, 12))

        # Beschrijving
        ttk.Label(
            frame,
            text=i18n.t("about.description"),
            font=("Segoe UI", 9), justify=tk.CENTER,
        ).pack(pady=(0, 12))

        # GitHub link
        ttk.Label(
            frame,
            text="github.com/joyvanacker/PandaPrice",
            font=("Segoe UI", 8), foreground=BAMBU_GREEN, cursor="hand2",
        ).pack(pady=(0, 12))

        # Sluiten
        ttk.Button(frame, text=i18n.t("about.close"), command=self.destroy).pack()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        from bambu_price_calculator.ui.theme_utils import apply_dialog_titlebar
        apply_dialog_titlebar(self)

        self.wait_window(self)
