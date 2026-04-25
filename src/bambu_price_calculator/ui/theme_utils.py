"""Gedeelde thema-hulpfuncties voor dialoogvensters."""

from __future__ import annotations

import tkinter as tk

from bambu_price_calculator.platform.dwm import set_titlebar_color


def apply_dialog_titlebar(dialog: tk.Toplevel) -> None:
    """Pas de dark/light titelbalkkleur toe op een dialoogvenster.

    Detecteert het huidige thema via de Windows registry en past
    de DWM titelbalkkleur aan.
    """
    dialog.update()
    try:
        is_dark = _is_dark_mode()
        hwnd = dialog.winfo_id()
        set_titlebar_color(hwnd, dark=is_dark)
    except Exception:
        pass


def _is_dark_mode() -> bool:
    """Detecteer of Windows in dark mode staat."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False
