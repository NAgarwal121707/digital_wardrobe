"""Shared multi-garment Vision AI helpers for website + REST API.

The important design rule is that a photograph and a wardrobe item are not the
same thing.  A photo can contain several independently reusable garments.  We
therefore keep the original photo in an OutfitGroup and save detected pieces as
individual ClothingItem rows.  The user may additionally save the whole look as
one complete-outfit card.
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps, UnidentifiedImageError

from wardrobe.models import ClothingItem, OutfitGroup


MULTI_GARMENT_PROMPT = r"""
You are the vision engine for a personal digital wardrobe. Analyse ONE uploaded
fashion photo and return ONLY one valid JSON object.

CRITICAL CONCEPT
A photo can contain multiple independently reusable garments. Never collapse a
burgundy top + black jeans into one wardrobe item. Detect the top and jeans as
two separate pieces. The app can separately remember that they appeared in the
same original look.

Return this exact shape:
{
  "is_clothing_image": true,
  "confidence": 0,
  "rejection_reason": "",
  "source_kind": "single_piece | multi_piece | one_piece_outfit",
  "pieces": [
    {
      "name": "Burgundy top",
      "category": "Tops",
      "color": "Burgundy",
      "tags": ["burgundy", "top"],
      "garment_type": "Top",
      "aesthetic": "Smart casual",
      "fit_silhouette": "Fitted",
      "occasion": "Casual, Smart casual",
      "season": "Autumn, Winter",
      "accessories": ["small hoops", "black shoulder bag"],
      "is_complete_outfit": false,
      "styling_notes": "Short, specific advice for this piece.",
      "bounding_box": {"x": 80, "y": 80, "width": 840, "height": 420}
    }
  ],
  "outfit": {
    "name": "Burgundy top + black jeans",
    "category": "Complete Outfit",
    "color": "Burgundy, Black",
    "aesthetic": "Smart casual",
    "occasion": "Casual, Smart casual",
    "season": "Autumn, Winter",
    "accessories": ["black shoulder bag", "minimal hoops"],
    "styling_notes": "Short advice for the whole look."
  }
}

RULES
- bounding_box coordinates are integers from 0 to 1000 relative to the full
  image: x/y are top-left; width/height are box size. Include a useful amount
  of the garment but minimise other garments where possible.
- Return one object in pieces for EACH clearly visible independently reusable
  main garment: top + jeans = 2, blazer + shirt + trousers = 3, kurta + pants =
  2, shirt + skirt = 2.
- A single dress, saree, gown, jumpsuit, frock or other true one-piece garment
  is ONE piece. Set its is_complete_outfit=true when it is wearable as the main
  complete garment.
- A co-ord set should normally be separate pieces if top and bottom can be worn
  independently; the outfit object remembers the set/look.
- Footwear, bags and visible fashion accessories may be pieces when they are a
  clear main subject. Do not create tiny jewellery pieces in a normal full-body
  outfit photo unless clearly showcased.
- Do not invent hidden garments, brands, fabric, fit, or colours you cannot see.
- If the image is not clearly fashion/clothing/footwear/bag/accessory, return
  is_clothing_image=false, an empty pieces array, and a useful rejection_reason.
- Keep names/categories concise. Use human wardrobe categories such as Tops,
  Jeans, Trousers, Skirts, Dresses, Jackets, Shoes, Bags, Accessories, Ethnic.
- styling_notes must be specific to what is visible, not generic filler.
- outfit describes the original combination. If there is only one ordinary
  piece, outfit may still describe it but must not invent a second garment.
