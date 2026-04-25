"""MainWindow — Hoofdvenster van PandaPrice.

Bambu Studio-geïnspireerd design met clean dark/light theming,
groene accenten en moderne card-achtige secties.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import sv_ttk

from bambu_price_calculator.core.i18n_manager import I18nManager
from bambu_price_calculator.core.price_calculator import CalculationResult
from bambu_price_calculator.core.settings_manager import SettingsManager
from bambu_price_calculator.platform.dwm import set_titlebar_color

# Bambu Studio kleurenpalet
BAMBU_GREEN = "#00AE42"
BAMBU_GREEN_HOVER = "#00C94D"
BAMBU_GREEN_DIM = "#008A35"
TEXT_SECONDARY = "#888888"

# Thema-opties
_THEME_OPTIONS = ["Licht", "Donker", "Systeem"]
_THEME_MAP = {"Licht": "light", "Donker": "dark", "Systeem": "system"}
_THEME_MAP_INV = {v: k for k, v in _THEME_MAP.items()}

# Venster afmetingen
_WINDOW_WIDTH = 380


class _Tooltip:
    """Simpele tooltip die verschijnt bij hover over een widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tw: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event: tk.Event) -> None:
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tw = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)
        lbl = tk.Label(
            tw, text=self._text,
            background="#333", foreground="#eee",
            font=("Segoe UI", 8),
            padx=6, pady=3, relief=tk.SOLID, borderwidth=1,
        )
        lbl.pack()

    def _hide(self, event: tk.Event) -> None:
        if self._tw:
            self._tw.destroy()
            self._tw = None


