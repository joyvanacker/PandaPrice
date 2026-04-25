# Changelog

Alle noemenswaardige wijzigingen in dit project worden bijgehouden in dit bestand.

Het formaat is gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/1.0.0/),
en dit project hanteert [Semantische Versienummering](https://semver.org/lang/nl/).

## [Unreleased]

## [0.1.0] - 2025-01-01

### Added

- Automatische bewaking van de Bambu Studio gcode-map via `watchdog`
- Automatische detectie van bekende Bambu Studio standaardpaden bij eerste opstart
- Gcode-parser die filamentgewicht, printtijd en filamentmetadata (merk, materiaaltype, kleur, filament-ID) extraheert uit de gcode-header
- Prijsberekening op basis van printtijd, filamentverbruik, kosten per uur, filamentmarge en winstmarge
- Filamentprofielbeheer: aanmaken, bewerken en verwijderen van profielen met merk, kleur, materiaaltype, rolgewicht en aankoopprijs
- Automatische herkenning van het gebruikte filament uit gcode-metadata en koppeling aan bestaande profielen
- Dialoog voor het aanmaken van een nieuw filamentprofiel bij onbekend filament
- Berekeningsgeschiedenis met de 500 meest recente berekeningen, persistent opgeslagen in AppData
- Systeem-tray integratie: minimaliseren naar tray, contextmenu met Openen en Afsluiten, dubbelklik om te herstellen
- Windows-native notificaties bij nieuwe berekeningen terwijl de app geminimaliseerd is
- Thema-ondersteuning: licht, donker en systeem (volgt Windows-instelling automatisch)
- Windows DWM titelbalkkleur aanpassing passend bij het actieve thema
- Meertaligheid: Nederlands en Engels, automatische systeemtaaldetectie, direct wisselen zonder herstart
- Auto-update mechanisme via GitHub Releases API met SemVer-vergelijking, downloadvoortgang en automatisch starten van de installer
- Instellingen persistent opgeslagen in `%APPDATA%\BambuPriceCalculator\settings.json`
- Herstel van standaardwaarden bij corrupt of ontbrekend configuratiebestand
- GitHub Actions workflow voor automatisch bouwen en publiceren van de Windows-installer bij het taggen van een versie
- PyInstaller-configuratie voor onefile `.exe` bundeling
- Inno Setup-script voor Windows-installer met startmenu-snelkoppeling en uninstaller

[Unreleased]: ../../compare/v0.1.0...HEAD
[0.1.0]: ../../releases/tag/v0.1.0
