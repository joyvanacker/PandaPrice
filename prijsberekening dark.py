import sys
import subprocess
import os
import ctypes
import threading
import time
import re

# --- Automatische installatie van bibliotheken ---
def install_dependencies():
    required_packages = ["sv-ttk", "darkdetect", "pystray", "Pillow"]
    import_names = {"sv-ttk": "sv_ttk", "Pillow": "PIL"}
    
    for package in required_packages:
        import_name = import_names.get(package, package)
        try:
            __import__(import_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_dependencies()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
import darkdetect
from PIL import Image, ImageDraw
import pystray

BAMBU_GREEN = "#00ae42"
BAMBOO_TEMP = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "bamboo_model")

# ─── Windows Titelbalk Kleur ──────────────────────────────────────────────────
def change_title_bar_color(root, is_dark):
    root.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        rendering_policy = 1 if is_dark else 0
        value = ctypes.c_int(rendering_policy)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except:
        pass

# ─── Logica ──────────────────────────────────────────────────────────────────
def bereken_prijs(gewicht_gr, printtijd_u, running_costs, filament_per_kg, marge_pct):
    kosten_tijd = printtijd_u * running_costs
    kosten_filament = (filament_per_kg / 1000) * gewicht_gr * 2
    return (kosten_tijd + kosten_filament) * (1 + marge_pct / 100)

def formatteer_tijd(tijd_u):
    uren = int(tijd_u)
    minuten = int((tijd_u - uren) * 60)
    return f"{uren}u {minuten:02d}m"

