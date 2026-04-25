"""Windows DWM titelbalkkleur integratie.

Gebruikt DwmSetWindowAttribute om de titelbalk in dark of light mode te zetten.
Op niet-Windows platforms doet deze module niets.
"""

import sys

# DWMWA_USE_IMMERSIVE_DARK_MODE attribute ID
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def set_titlebar_color(hwnd: int, dark: bool) -> None:
    """Stel de titelbalkkleur in op dark of light mode.

    Args:
        hwnd: Het window handle van het Tkinter-venster.
        dark: True voor dark mode, False voor light mode.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        import ctypes.wintypes

        dwmapi = ctypes.windll.dwmapi
        value = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        # Stilzwijgend negeren — DWM is niet beschikbaar op alle Windows versies
        pass
