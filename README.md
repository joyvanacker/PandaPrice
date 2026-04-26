# PandaPrice

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="src/bambu_price_calculator/assets/logo-white.svg">
    <source media="(prefers-color-scheme: light)" srcset="src/bambu_price_calculator/assets/logo-black.svg">
    <img alt="PandaPrice Logo" src="src/bambu_price_calculator/assets/logo-black.svg" width="200">
  </picture>

  ### **Automatic price calculator for 3D prints based on Bambu Studio gcode files.**

  [![GitHub last commit](https://img.shields.io/github/last-commit/joyvanacker/PandaPrice?style=flat-square&color=2ecc71)](https://github.com/joyvanacker/PandaPrice/commits)
  [![GitHub top language](https://img.shields.io/github/languages/top/joyvanacker/PandaPrice?style=flat-square&color=3498db)](https://github.com/joyvanacker/PandaPrice)
  [![GitHub license](https://img.shields.io/github/license/joyvanacker/PandaPrice?style=flat-square&color=f1c40f)](https://github.com/joyvanacker/PandaPrice/blob/main/LICENSE)

  ---

  *PandaPrice runs in the background, watches for new sliced files from Bambu Studio, and instantly calculates a sale price based on print time, filament usage, and your configured parameters.*
</div>

## ✨ Features

* **🔍 Smart Detection:** Automatic gcode detection from the Bambu Studio temp folder.
* **🌈 Multicolor Support:** Multi-filament support with per-slot pricing and per-plate navigation.
* **📦 Multi-Instance:** Support for multiple Bambu Studio instances with carousel navigation.
* **🌐 3D Preview:** Real-time 3D wireframe preview rendered directly from the model mesh.
* **💰 Dynamic Pricing:** * *Simple Mode:* Quick cost per hour and margins.
    * *Advanced Mode:* Energy, depreciation, maintenance, labor, and failure rate.
* **📋 Print Details:** Shows layer height, infill, volume, bounding box, and nozzle size.
* **🔔 System Integration:** System tray support with rich toast notifications.
* **🎨 Theme Support:** Dark, light, and system themes inspired by the Bambu Studio design.
* **🔄 Auto-update:** Built-in update checker via GitHub Releases.
* **🌍 Multilingual:** Fully localized in **English** and **Dutch**.

---

## 🚀 Installation

### Installer (Recommended)
Download the latest `PandaPrice-Setup.exe` from the [Releases page](https://github.com/joyvanacker/PandaPrice/releases) and run the installer.

### From Source
If you prefer to run it manually, ensure you have **Python 3.11+** installed:

```bash
# Clone the repository
git clone [https://github.com/joyvanacker/PandaPrice.git](https://github.com/joyvanacker/PandaPrice.git)
cd PandaPrice
```

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .
```

```bash
# Run the application
python -m bambu_price_calculator
```

## 🛠️ Usage

1.  **First Launch:** PandaPrice automatically detects the Bambu Studio temp folder. If it fails, you can set the path manually in **Settings**.
2.  **Monitoring:** Keep the app running (in the tray). When you slice a model in Bambu Studio, PandaPrice instantly calculates the price.
3.  **Filament Profiles:** Profiles are auto-created from gcode metadata (brand, type, color, price). You can fine-tune these in the **Filament Profiles** dialog.

---

## 📋 Requirements

* **OS:** Windows 10 or newer
* **Python:** 3.11 or newer (for source installation)

---

## 🔄 Auto-update

PandaPrice checks for updates on startup via the GitHub Releases API. When a newer version is available, it shows a dialog with release notes and offers to download and install the update.

---

## 📄 License & Disclaimer

**License:** Distributed under the **MIT License**. See `LICENSE` for more information.

**Disclaimer:** PandaPrice is not affiliated with, endorsed by, or associated with **Bambu Lab**. "Bambu Studio" is a trademark of Bambu Lab. This is an independent open-source tool.

---
<div align="center">
  <sub>Built with ❤️ for the 3D printing community</sub>
</div>
