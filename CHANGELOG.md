# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-26

### Added

- Multi-instance support: carousel navigation between multiple Bambu Studio instances
- Multi-plate support: navigate between plates within an instance, with automatic totals
- 3D wireframe preview rendered from the model mesh using PIL (no extra dependencies)
- Volume calculation and bounding box extraction from 3MF model files
- Per-plate model file matching via project 3MF mapping
- Model name extraction from project 3MF (original filename without extension)
- Advanced pricing mode: energy consumption, machine depreciation, maintenance, labor (prep + post-processing), setup costs, failure rate
- Settings dialog with tabbed interface (General, Simple, Advanced)
- Bambu Studio-inspired dark theme UI with custom toolbar and PIL-generated icons
- Custom PandaPrice application icon (panda face with euro sign)
- About dialog with version info and GitHub link
- Rich toast popup notification with thumbnail, price, and details when minimized to tray
- Full system tray context menu: Settings, Filament Profiles, History, Check for Updates, About, Quit
- Tooltips on all toolbar buttons
- Dark titlebar support via Windows DWM API
- Print details section: layer height, infill, nozzle diameter, total layers, model height, support, prime tower
- Total estimated time used instead of model printing time (includes machine preparation)
- Filament profile names cleaned: stripped @printer suffix and redundant material type
- Session-based deduplication: re-slicing the same model updates the existing result

### Changed

- Rebranded from "Bambu Price Calculator" to "PandaPrice"
- Installer renamed to PandaPrice-Setup.exe, install directory to PandaPrice
- Gcode watcher now scans recursively and processes all plates in the newest session on startup
- Filament matching prioritizes filament_id + color_hex for multicolor prints
- All filament profiles can now be deleted (minimum-one restriction removed)

### Fixed

- Recursive gcode watching for Bambu Studio subdirectories
- Correct active filament slot mapping via `; filament:` header
- Node.js 24 compatibility for GitHub Actions

## [0.1.0] - 2026-04-25

### Added

- Automatic gcode file watching via watchdog with polling observer
- Automatic detection of Bambu Studio default temp paths on first launch
- Gcode parser extracting filament weight, print time, and filament metadata (brand, material type, color, filament ID)
- Price calculation based on print time, filament usage, cost per hour, filament margin, and profit margin
- Filament profile management: create, edit, and delete profiles with brand, color, material type, spool weight, and purchase price
- Automatic filament recognition from gcode metadata with profile matching
- Dialog for creating new filament profiles when unknown filament is detected
- Calculation history with up to 500 most recent calculations, persisted in AppData
- System tray integration: minimize to tray, context menu with Open and Quit, double-click to restore
- Windows native notifications for new calculations while minimized
- Theme support: light, dark, and system (follows Windows setting automatically)
- Windows DWM titlebar color adjustment matching the active theme
- Multilingual support: Dutch and English, automatic system language detection, switch without restart
- Auto-update mechanism via GitHub Releases API with SemVer comparison, download progress, and automatic installer launch
- Settings persisted in `%APPDATA%\BambuPriceCalculator\settings.json`
- Recovery of default values when configuration file is corrupt or missing
- GitHub Actions workflow for automatic installer build and publish on version tag
- PyInstaller configuration for single-file .exe bundling
- Inno Setup script for Windows installer with start menu shortcut and uninstaller

[Unreleased]: https://github.com/joyvanacker/PandaPrice/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/joyvanacker/PandaPrice/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/joyvanacker/PandaPrice/releases/tag/v0.1.0
