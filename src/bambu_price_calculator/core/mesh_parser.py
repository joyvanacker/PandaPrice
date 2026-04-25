"""Mesh parser: extraheert vertices, triangles, volume en bounding box uit 3MF model bestanden.

Rendert ook een isometrische wireframe preview met PIL (geen extra dependencies).
"""

from __future__ import annotations

import io
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


@dataclass
class MeshInfo:
    vertices: list[tuple[float, float, float]]
    triangles: list[tuple[int, int, int]]
    volume_cm3: float
    bbox_mm: tuple[float, float, float]  # L, B, H
    thumbnail_data: bytes  # PNG wireframe render


def parse_model_file(filepath: str) -> MeshInfo | None:
    """Parse een .model bestand (ZIP met 3MF XML) en extraheer mesh data."""
    path = Path(filepath)
    if not path.exists():
        return None

    try:
        # .model bestanden zijn ZIP-bestanden
        with zipfile.ZipFile(path) as z:
            # Zoek het model XML bestand
            model_name = None
            for name in z.namelist():
                if name.endswith(".model"):
                    model_name = name
                    break
            if not model_name:
                return None
            data = z.read(model_name).decode("utf-8")
    except (zipfile.BadZipFile, OSError):
        # Misschien is het een plain XML bestand
        try:
            data = path.read_text(encoding="utf-8")
        except Exception:
            return None

    return _parse_xml(data)


def _parse_xml(xml_data: str) -> MeshInfo | None:
    """Parse 3MF model XML en bereken volume, bbox en render wireframe."""
    try:
        tree = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError:
        return None

    verts: list[tuple[float, float, float]] = []
    tris: list[tuple[int, int, int]] = []

    for v in tree.iter(f"{{{_NS}}}vertex"):
        verts.append((float(v.get("x", 0)), float(v.get("y", 0)), float(v.get("z", 0))))

    for t in tree.iter(f"{{{_NS}}}triangle"):
        tris.append((int(t.get("v1", 0)), int(t.get("v2", 0)), int(t.get("v3", 0))))

    if not verts or not tris:
        return None

    # Bounding box
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    bbox = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))

    # Volume via signed tetrahedron method
    vol = 0.0
    for i1, i2, i3 in tris:
        v1, v2, v3 = verts[i1], verts[i2], verts[i3]
        vol += (
            v1[0] * (v2[1] * v3[2] - v3[1] * v2[2])
            - v2[0] * (v1[1] * v3[2] - v3[1] * v1[2])
            + v3[0] * (v1[1] * v2[2] - v2[1] * v1[2])
        )
    vol_cm3 = abs(vol) / 6.0 / 1000.0

    # Wireframe render
    thumbnail = _render_wireframe(verts, tris, xs, ys, zs, size=300)

    return MeshInfo(
        vertices=verts,
        triangles=tris,
        volume_cm3=round(vol_cm3, 2),
        bbox_mm=(round(bbox[0], 1), round(bbox[1], 1), round(bbox[2], 1)),
        thumbnail_data=thumbnail,
    )


