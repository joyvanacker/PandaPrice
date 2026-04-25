"""Genereer het PandaPrice applicatie-icoon als .ico bestand.

Draai dit script eenmalig om icon.ico te genereren:
    python -m bambu_price_calculator.assets.generate_icon
"""

from PIL import Image, ImageDraw


def create_icon(size: int = 256) -> Image.Image:
    """Maak een PandaPrice icoon: panda-gezicht met groen €-teken."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    cx, cy = s // 2, s // 2

    # Achtergrond cirkel (donkergrijs)
    d.ellipse([8, 8, s - 8, s - 8], fill="#2D2D30")

    # Panda oren (zwart)
    ear_r = s // 6
    d.ellipse([cx - s // 3 - ear_r, 12, cx - s // 3 + ear_r, 12 + ear_r * 2], fill="#1a1a1a")
    d.ellipse([cx + s // 3 - ear_r, 12, cx + s // 3 + ear_r, 12 + ear_r * 2], fill="#1a1a1a")

    # Panda gezicht (wit)
    face_r = s // 3
    d.ellipse([cx - face_r, cy - face_r + 10, cx + face_r, cy + face_r + 10], fill="#F0F0F0")

    # Ogen (zwart)
    eye_r = s // 10
    eye_y = cy - 5
    d.ellipse([cx - s // 5 - eye_r, eye_y - eye_r, cx - s // 5 + eye_r, eye_y + eye_r], fill="#1a1a1a")
    d.ellipse([cx + s // 5 - eye_r, eye_y - eye_r, cx + s // 5 + eye_r, eye_y + eye_r], fill="#1a1a1a")

    # Oogpupillen (wit)
    pr = eye_r // 3
    d.ellipse([cx - s // 5 - pr + 2, eye_y - pr - 2, cx - s // 5 + pr + 2, eye_y + pr - 2], fill="white")
    d.ellipse([cx + s // 5 - pr + 2, eye_y - pr - 2, cx + s // 5 + pr + 2, eye_y + pr - 2], fill="white")

    # Neus (zwart)
    nose_r = s // 18
    nose_y = cy + s // 10
    d.ellipse([cx - nose_r, nose_y - nose_r // 2, cx + nose_r, nose_y + nose_r // 2], fill="#1a1a1a")

    # € teken rechtsonder (Bambu groen)
    euro_size = s // 3
    euro_x = s - euro_size - 8
    euro_y = s - euro_size - 8
    # Groene cirkel achtergrond
    d.ellipse([euro_x, euro_y, euro_x + euro_size, euro_y + euro_size], fill="#00AE42")
    # € teken
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("segoeui.ttf", euro_size * 2 // 3)
    except (OSError, ImportError):
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), "€", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(
        (euro_x + (euro_size - tw) // 2, euro_y + (euro_size - th) // 2 - 2),
        "€", fill="white", font=font,
    )

    return img


def save_ico(path: str = "src/bambu_price_calculator/assets/icon.ico") -> None:
    """Sla het icoon op als .ico met meerdere resoluties."""
    sizes = [16, 32, 48, 64, 128, 256]
    base = create_icon(256)
    images = [base.resize((s, s), Image.LANCZOS) for s in sizes]
    images[0].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"Icoon opgeslagen: {path}")


if __name__ == "__main__":
    save_ico()
