"""Windows native notificaties.

Probeert win10toast te gebruiken, dan plyer, dan silent fallback.
Op niet-Windows platforms doet deze module niets.
"""

import sys


def show_notification(title: str, message: str) -> None:
    """Toon een Windows-notificatie.

    Probeert achtereenvolgens win10toast en plyer. Als geen van beide
    beschikbaar is, wordt de notificatie stilzwijgend genegeerd.

    Args:
        title: De titel van de notificatie.
        message: De berichttekst van de notificatie.
    """
    if sys.platform != "win32":
        return

    # Probeer win10toast
    try:
        from win10toast import ToastNotifier  # type: ignore[import]

        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=5, threaded=True)
        return
    except Exception:
        pass

    # Probeer plyer als fallback
    try:
        from plyer import notification  # type: ignore[import]

        notification.notify(title=title, message=message, timeout=5)
        return
    except Exception:
        pass

    # Silent fallback — geen notificatie mogelijk