""".strip()


_ALLOWED_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}


def validate_image_bytes(raw: bytes) -> tuple[str, str]:
    """Return trusted MIME and extension after validating actual image bytes."""
    try:
        with Image.open(BytesIO(raw)) as image:
            fmt = (image.format or "").upper()
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("The selected file is not a valid image.") from exc
    if fmt not in _ALLOWED_FORMATS:
        raise ValueError("Only JPG, PNG or WEBP images are allowed.")
    return _ALLOWED_FORMATS[fmt]


def _ai_ready_bytes(raw: bytes) -> tuple[bytes, str]:
    """Compress large inputs before sending to the vision model."""
    with Image.open(BytesIO(raw)) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        elif image.mode == "L":
            image = image.convert("RGB")
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        out = BytesIO()
        image.save(out, format="JPEG", quality=84, optimize=True)
        return out.getvalue(), "image/jpeg"


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value or "").strip()
    return [x.strip() for x in text.split(",") if x.strip()] if text else []


def _normalise_box(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    try:
        x = int(float(value.get("x", 0)))
        y = int(float(value.get("y", 0)))
        w = int(float(value.get("width", 0)))
        h = int(float(value.get("height", 0)))
    except (TypeError, ValueError):
        return None
    x, y = max(0, min(x, 1000)), max(0, min(y, 1000))
    w, h = max(0, min(w, 1000 - x)), max(0, min(h, 1000 - y))
    if w < 80 or h < 80:
        return None
    return {"x": x, "y": y, "width": w, "height": h}


def _normalise_piece(piece: Any, index: int) -> dict[str, Any]:
    p = piece if isinstance(piece, dict) else {}
    name = _as_text(p.get("name")) or f"Detected item {index + 1}"
    return {
        "name": name[:120],
        "category": (_as_text(p.get("category")) or "Uncategorized")[:80],
        "color": (_as_text(p.get("color")) or "Not specified")[:50],
        "tags": _as_list(p.get("tags")),
        "garment_type": _as_text(p.get("garment_type"))[:120],
        "aesthetic": _as_text(p.get("aesthetic"))[:120],
        "fit_silhouette": _as_text(p.get("fit_silhouette"))[:160],
        "occasion": _as_text(p.get("occasion"))[:120],
        "season": _as_text(p.get("season"))[:120],
        "accessories": _as_list(p.get("accessories")),
        "is_complete_outfit": bool(p.get("is_complete_outfit", False)),
        "styling_notes": _as_text(p.get("styling_notes")),
        "bounding_box": _normalise_box(p.get("bounding_box")),
        "selected": True,
        "piece_index": index,
    }


def _normalise_outfit(value: Any, pieces: list[dict[str, Any]]) -> dict[str, Any]:
    outfit = value if isinstance(value, dict) else {}
    default_name = " + ".join(p["name"] for p in pieces[:4]) or "Complete outfit"
    default_color = ", ".join(dict.fromkeys(p["color"] for p in pieces if p["color"] and p["color"] != "Not specified"))
    return {
        "name": (_as_text(outfit.get("name")) or default_name)[:120],
        "category": (_as_text(outfit.get("category")) or "Complete Outfit")[:80],
        "color": (_as_text(outfit.get("color")) or default_color or "Mixed")[:50],
        "aesthetic": _as_text(outfit.get("aesthetic"))[:120],
        "occasion": _as_text(outfit.get("occasion"))[:120],
        "season": _as_text(outfit.get("season"))[:120],
        "accessories": _as_list(outfit.get("accessories")),
        "styling_notes": _as_text(outfit.get("styling_notes")),
    }


def analyse_multigarment_image(raw: bytes) -> dict[str, Any]:
    """Call Vision AI and return a normalized multi-garment result."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY is missing. Add it in Render Environment Variables to enable Vision AI."}
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "The openai package is missing. Add openai to requirements.txt and redeploy."}

    try:
        ai_bytes, ai_mime = _ai_ready_bytes(raw)
    except Exception as exc:
        return {"error": f"Could not prepare image for AI: {exc}"}

    image_url = f"data:{ai_mime};base64,{base64.b64encode(ai_bytes).decode('utf-8')}"
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": MULTI_GARMENT_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                ],
            }],
            response_format={"type": "json_object"},
            temperature=0.15,
            max_tokens=2200,
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": f"AI analysis failed: {exc}"}

    pieces_raw = data.get("pieces") if isinstance(data.get("pieces"), list) else []
    pieces = [_normalise_piece(p, i) for i, p in enumerate(pieces_raw[:12])]
    is_clothing = bool(data.get("is_clothing_image", bool(pieces)))
    if is_clothing and not pieces:
        return {"error": "AI recognised fashion in the photo but could not separate a clear wardrobe item. Try a clearer photo."}

    kind = _as_text(data.get("source_kind"))
    if kind not in {"single_piece", "multi_piece", "one_piece_outfit"}:
        kind = "multi_piece" if len(pieces) > 1 else ("one_piece_outfit" if pieces and pieces[0]["is_complete_outfit"] else "single_piece")

    return {
        "is_clothing_image": is_clothing,
        "confidence": max(0, min(int(float(data.get("confidence", 0) or 0)), 100)),
        "rejection_reason": _as_text(data.get("rejection_reason")),
        "source_kind": kind,
        "pieces": pieces,
        "outfit": _normalise_outfit(data.get("outfit"), pieces),
        "recommended_save_mode": "separate",
    }


def _crop_piece(raw: bytes, box: dict[str, int] | None, user_id: int, source_ext: str, index: int) -> str | None:
    if not box:
        return None
    try:
        with Image.open(BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image)
            width, height = image.size
            x1 = int(width * box["x"] / 1000)
            y1 = int(height * box["y"] / 1000)
            x2 = int(width * (box["x"] + box["width"]) / 1000)
            y2 = int(height * (box["y"] + box["height"]) / 1000)
            # A little breathing room so sleeves/waistbands are not clipped.
            pad_x = max(8, int((x2 - x1) * .05))
            pad_y = max(8, int((y2 - y1) * .05))
            x1, y1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
            x2, y2 = min(width, x2 + pad_x), min(height, y2 + pad_y)
            crop = image.crop((x1, y1, x2, y2))
            if crop.mode not in ("RGB", "L"):
                crop = crop.convert("RGB")
            elif crop.mode == "L":
                crop = crop.convert("RGB")
            out = BytesIO()
            crop.save(out, format="JPEG", quality=90, optimize=True)
            path = f"ai_piece_crops/{user_id}/{uuid.uuid4().hex}_{index}.jpg"
            return default_storage.save(path, ContentFile(out.getvalue()))
    except Exception:
        return None