def lees_gcode(pad):
    info = {"gewicht_totaal": 0, "printtijd_u": 0}
    try:
        with open(pad, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(150000)
            m_tijd = re.search(r"model printing time:\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?", content)
            if m_tijd:
                h, m, s = m_tijd.groups()
                info["printtijd_u"] = int(h or 0) + int(m or 0)/60 + int(s or 0)/3600
            m_gew = re.search(r"total filament weight \[g\]\s*:\s*([\d.,\s]+)", content)
            if m_gew:
                weights = [float(v.replace(',', '.')) for v in m_gew.group(1).replace(' ', '').split(",") if v]
                info["gewicht_totaal"] = sum(weights)
        return (info, None) if info["gewicht_totaal"] > 0 else (None, "Data incompleet")
    except Exception as e:
        return None, str(e)

# ─── Applicatie ──────────────────────────────────────────────────────────────
class PrijsBerekeningApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bambu Price Calculator")
        self.root.resizable(False, False)
        
        self.watch_map = tk.StringVar(value=BAMBOO_TEMP)
        self.watch_actief = False
        self.laatste_pad, self.laatste_mt = None, 0
        self.theme_var = tk.StringVar(value="System")

        self._bouw_ui()
        self._set_theme()
        
        # System Tray Logica
        self.root.protocol('WM_DELETE_WINDOW', self._hide_window)
        self._create_tray_icon()

        self.root.update_idletasks()
        self.root.geometry("")

    def _create_tray_icon(self):
        # Genereer icoon
        image = Image.new('RGB', (64, 64), color=BAMBU_GREEN)
        draw = ImageDraw.Draw(image)
        draw.ellipse((15, 15, 49, 49), fill="white")
        
        menu = (
            pystray.MenuItem('Open Calculator', self._show_window, default=True),
            pystray.MenuItem('Sluiten', self._quit_app)
        )
        self.tray_icon = pystray.Icon("BambuCalc", image, "Bambu Price Calculator", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _hide_window(self):
        self.root.withdraw()

    def _show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)

    def _quit_app(self, icon=None, item=None):
        self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def _set_theme(self, *args):
        mode = self.theme_var.get()
        is_dark = (darkdetect.theme().lower() == "dark") if mode == "System" else (mode.lower() == "dark")
        sv_ttk.set_theme("dark" if is_dark else "light")
        change_title_bar_color(self.root, is_dark)
        self._apply_styles()

    def _apply_styles(self):
        s = ttk.Style()
        s.configure("Bambu.TLabel", font=("Segoe UI", 11, "bold"), foreground=BAMBU_GREEN)
        s.configure("Price.TLabel", font=("Segoe UI", 26, "bold"), foreground=BAMBU_GREEN)

    def _bouw_ui(self):
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)

        fi = ttk.LabelFrame(main, text=" Calculatie ", padding=15)
        fi.pack(fill="x", pady=(0, 10))

        self.costs = tk.DoubleVar(value=1.00)
        self.filament = tk.DoubleVar(value=25.00)
        self.marge = tk.DoubleVar(value=20.0)

        for txt, var in [("Kosten p/u (€):", self.costs), ("Filament p/kg (€):", self.filament), ("Winstmarge (%):", self.marge)]:
            f = ttk.Frame(fi)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=txt).pack(side="left")
            ttk.Entry(f, textvariable=var, width=8, justify="right").pack(side="right")

        ft = ttk.Frame(fi)
        ft.pack(fill="x", pady=(10,0))
        ttk.Label(ft, text="Thema:").pack(side="left")
        cb = ttk.Combobox(ft, textvariable=self.theme_var, values=["Light", "Dark", "System"], state="readonly", width=8)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", self._set_theme)

        fm = ttk.LabelFrame(main, text=" Monitor ", padding=15)
        fm.pack(fill="x", pady=5)
        self.btn_watch = ttk.Button(fm, text="START AUTO-UPDATE", command=self._toggle_watch)
        self.btn_watch.pack(fill="x")
        self.status_lbl = ttk.Label(fm, text="Status: Stand-by", font=("Segoe UI", 8))
        self.status_lbl.pack(pady=(5,0))

        fr = ttk.LabelFrame(main, text=" Resultaat ", padding=15)
        fr.pack(fill="x", pady=10)
        self.lbl_file = ttk.Label(fr, text="Wachten op G-code...", font=("Segoe UI", 9, "italic"))
        self.lbl_file.pack(anchor="w")
        self.lbl_info = ttk.Label(fr, text="Gewicht: — | Tijd: —")
        self.lbl_info.pack(anchor="w", pady=5)
        ttk.Separator(fr, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(fr, text="TOTAALPRIJS", style="Bambu.TLabel").pack()
        self.lbl_totaal = ttk.Label(fr, text="€ 0.00", style="Price.TLabel")
        self.lbl_totaal.pack()

    def _toggle_watch(self):
        if self.watch_actief:
            self.watch_actief = False
            self.btn_watch.config(text="START AUTO-UPDATE")
            self.status_lbl.config(text="Status: Stand-by", foreground="gray")
        else:
            self.watch_actief = True
            self.btn_watch.config(text="STOP AUTO-UPDATE")
            self.status_lbl.config(text="Status: Actief", foreground=BAMBU_GREEN)
            threading.Thread(target=self._bewaken, daemon=True).start()

    def _bewaken(self):
        while self.watch_actief:
            nieuwste_pad, nieuwste_mtime = None, 0
            if os.path.exists(self.watch_map.get()):
                for dirpath, _, bestanden in os.walk(self.watch_map.get()):
                    for naam in bestanden:
                        if naam.endswith(".gcode"):
                            v = os.path.join(dirpath, naam)
                            try:
                                mt = os.path.getmtime(v)
                                if mt > nieuwste_mtime: nieuwste_mtime, nieuwste_pad = mt, v
                            except: pass
            
            if nieuwste_pad and (nieuwste_pad != self.laatste_pad or nieuwste_mtime != self.laatste_mt):
                self.laatste_pad, self.laatste_mt = nieuwste_pad, nieuwste_mtime
                self.root.after(0, lambda p=nieuwste_pad: self._verwerk(p))
            time.sleep(1)

    def _verwerk(self, pad):
        info, fout = lees_gcode(pad)
        if not fout:
            tijd_str = formatteer_tijd(info["printtijd_u"])
            totaal = bereken_prijs(info["gewicht_totaal"], info["printtijd_u"], self.costs.get(), self.filament.get(), self.marge.get())
            prijs_str = f"€ {totaal:.2f}"

            # UI Updaten
            self.lbl_file.config(text=os.path.basename(pad))
            self.lbl_info.config(text=f"Gewicht: {info['gewicht_totaal']:.1f}g  |  Tijd: {tijd_str}")
            self.lbl_totaal.config(text=prijs_str)

            # Nieuw: Systeemmelding versturen als de app op de achtergrond draait
            if self.root.state() == 'withdrawn' or self.root.state() == 'iconic':
                self.tray_icon.notify(
                    f"Nieuwe berekening: {os.path.basename(pad)}",
                    f"Printtijd: {tijd_str}\nTotale prijs: {prijs_str}"
                )

if __name__ == "__main__":
    root = tk.Tk()
    app = PrijsBerekeningApp(root)
    root.mainloop()