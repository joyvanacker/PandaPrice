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
    thumbnail = _render_wireframe(verts, tris, xs, ys, zs)

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
    """Render een isometrische wireframe preview als PNG bytes met PIL."""
    from PIL import Image, ImageDraw

    # Isometrische projectie (30° elevatie, -45° azimut)
    cos_a, sin_a = math.cos(math.radians(-45)), math.sin(math.radians(-45))
    cos_e, sin_e = math.cos(math.radians(30)), math.sin(math.radians(30))

    # Centreer het model
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2

    def project(x: float, y: float, z: float) -> tuple[float, float]:
        """Projecteer 3D punt naar 2D isometrisch."""
        dx, dy, dz = x - cx, y - cy, z - cz
        # Roteer rond Z-as
        rx = dx * cos_a - dy * sin_a
        ry = dx * sin_a + dy * cos_a
        rz = dz
        # Projecteer met elevatie
        px = rx
        py = -ry * sin_e - rz * cos_e
        return px, py

    # Projecteer alle vertices
    projected = [project(v[0], v[1], v[2]) for v in verts]

    # Bereken schaal
    pxs = [p[0] for p in projected]
    pys = [p[1] for p in projected]
    if not pxs or not pys:
        return b""

    margin = 16
    usable = size - 2 * margin
    range_x = max(pxs) - min(pxs) or 1
    range_y = max(pys) - min(pys) or 1
    scale = usable / max(range_x, range_y)

    off_x = size / 2 - (min(pxs) + max(pxs)) / 2 * scale
    off_y = size / 2 - (min(pys) + max(pys)) / 2 * scale

    def to_screen(idx: int) -> tuple[int, int]:
        px, py = projected[idx]
        return int(px * scale + off_x), int(py * scale + off_y)

    # Render
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Subsample edges voor performance (max ~3000 unieke edges)
    edges: set[tuple[int, int]] = set()
    max_edges = 3000
    for i1, i2, i3 in tris:
        for a, b in ((i1, i2), (i2, i3), (i3, i1)):
            edge = (min(a, b), max(a, b))
            edges.add(edge)
            if len(edges) >= max_edges:
                break
        if len(edges) >= max_edges:
            break

    # Teken edges
    edge_color = (0, 174, 66, 180)  # BAMBU_GREEN met alpha
    for a, b in edges:
        p1 = to_screen(a)
        p2 = to_screen(b)
        draw.line([p1, p2], fill=edge_color, width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def find_model_file(gcode_path: str) -> str | None:
    """Zoek het .model bestand in de 3D/Objects map van de session."""
    p = Path(gcode_path)
    # gcode zit in Metadata/, model in ../3D/Objects/
    session_dir = p.parent.parent
    objects_dir = session_dir / "3D" / "Objects"
    if not objects_dir.exists():
        return None
    # Neem het eerste .model bestand
    for f in sorted(objects_dir.glob("*.model")):
        return str(f)
    return None
