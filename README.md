# Bambu Price Calculator

Een Windows-desktopapplicatie die automatisch verkoopprijzen berekent voor 3D-prints op basis van gcode-bestanden die Bambu Studio aanmaakt.

De app bewaakt een gcode-map op de achtergrond, parseert nieuwe bestanden zodra ze verschijnen, en berekent direct een verkoopprijs op basis van printtijd, filamentverbruik en jouw ingestelde parameters. Resultaten worden bijgehouden in een geschiedenis en de app draait als systeem-tray icoon zodat hij niet in de weg zit.

## Vereisten

- Windows 10 of nieuwer
- Python 3.11 of nieuwer

## Installatie

### Via de installer (aanbevolen)

Download de nieuwste `installer.exe` van de [Releases-pagina](https://github.com/joyvanacker/PandaPrice/releases) en voer hem uit.

### Vanuit broncode

```bash
pip install -r requirements.txt
```

## Gebruik

### App starten

```bash
python -m bambu_price_calculator
```

Of dubbelklik op de geïnstalleerde snelkoppeling in het startmenu.

### Gcode-map instellen

Bij de eerste opstart probeert de app de Bambu Studio tijdelijke map automatisch te vinden. Als dat niet lukt, verschijnt er een dialoog om het pad handmatig in te stellen.

Je kunt het pad altijd aanpassen via **Instellingen → Gcode-map**. Klik op de mapkiezer-knop om een map te selecteren. De watcher herstart automatisch op het nieuwe pad.

Standaard Bambu Studio-paden die automatisch worden gedetecteerd:

- `%LOCALAPPDATA%\Bambu Lab\Bambu Studio\cache`
- `%TEMP%\Bambu Studio`

### Berekeningsparameters instellen

Via **Instellingen** stel je in:

- **Kosten per uur (€)** — machineuurtarief
- **Filamentmarge (%)** — opslag op de filamentkosten
- **Winstmarge (%)** — algemene winstopslag

De verkoopprijs wordt berekend als:

```
verkoopprijs = (
    (printtijd_minuten / 60) × kosten_per_uur
    + gewicht_gram × (aankoopprijs / rolgewicht) × (1 + filamentmarge / 100)
) × (1 + winstmarge / 100)
```

### Filamentprofielen beheren

Via **Filamenten** maak je profielen aan met merk, kleur, materiaaltype, rolgewicht en aankoopprijs. De app herkent het gebruikte filament automatisch uit de gcode-metadata en selecteert het bijbehorende profiel. Bij een onbekend filament wordt gevraagd om een prijs per kg in te voeren, waarna een nieuw profiel wordt aangemaakt.

### Systeem-tray

Het venster sluiten of minimaliseren verbergt de app naar de systeem-tray. Dubbelklik op het tray-icoon om het venster te herstellen. Via het contextmenu kies je **Openen** of **Afsluiten**.

## Auto-update workflow

De app controleert bij elke opstart automatisch op updates via de GitHub Releases API.

### Hoe het werkt

1. Bij opstart roept `UpdateManager` `GET /repos/{owner}/{repo}/releases/latest` aan.
2. Het versienummer van de nieuwste release wordt vergeleken met de huidige versie via semantische versienummering (SemVer 2.0).
3. Als er een nieuwere versie beschikbaar is, verschijnt er een dialoog met het versienummer en de releasenotities.
4. Na bevestiging downloadt de app de `installer.exe` uit de release-assets naar een tijdelijke map.
5. De installer wordt gestart en de app sluit zichzelf af zodat de installatie kan plaatsvinden.

Als de GitHub API niet bereikbaar is, start de app gewoon op zonder foutmelding. Een mislukte download toont een dialoog met de opties **Opnieuw proberen** of **Overslaan**.

Je kunt ook handmatig een updatecontrole starten via **Help → Controleer op updates**.

## Ontwikkelaarsinstructies

### Omgeving opzetten

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Tests uitvoeren

```bash
pytest
```

### Applicatie bouwen

Zorg dat [PyInstaller](https://pyinstaller.org/) en [Inno Setup](https://jrsoftware.org/isinfo.php) geïnstalleerd zijn.

```bash
# Stap 1: bouw de .exe
pyinstaller bambu_price_calculator.spec

# Stap 2: bouw de installer
iscc installer/setup.iss
```

De installer verschijnt als `installer/Output/installer.exe`.

### Release publiceren

1. Verhoog de versie in `pyproject.toml` en `src/bambu_price_calculator/app.py`.
2. Werk `CHANGELOG.md` bij met de wijzigingen voor de nieuwe versie.
3. Commit en tag de release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

De GitHub Actions workflow (`.github/workflows/release.yml`) bouwt automatisch de installer en publiceert hem als GitHub Release-asset.

### GitHub owner/repo aanpassen

De `UpdateManager` in `src/bambu_price_calculator/app.py` bevat de GitHub-repository-referentie:

```python
self._update_manager = UpdateManager("0.1.0", "joyvanacker", "PandaPrice")
```

De repository staat op [github.com/joyvanacker/PandaPrice](https://github.com/joyvanacker/PandaPrice).