def _render_wireframe(
    verts: list[tuple[float, float, float]],
    tris: list[tuple[int, int, int]],
    xs: list[float], ys: list[float], zs: list[float],
    size: int = 200,
) -> bytes:
    """Render een isometrische 3D preview met gevulde faces en belichting."""
    from PIL import Image, ImageDraw

    # Isometrische projectie
    cos_a, sin_a = math.cos(math.radians(-45)), math.sin(math.radians(-45))
    cos_e, sin_e = math.cos(math.radians(30)), math.sin(math.radians(30))

    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2

    def project(x: float, y: float, z: float) -> tuple[float, float, float]:
        dx, dy, dz = x - cx, y - cy, z - cz
        rx = dx * cos_a - dy * sin_a
        ry = dx * sin_a + dy * cos_a
        rz = dz
        px = rx
        py = -ry * sin_e - rz * cos_e
        depth = ry * cos_e - rz * sin_e  # voor z-sorting
        return px, py, depth

    # Projecteer alle vertices
    projected = [project(v[0], v[1], v[2]) for v in verts]

    pxs = [p[0] for p in projected]
    pys = [p[1] for p in projected]
    if not pxs or not pys:
        return b""

    margin = 12
    usable = size - 2 * margin
    range_x = max(pxs) - min(pxs) or 1
    range_y = max(pys) - min(pys) or 1
    scale = usable / max(range_x, range_y)

    off_x = size / 2 - (min(pxs) + max(pxs)) / 2 * scale
    off_y = size / 2 - (min(pys) + max(pys)) / 2 * scale

    def to_screen(idx: int) -> tuple[int, int]:
        px, py, _ = projected[idx]
        return int(px * scale + off_x), int(py * scale + off_y)

    # Lichtrichting (van rechtsboven)
    light = (0.4, -0.5, 0.7)
    light_len = math.sqrt(sum(c * c for c in light))
    light = tuple(c / light_len for c in light)

    # Bereken face normals en depth voor z-sorting
    face_data: list[tuple[float, list[tuple[int, int]], float]] = []
    for i1, i2, i3 in tris:
        v1, v2, v3 = verts[i1], verts[i2], verts[i3]
        # Normaal via kruisproduct
        e1 = (v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2])
        e2 = (v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2])
        nx = e1[1]*e2[2] - e1[2]*e2[1]
        ny = e1[2]*e2[0] - e1[0]*e2[2]
        nz = e1[0]*e2[1] - e1[1]*e2[0]
        nl = math.sqrt(nx*nx + ny*ny + nz*nz)
        if nl < 1e-10:
            continue
        nx, ny, nz = nx/nl, ny/nl, nz/nl

        # Belichting
        dot = nx*light[0] + ny*light[1] + nz*light[2]
        brightness = max(0.15, min(1.0, 0.3 + 0.7 * abs(dot)))

        # Depth (gemiddelde van geprojecteerde z)
        depth = (projected[i1][2] + projected[i2][2] + projected[i3][2]) / 3

        pts = [to_screen(i1), to_screen(i2), to_screen(i3)]
        face_data.append((depth, pts, brightness))

    # Sort: verste eerst (painter's algorithm)
    face_data.sort(key=lambda f: f[0])

    # Render
    bg = (0, 0, 0, 0)  # transparante achtergrond
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)

    # Bambu groen basis: (0, 174, 66)
    for _, pts, brightness in face_data:
        r = int(0 * brightness)
        g = int(174 * brightness)
        b = int(66 * brightness)
        fill = (r, g, b, 230)
        outline = (int(r * 0.6), int(g * 0.6), int(b * 0.6), 255)
        draw.polygon(pts, fill=fill, outline=outline)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def find_model_file(gcode_path: str) -> str | None:
    """Zoek het juiste .model bestand voor een specifiek gcode bestand.

    Gebruikt de project-3MF om de mapping gcode → object_id → model bestand
    te bepalen. Valt terug op het eerste .model bestand als de mapping faalt.
    """
    p = Path(gcode_path)
    session_dir = p.parent.parent
    objects_dir = session_dir / "3D" / "Objects"
    if not objects_dir.exists():
        return None

    gcode_name = p.name

    # Probeer de mapping via de project-3MF
    project_3mf = session_dir / ".3mf"
    if project_3mf.exists():
        try:
            model_path = _find_model_via_3mf(project_3mf, gcode_name, objects_dir)
            if model_path:
                return model_path
        except Exception:
            pass

    # Fallback: eerste .model bestand
    for f in sorted(objects_dir.glob("*.model")):
        return str(f)
    return None


def _find_model_via_3mf(
    project_3mf: Path, gcode_name: str, objects_dir: Path
) -> str | None:
    """Zoek het juiste .model bestand via de project-3MF mapping.

    Pad: gcode_name → plate.gcode_file → plate.model_instance.object_id
         → 3dmodel.model component.path → object_X.model
    """
    ns3mf = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ns_prod = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"

    with zipfile.ZipFile(project_3mf) as zf:
        names = zf.namelist()

        # Stap 1: Zoek object_id voor deze gcode via model_settings.config
        if "Metadata/model_settings.config" not in names:
            return None

        config = ElementTree.fromstring(zf.read("Metadata/model_settings.config"))
        target_obj_id: str | None = None

        for plate in config.iter("plate"):
            gcode_file = ""
            for meta in plate.iter("metadata"):
                if meta.get("key") == "gcode_file":
                    gcode_file = meta.get("value", "")
            if gcode_name in gcode_file:
                for mi in plate.iter("model_instance"):
                    for meta in mi.iter("metadata"):
                        if meta.get("key") == "object_id":
                            target_obj_id = meta.get("value", "")
                            break
                    if target_obj_id:
                        break
                break

        if not target_obj_id:
            return None

        # Stap 2: Zoek het component path in 3dmodel.model
        if "3D/3dmodel.model" not in names:
            return None

        model_xml = ElementTree.fromstring(zf.read("3D/3dmodel.model"))
        for obj in model_xml.iter(f"{{{ns3mf}}}object"):
            if obj.get("id") == target_obj_id:
                for comp in obj.iter(f"{{{ns3mf}}}component"):
                    comp_path = comp.get(f"{{{ns_prod}}}path", "")
                    if comp_path:
                        # comp_path is bijv. "/3D/Objects/object_1.model"
                        model_file = objects_dir / Path(comp_path).name
                        if model_file.exists():
                            return str(model_file)

    return None
