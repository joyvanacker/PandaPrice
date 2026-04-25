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
        hwnd: Het Tkinter winfo_id() — wordt intern omgezet naar het echte Windows HWND.
        dark: True voor dark mode, False voor light mode.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        import ctypes.wintypes

        # Tkinter winfo_id() geeft een child widget ID, niet het top-level HWND.
        # GetParent() geeft het echte venster-handle.
        real_hwnd = ctypes.windll.user32.GetParent(hwnd)

        dwmapi = ctypes.windll.dwmapi
        value = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(
            real_hwnd,
            _DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        pass