class MainWindow:
    """Hoofdvenster met Bambu Studio-geïnspireerd design."""

    def __init__(
        self,
        root: tk.Tk,
        i18n: I18nManager,
        settings_manager: SettingsManager,
    ) -> None:
        self._root = root
        self._i18n = i18n
        self._sm = settings_manager

        # Callbacks
        self.on_toggle_watch: Callable[[], None] | None = None
        self.on_open_settings: Callable[[], None] | None = None
        self.on_open_filaments: Callable[[], None] | None = None
        self.on_open_history: Callable[[], None] | None = None
        self.on_check_update: Callable[[], None] | None = None
        self.on_settings_changed: Callable[[str, float], None] | None = None
        self.on_about: Callable[[], None] | None = None
        self.on_quit: Callable[[], None] | None = None

        settings = self._sm.get()

        # Tkinter variabelen
        self._theme_var = tk.StringVar(
            value=_THEME_MAP_INV.get(settings.theme, "Systeem")
        )

        # Venster configuratie
        self._root.title("PandaPrice")
        self._root.resizable(False, False)
        self._root.minsize(_WINDOW_WIDTH, 400)

        # Applicatie-icoon
        try:
            from pathlib import Path
            icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self._root.iconbitmap(str(icon_path))
        except Exception:
            pass

        # Thema
        sv_ttk.set_theme(self._resolve_sv_theme(settings.theme))
        self._apply_custom_styles()

        # UI opbouwen
        self._build_menubar()
        self._build_ui()

        # Titelbalk dark mode bij opstart
        self._update_titlebar(self._resolve_sv_theme(settings.theme))

    # ------------------------------------------------------------------
    # Custom styles
    # ------------------------------------------------------------------

    def _apply_custom_styles(self) -> None:
        """Pas Bambu Studio-geïnspireerde custom styles toe."""
        s = ttk.Style()

        # Groene accent knop
        s.configure(
            "Accent.TButton",
            font=("Segoe UI", 10, "bold"),
        )

        # Sectie headers
        s.configure(
            "Section.TLabel",
            font=("Segoe UI", 9, "bold"),
            foreground=TEXT_SECONDARY,
        )

        # Prijs display
        s.configure(
            "Price.TLabel",
            font=("Segoe UI", 28, "bold"),
            foreground=BAMBU_GREEN,
        )

        # Prijs header
        s.configure(
            "PriceHeader.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground=BAMBU_GREEN,
        )

        # Bestandsnaam
        s.configure(
            "Filename.TLabel",
            font=("Segoe UI", 10, "bold"),
        )

        # Info tekst
        s.configure(
            "Info.TLabel",
            font=("Segoe UI", 9),
            foreground=TEXT_SECONDARY,
        )

        # Filament item
        s.configure(
            "Filament.TLabel",
            font=("Segoe UI", 9),
        )

        # Status label
        s.configure(
            "Status.TLabel",
            font=("Segoe UI", 8),
            foreground=TEXT_SECONDARY,
        )

        # Actieve status
        s.configure(
            "StatusActive.TLabel",
            font=("Segoe UI", 8),
            foreground=BAMBU_GREEN,
        )

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_menubar(self) -> None:
        """Custom toolbar met PIL-gegenereerde iconen."""
        from PIL import Image, ImageDraw, ImageTk

        self._root.config(menu=tk.Menu(self._root))
        # Bewaar referenties zodat GC ze niet opruimt
        self._toolbar_icons: list[ImageTk.PhotoImage] = []

        toolbar = ttk.Frame(self._root, padding=(10, 6, 10, 4))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        # App titel links
        title_lbl = ttk.Label(
            toolbar,
            text="PandaPrice",
            font=("Segoe UI", 11, "bold"),
            foreground=BAMBU_GREEN,
        )
        title_lbl.pack(side=tk.LEFT)

        # Status indicator naast titel
        self._status_label = ttk.Label(
            toolbar, text="", font=("Segoe UI", 9)
        )
        self._status_label.pack(side=tk.LEFT, padx=(8, 0))
        self._status_tooltip: _Tooltip | None = None

        btn_style = "Toolbutton"
        sz = 18  # icoon grootte

        def _make_icon(draw_fn) -> ImageTk.PhotoImage:
            img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw_fn(draw, sz)
            photo = ImageTk.PhotoImage(img)
            self._toolbar_icons.append(photo)
            return photo

        # Gear icoon (instellingen) — tandwiel met inkepingen
        def _draw_gear(d: ImageDraw.Draw, s: int) -> None:
            c = s // 2
            # Buitenring met "tanden" gesimuleerd als dikkere ring
            d.ellipse([2, 2, s - 3, s - 3], outline="#aaa", width=3)
            # Binnenring (gat)
            d.ellipse([6, 6, s - 7, s - 7], fill=(0, 0, 0, 0), outline="#aaa", width=1)
            # Kruis in het midden voor tandwiel-effect
            d.line([(c, 1), (c, s - 2)], fill="#aaa", width=2)
            d.line([(1, c), (s - 2, c)], fill="#aaa", width=2)

        # Spool icoon (filamenten) — verticale spool met gat
        def _draw_spool(d: ImageDraw.Draw, s: int) -> None:
            # Buitenste rechthoek (spool body)
            d.rectangle([3, 1, s - 4, s - 2], outline=BAMBU_GREEN, width=2)
            # Horizontale lijn midden (as)
            c = s // 2
            d.line([(5, c), (s - 6, c)], fill=BAMBU_GREEN, width=1)
            # Kleine cirkel midden (gat)
            d.ellipse([c - 2, c - 2, c + 2, c + 2], outline=BAMBU_GREEN, width=1)

        # List icoon (geschiedenis)
        def _draw_list(d: ImageDraw.Draw, s: int) -> None:
            for y in (4, 9, 14):
                d.line([(3, y), (s - 4, y)], fill="#aaa", width=1)

        # Refresh icoon (updates)
        def _draw_refresh(d: ImageDraw.Draw, s: int) -> None:
            d.arc([3, 3, s - 4, s - 4], start=30, end=330, fill="#aaa", width=2)
            d.polygon([(s - 5, 3), (s - 2, 7), (s - 8, 7)], fill="#aaa")

        # Info icoon (about)
        def _draw_info(d: ImageDraw.Draw, s: int) -> None:
            c = s // 2
            d.ellipse([2, 2, s - 3, s - 3], outline="#aaa", width=2)
            d.line([(c, 7), (c, 7)], fill="#aaa", width=2)
            d.line([(c, 10), (c, s - 5)], fill="#aaa", width=2)

        icon_gear = _make_icon(_draw_gear)
        icon_spool = _make_icon(_draw_spool)
        icon_list = _make_icon(_draw_list)
        icon_refresh = _make_icon(_draw_refresh)
        icon_info = _make_icon(_draw_info)

        # Knoppen rechts
        btn_about = ttk.Button(
            toolbar, image=icon_info, style=btn_style,
            command=lambda: self.on_about and self.on_about(),
        )
        btn_about.pack(side=tk.RIGHT, padx=2)
        _Tooltip(btn_about, "Over PandaPrice")

        btn_update = ttk.Button(
            toolbar, image=icon_refresh, style=btn_style,
            command=lambda: self.on_check_update and self.on_check_update(),
        )
        btn_update.pack(side=tk.RIGHT, padx=2)
        _Tooltip(btn_update, "Controleer op updates")

        btn_history = ttk.Button(
            toolbar, image=icon_list, style=btn_style,
            command=lambda: self.on_open_history and self.on_open_history(),
        )
        btn_history.pack(side=tk.RIGHT, padx=2)
        _Tooltip(btn_history, "Berekeningsgeschiedenis")

        btn_filament = ttk.Button(
            toolbar, image=icon_spool, style=btn_style,
            command=lambda: self.on_open_filaments and self.on_open_filaments(),
        )
        btn_filament.pack(side=tk.RIGHT, padx=2)
        _Tooltip(btn_filament, "Filamentprofielen")

        btn_settings = ttk.Button(
            toolbar, image=icon_gear, style=btn_style,
            command=lambda: self.on_open_settings and self.on_open_settings(),
        )
        btn_settings.pack(side=tk.RIGHT, padx=2)
        _Tooltip(btn_settings, "Instellingen")

        ttk.Separator(self._root, orient=tk.HORIZONTAL).pack(fill=tk.X)

    def _build_ui(self) -> None:
        # Hoofdcontainer met padding
        outer = ttk.Frame(self._root, padding=(16, 12, 16, 8))
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_result_section(outer)
        self._build_filament_section(outer)
        self._build_details_section(outer)
        self._build_statusbar()

    def _build_result_section(self, parent: ttk.Frame) -> None:
        """Prominente resultaat-card met thumbnail en prijs."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 12))

        # Bovenste rij: thumbnail links, prijs rechts
        top_row = ttk.Frame(frame)
        top_row.pack(fill=tk.X, pady=(0, 6))

        # Thumbnail placeholder (links)
        self._thumb_label = ttk.Label(top_row, text="", style="Info.TLabel")
        self._thumb_label.pack(side=tk.LEFT, padx=(0, 12))
        self._thumb_photo = None  # bewaar referentie

        # Prijs + info (rechts)
        price_frame = ttk.Frame(top_row)
        price_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Object naam
        self._object_name_label = ttk.Label(
            price_frame, text="", style="Filename.TLabel"
        )
        self._object_name_label.pack(anchor=tk.W)

        # Gewicht + Tijd
        self._weight_time_label = ttk.Label(price_frame, text="", style="Info.TLabel")
        self._weight_time_label.pack(anchor=tk.W, pady=(2, 6))

        ttk.Label(
            price_frame, text="TOTAALPRIJS", style="PriceHeader.TLabel"
        ).pack(anchor=tk.W)

        self._price_label = ttk.Label(
            price_frame, text="€ 0.00", style="Price.TLabel"
        )
        self._price_label.pack(anchor=tk.W, pady=(2, 0))

    def _build_filament_section(self, parent: ttk.Frame) -> None:
        """Filament breakdown sectie met kleurblokjes."""
        # Sectie header
        ttk.Label(
            parent, text="FILAMENTEN", style="Section.TLabel"
        ).pack(anchor=tk.W, pady=(0, 6))

        self._filament_frame = ttk.Frame(parent)
        self._filament_frame.pack(fill=tk.X, pady=(0, 12))

        # Placeholder
        self._filament_placeholder = ttk.Label(
            self._filament_frame,
            text="Nog geen filamenten gedetecteerd",
            style="Info.TLabel",
        )
        self._filament_placeholder.pack(anchor=tk.W)

    def _build_details_section(self, parent: ttk.Frame) -> None:
        """Compacte print details sectie."""
        ttk.Label(
            parent, text="PRINT DETAILS", style="Section.TLabel"
        ).pack(anchor=tk.W, pady=(0, 6))

        self._details_frame = ttk.Frame(parent)
        self._details_frame.pack(fill=tk.X, pady=(0, 12))

        self._details_placeholder = ttk.Label(
            self._details_frame,
            text="Nog geen printgegevens",
            style="Info.TLabel",
        )
        self._details_placeholder.pack(anchor=tk.W)

    def _build_statusbar(self) -> None:
        self._statusbar = ttk.Label(
            self._root,
            text="",
            style="Status.TLabel",
            anchor=tk.W,
            padding=(16, 4),
        )
        self._statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # Publieke methoden
    # ------------------------------------------------------------------

    def update_result(self, result: CalculationResult) -> None:
        hours = int(result.print_time_minutes // 60)
        minutes = int(result.print_time_minutes % 60)
        time_str = f"{hours}u {minutes:02d}m" if hours else f"{minutes}m"
        self._weight_time_label.config(
            text=f"{time_str}   |   {result.weight_grams:.1f}g"
        )
        self._price_label.config(text=f"€ {result.sale_price:.2f}")

    def update_filament_breakdown(
        self,
        items: list[tuple[str, str, float, float]],
    ) -> None:
        """Toon per filament: naam, kleur, gewicht en kosten."""
        for widget in self._filament_frame.winfo_children():
            widget.destroy()

        if not items:
            ttk.Label(
                self._filament_frame,
                text="Nog geen filamenten gedetecteerd",
                style="Info.TLabel",
            ).pack(anchor=tk.W)
            return

        for name, color_hex, weight, cost in items:
            row = ttk.Frame(self._filament_frame)
            row.pack(fill=tk.X, pady=2)

            # Kleurblokje — groter en afgerond
            canvas = tk.Canvas(
                row, width=16, height=16,
                highlightthickness=0, borderwidth=0,
            )
            canvas.pack(side=tk.LEFT, padx=(0, 8), pady=1)
            # Rond vierkant simuleren
            canvas.create_oval(1, 1, 15, 15, fill=color_hex, outline=color_hex)

            # Naam
            ttk.Label(
                row, text=name, style="Filament.TLabel"
            ).pack(side=tk.LEFT)

            # Kosten rechts
            ttk.Label(
                row,
                text=f"€ {cost:.2f}",
                style="Filament.TLabel",
                foreground=BAMBU_GREEN,
            ).pack(side=tk.RIGHT)

            # Gewicht rechts van naam
            ttk.Label(
                row,
                text=f"{weight:.1f}g",
                style="Info.TLabel",
            ).pack(side=tk.RIGHT, padx=(0, 12))

    def update_print_details(self, result: "ParseResult") -> None:
        """Toon compacte print details + thumbnail + objectnaam."""
        # Thumbnail
        if result.thumbnail_data:
            try:
                from PIL import Image, ImageTk
                import io
                img = Image.open(io.BytesIO(result.thumbnail_data))
                img.thumbnail((100, 100))
                self._thumb_photo = ImageTk.PhotoImage(img)
                self._thumb_label.config(image=self._thumb_photo, text="")
            except Exception:
                self._thumb_label.config(image="", text="")
        else:
            self._thumb_label.config(image="", text="")

        # Object naam
        self._object_name_label.config(text=result.object_name or "")

        # Details grid
        for widget in self._details_frame.winfo_children():
            widget.destroy()

        grid = ttk.Frame(self._details_frame)
        grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)

        items = []
        if result.layer_height_mm:
            items.append(("Laaghoogte", f"{result.layer_height_mm}mm"))
        if result.nozzle_diameter_mm:
            items.append(("Nozzle", f"{result.nozzle_diameter_mm}mm"))
        if result.total_layers:
            items.append(("Lagen", str(result.total_layers)))
        if result.model_height_mm:
            items.append(("Hoogte", f"{result.model_height_mm}mm"))
        if result.infill_pct:
            items.append(("Infill", f"{int(result.infill_pct)}%"))
        if result.print_profile:
            items.append(("Profiel", result.print_profile))
        if result.bed_type:
            items.append(("Bed", result.bed_type))

        flags = []
        if result.has_support:
            flags.append("Support")
        if result.has_prime_tower:
            flags.append("Prime Tower")
        if flags:
            items.append(("Opties", ", ".join(flags)))

        for row, (label, value) in enumerate(items):
            ttk.Label(grid, text=label, style="Info.TLabel").grid(
                row=row, column=0, sticky=tk.W, pady=1
            )
            ttk.Label(grid, text=value, font=("Segoe UI", 9)).grid(
                row=row, column=1, sticky=tk.E, pady=1
            )

    def set_status(self, text: str, is_error: bool = False) -> None:
        if is_error:
            self._status_label.config(text="Inactief", foreground="#E74C3C")
            # Tooltip met foutdetails
            if self._status_tooltip:
                self._status_tooltip._text = text
            else:
                self._status_tooltip = _Tooltip(self._status_label, text)
            self._statusbar.config(text=text, foreground="#E74C3C")
        else:
            self._statusbar.config(text=text, foreground=TEXT_SECONDARY)

    def set_watch_active(self, active: bool) -> None:
        if active:
            self._status_label.config(text="Actief", foreground=BAMBU_GREEN)
            # Verwijder error tooltip
            self._status_tooltip = None
        else:
            self._status_label.config(text="", foreground=TEXT_SECONDARY)

    def apply_theme(self, theme: str) -> None:
        sv_theme = self._resolve_sv_theme(theme)
        sv_ttk.set_theme(sv_theme)
        self._apply_custom_styles()
        self._update_titlebar(sv_theme)

    # ------------------------------------------------------------------
    # Interne callbacks
    # ------------------------------------------------------------------

    def _on_toggle_watch(self) -> None:
        if self.on_toggle_watch:
            self.on_toggle_watch()

    def _on_quit(self) -> None:
        if self.on_quit:
            self.on_quit()
        else:
            self._root.destroy()

    # ------------------------------------------------------------------
    # Hulpmethoden
    # ------------------------------------------------------------------

    def _resolve_sv_theme(self, theme: str) -> str:
        if theme == "dark":
            return "dark"
        if theme == "light":
            return "light"
        return self._detect_system_theme()

    @staticmethod
    def _detect_system_theme() -> str:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value else "dark"
        except Exception:
            return "light"

    def _update_titlebar(self, sv_theme: str) -> None:
        try:
            self._root.update()
            hwnd = self._root.winfo_id()
            set_titlebar_color(hwnd, dark=(sv_theme == "dark"))
        except Exception:
            pass
