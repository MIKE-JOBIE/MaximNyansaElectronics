"""
Fixed-size image processing.
Every image is center-cropped to a fixed aspect ratio, then resized,
so templates always render clean, consistent cards.
"""
from io import BytesIO
from PIL import Image

# Central registry — change once, applies everywhere
IMAGE_PRESETS = {
    "product":   (800, 600),    # 4:3   — shop product card
    "program":   (1200, 675),   # 16:9  — training program cover
    "news":      (1200, 630),   # 1.9:1 — blog cover / og:image
    "video":     (1280, 720),   # 16:9  — video thumbnail
    "resource":  (600, 400),    # 3:2   — library thumbnail
    "hero":      (1920, 1080),  # 16:9  — hero background
    "avatar":    (400, 400),    # 1:1   — user profile
    "logo":      (600, 200),    # 3:1   — upload logo variant
}


def resize_and_crop(image_bytes, preset_or_size, quality=88):
    """
    Center-crop to target aspect ratio, then resize.
    preset_or_size: a key from IMAGE_PRESETS, or a (w, h) tuple.
    Returns JPEG bytes.
    """
    if isinstance(preset_or_size, str):
        if preset_or_size not in IMAGE_PRESETS:
            raise ValueError(f"Unknown preset: {preset_or_size}")
        target_w, target_h = IMAGE_PRESETS[preset_or_size]
    else:
        target_w, target_h = preset_or_size

    img = Image.open(BytesIO(image_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.convert("RGBA").split()[-1] if img.mode == "RGBA" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    target_ratio = target_w / target_h
    w, h = img.size
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    img = img.resize((target_w, target_h), Image.LANCZOS)

    out = BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    out.seek(0)
    return out.getvalue()