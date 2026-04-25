# PandaPrice

Automatic price calculator for 3D prints based on Bambu Studio gcode files.

PandaPrice runs in the background, watches for new sliced files from Bambu Studio, and instantly calculates a sale price based on print time, filament usage, and your configured parameters. It supports multicolor prints, multiple plates, multiple Bambu Studio instances, and shows a 3D wireframe preview of each model.

## Features

- Automatic gcode detection from Bambu Studio temp folder
- Multicolor and multi-filament support with per-slot pricing
- Multi-plate support with totals and per-plate navigation
- Multiple Bambu Studio instance support with carousel navigation
- 3D wireframe preview rendered from the model mesh
- Automatic filament profile creation from gcode metadata
- Simple and advanced pricing modes (energy, depreciation, labor, failure rate)
- Print details: layer height, infill, volume, bounding box, nozzle size
- System tray with rich toast notifications
- Dark/light/system theme with Bambu Studio-inspired design
- Auto-update via GitHub Releases
- Calculation history
- Multilingual (English, Dutch)

## Requirements

- Windows 10 or newer
- Python 3.11 or newer

## Installation

### Installer (recommended)

Download the latest `PandaPrice-Setup.exe` from the [Releases page](https://github.com/joyvanacker/PandaPrice/releases) and run it.

### From source

```bash
pip install -r requirements.txt
pip install -e .
python -m bambu_price_calculator
```

## Usage

On first launch, PandaPrice automatically detects the Bambu Studio temp folder. If not found, you can set the path manually via Settings.

The app watches for new gcode files in the background. When Bambu Studio slices a model, PandaPrice instantly calculates the price and shows it in the main window or as a toast notification if minimized to the system tray.

### Pricing

Simple mode: configure cost per hour, filament margin, and profit margin.

Advanced mode: break down costs into energy consumption, machine depreciation, maintenance, labor (prep + post-processing time), setup costs, and failure rate.

### Filament profiles

Filament profiles are automatically created from gcode metadata (brand, material type, color, price per kg from Bambu Studio settings). You can edit profiles manually via the filament profiles dialog.

## Auto-update

PandaPrice checks for updates on startup via the GitHub Releases API. When a newer version is available, it shows a dialog with release notes and offers to download and install the update.

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
pytest
```

### Building

```bash
pyinstaller bambu_price_calculator.spec
iscc installer/setup.iss
```

### Releasing

1. Update version in `pyproject.toml`, `src/bambu_price_calculator/__init__.py`, and `src/bambu_price_calculator/app.py`
2. Update `CHANGELOG.md`
3. Tag and push:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The GitHub Actions workflow builds the installer and publishes it as a release asset.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer

PandaPrice is not affiliated with, endorsed by, or associated with Bambu Lab. "Bambu Studio" is a trademark of Bambu Lab. This is an independent open-source tool.
