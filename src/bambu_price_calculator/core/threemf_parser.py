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
    thumbnail_data: bytes = b""
    object_name: str = ""
    model_name: str = ""              # Originele modelnaam (zonder extensie)
    printer_model_id: str = ""
    creation_date: str = ""


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
    """Zoek het bijbehorende geslicede 3MF bestand voor een gcode bestand."""
    p = Path(gcode_path)
    candidate = p.with_suffix(".3mf")
    if candidate.exists():
        return str(candidate)
    return None


def find_project_threemf(gcode_path: str) -> str | None:
    """Zoek de project-3MF (ongeslieed) in de parent map van de Metadata map.

    Bambu Studio structuur:
        session_dir/.3mf              ← project 3MF
        session_dir/Metadata/.gcode   ← geslicede gcode
    """
    p = Path(gcode_path)
    # gcode zit in Metadata/, project 3MF zit in de parent daarvan
    session_dir = p.parent.parent
    candidate = session_dir / ".3mf"
    if candidate.exists():
        return str(candidate)
    # Zoek ook naar andere .3mf bestanden in de session dir
    for f in session_dir.glob("*.3mf"):
        return str(f)
    return None


def extract_model_name(project_3mf_path: str) -> str:
    """Extraheer de originele modelnaam uit een project-3MF.

    Zoekt in Metadata/model_settings.config naar het 'name' attribuut
    van het eerste object. Stript de bestandsextensie.
    """
    try:
        with zipfile.ZipFile(project_3mf_path, "r") as zf:
            if "Metadata/model_settings.config" not in zf.namelist():
                return ""
            tree = ElementTree.fromstring(zf.read("Metadata/model_settings.config"))
            for obj in tree.iter("object"):
                for meta in obj.iter("metadata"):
                    if meta.get("key") == "name":
                        name = meta.get("value", "")
                        if name:
                            # Strip extensie (.step, .stl, .3mf, etc.)
                            return Path(name).stem
            return ""
    except Exception:
        return ""