def analyse_and_store(raw: bytes, user_id: int) -> dict[str, Any]:
    """Validate, analyse, save original and piece crops; never saves wardrobe rows."""
    try:
        _mime, ext = validate_image_bytes(raw)
    except ValueError as exc:
        return {"error": str(exc)}

    result = analyse_multigarment_image(raw)
    if result.get("error") or not result.get("is_clothing_image", True):
        return result

    source_path = default_storage.save(
        f"ai_sources/{user_id}/{uuid.uuid4().hex}{ext}", ContentFile(raw)
    )
    result["source_image_path"] = source_path
    try:
        result["source_image_url"] = default_storage.url(source_path)
    except Exception:
        result["source_image_url"] = ""

    for index, piece in enumerate(result["pieces"]):
        crop_path = _crop_piece(raw, piece.get("bounding_box"), user_id, ext, index)
        piece_path = crop_path or source_path
        piece["image_path"] = piece_path
        try:
            piece["image_url"] = default_storage.url(piece_path)
        except Exception:
            piece["image_url"] = result.get("source_image_url", "")
    return result


def _piece_from_payload(data: dict[str, Any], index: int) -> dict[str, Any]:
    normalized = _normalise_piece(data, index)
    normalized["image_path"] = _as_text(data.get("image_path"))
    normalized["selected"] = data.get("selected", True) not in (False, "false", "0", 0)
    return normalized


def save_multigarment_selection(
    *,
    user,
    source_image_path: str,
    pieces_payload: list[dict[str, Any]],
    outfit_payload: dict[str, Any] | None,
    save_mode: str = "separate",
    source_type: str = "ai_add",
) -> tuple[OutfitGroup | None, list[ClothingItem]]:
    """Persist reviewed pieces and optionally a whole-look card."""
    save_mode = save_mode if save_mode in {"separate", "outfit", "both"} else "separate"
    pieces = [_piece_from_payload(p, i) for i, p in enumerate(pieces_payload or [])]
    selected = [p for p in pieces if p.get("selected")]
    if save_mode in {"separate", "both"} and not selected:
        raise ValueError("Select at least one detected piece to save.")

    # Do not accept arbitrary storage paths from another user's AI session.
    expected_source_prefix = f"ai_sources/{user.id}/"
    if source_image_path and not source_image_path.startswith(expected_source_prefix):
        raise ValueError("Invalid AI source image. Please analyse the photo again.")

    outfit = _normalise_outfit(outfit_payload or {}, selected or pieces)
    group_needed = bool(source_image_path) and (len(selected or pieces) > 1 or save_mode in {"outfit", "both"})
    group = None
    if group_needed:
        group = OutfitGroup.objects.create(
            user=user,
            name=outfit["name"] or "Original look",
            source_type=source_type,
            original_image=source_image_path or None,
            notes=outfit.get("styling_notes", ""),
        )

    created: list[ClothingItem] = []
    if save_mode in {"separate", "both"}:
        for index, p in enumerate(selected):
            image_path = p.get("image_path") or source_image_path
            if image_path and not (
                image_path.startswith(f"ai_piece_crops/{user.id}/")
                or image_path.startswith(expected_source_prefix)
            ):
                image_path = source_image_path
            created.append(ClothingItem.objects.create(
                user=user,
                name=p["name"],
                category=p["category"],
                color=p["color"],
                image=image_path or None,
                tags=_as_text(p.get("tags")),
                garment_type=p.get("garment_type", ""),
                aesthetic=p.get("aesthetic", ""),
                fit_silhouette=p.get("fit_silhouette", ""),
                occasion=p.get("occasion", ""),
                season=p.get("season", ""),
                accessories=_as_text(p.get("accessories")),
                styling_notes=p.get("styling_notes", ""),
                is_complete_outfit=bool(p.get("is_complete_outfit")),
                outfit_group=group,
                source_item_index=index,
            ))

    if save_mode in {"outfit", "both"}:
        created.append(ClothingItem.objects.create(
            user=user,
            name=outfit["name"] or "Complete outfit",
            category=outfit["category"] or "Complete Outfit",
            color=outfit["color"] or "Mixed",
            image=source_image_path or None,
            tags=", ".join(p["name"] for p in selected or pieces),
            garment_type="Complete outfit",
            aesthetic=outfit.get("aesthetic", ""),
            occasion=outfit.get("occasion", ""),
            season=outfit.get("season", ""),
            accessories=_as_text(outfit.get("accessories")),
            styling_notes=outfit.get("styling_notes", ""),
            is_complete_outfit=True,
            outfit_group=group,
            source_item_index=None,
        ))

    return group, created
