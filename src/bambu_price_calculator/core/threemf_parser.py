"""3MF Parser: extraheert thumbnail en metadata uit Bambu Studio 3MF bestanden.

Een 3MF bestand is een ZIP-archief dat naast het 3D model ook metadata bevat
zoals een preview-afbeelding, objectnamen en printermodel.
"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


@dataclass
class ThreeMFInfo:
    """Metadata geëxtraheerd uit een 3MF bestand."""
    thumbnail_data: bytes = b""       # PNG data van de plate thumbnail
    object_name: str = ""             # Naam van het hoofdobject
    printer_model_id: str = ""        # Printer model ID (bijv. "C12")
    creation_date: str = ""           # Aanmaakdatum


def parse_threemf(filepath: str) -> ThreeMFInfo | None:
    """Extraheer metadata uit een Bambu Studio 3MF bestand.

    Args:
        filepath: Pad naar het .3mf bestand.

    Returns:
        ThreeMFInfo met thumbnail en metadata, of None bij fout.
    """
    path = Path(filepath)
    if not path.exists() or not path.suffix == ".3mf":
        return None

    info = ThreeMFInfo()

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()

            # Thumbnail extraheren
            for candidate in ("Metadata/plate_1.png", "Metadata/plate_1_small.png"):
                if candidate in names:
                    info.thumbnail_data = zf.read(candidate)
                    break

            # plate_1.json: objectnamen
            if "Metadata/plate_1.json" in names:
                try:
                    plate = json.loads(zf.read("Metadata/plate_1.json"))
                    for obj in plate.get("bbox_objects", []):
                        name = obj.get("name", "")
                        if name and name != "wipe_tower":
                            info.object_name = name
                            break
                except (json.JSONDecodeError, KeyError):
                    pass

            # slice_info.config: printer model
            if "Metadata/slice_info.config" in names:
                try:
                    tree = ElementTree.fromstring(zf.read("Metadata/slice_info.config"))
                    for meta in tree.iter("metadata"):
                        key = meta.get("key", "")
                        val = meta.get("value", "")
                        if key == "printer_model_id":
                            info.printer_model_id = val
                except ElementTree.ParseError:
                    pass

            # 3dmodel.model: creation date
            if "3D/3dmodel.model" in names:
                try:
                    tree = ElementTree.fromstring(zf.read("3D/3dmodel.model"))
                    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
                    for meta in tree.findall("m:metadata", ns):
                        if meta.get("name") == "CreationDate":
                            info.creation_date = (meta.text or "").strip()
                except ElementTree.ParseError:
                    pass

    except (zipfile.BadZipFile, OSError) as exc:
        logger.warning("Kan 3MF niet lezen: %s: %s", filepath, exc)
        return None

    return info


def find_threemf_for_gcode(gcode_path: str) -> str | None:
    """Zoek het bijbehorende 3MF bestand voor een gcode bestand.

    Bambu Studio plaatst het 3MF in dezelfde map als de gcode,
    met dezelfde basisnaam maar .3mf extensie.
    """
    p = Path(gcode_path)
    candidate = p.with_suffix(".3mf")
    if candidate.exists():
        return str(candidate)
    return None
