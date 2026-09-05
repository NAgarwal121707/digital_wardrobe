import base64
import json
import os
import uuid

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from wardrobe.forms import ClothingItemForm, WishlistItemForm
from wardrobe.models import ClothingItem, OutfitGroup, WishlistItem
from .ai_multigarment import analyse_and_store, save_multigarment_selection

from .forms import LoginForm, RegisterForm


AI_STYLIST_PROMPT = """
You are a professional AI fashion stylist with visual understanding.
Analyze the uploaded clothing image visually.

Return ONLY valid JSON with these keys:
{
  "is_clothing_image": true,
  "confidence": 0,
  "rejection_reason": "",
  "name": "short natural item name",
  "category": "custom but simple category",
  "color": "main visible colors",
  "tags": ["tag 1", "tag 2", "tag 3"],
  "garment_type": "specific garment type",
  "aesthetic": "fashion vibe",
  "fit_silhouette": "fit and silhouette",
  "occasion": "best occasion",
  "season": "best season",
  "accessories": ["accessory 1", "accessory 2", "accessory 3"],
  "is_complete_outfit": true or false,
  "styling_notes": "3-5 useful stylist sentences"
}

Rules:
- If the image is not clearly clothing, outfit, footwear, bag, or fashion accessory, return is_clothing_image=false and explain rejection_reason.
- Be visually specific. Do not give generic styling lines.
- Do not invent luxury brands.
- If the image has jeans + top or multiple main garments worn together, treat it as a two-piece outfit or complete outfit and mention each piece in tags.
- If it is a complete outfit like saree, gown, lehenga, jumpsuit, dress, co-ord set, or frock, do not force clothing pairings. Suggest accessories, footwear, layering, hairstyle, and occasion styling.
- If it is a pairable item like shirt, top, jeans, skirt, trouser, blazer, jacket, shoes, or bag, suggest realistic pairings.
- Keep name, category, and color short enough for a wardrobe form.
""".strip()


AI_WARDROBE_SCAN_PROMPT = """
You are a professional AI wardrobe scanner with strong visual understanding.
The user may upload 1 to 5 wardrobe/closet photos. Detect visible fashion items and return ONLY valid JSON.

Return format:
{
  "is_wardrobe_image": true,
  "rejection_reason": "",
  "items": [
    {
      "source_image_index": 0,
      "name": "short item name",
      "category": "simple custom category",
      "color": "main visible color",
      "tags": ["tag 1", "tag 2"],
      "garment_type": "specific garment type",
      "aesthetic": "fashion vibe",
      "fit_silhouette": "short fit/silhouette if visible",
      "occasion": "best occasion",
      "season": "best season",
      "accessories": ["accessory idea 1", "accessory idea 2"],
      "is_complete_outfit": false,
      "styling_notes": "1-2 short useful styling lines"
    }
  ]
}

Rules:
- Detect multiple visible clothes, footwear, bags, or fashion accessories.
- If the photo is not a wardrobe/closet/clothing/fashion image, set is_wardrobe_image=false.
- Do not invent hidden items. Only list visible and reasonably identifiable items.
- If a rack/shelf is crowded, list the most clear items first.
- If multiple items are worn together as an outfit, create one Complete Outfit entry and mention pieces in tags.
- For hanging/shelf wardrobe photos, create separate entries for visible different garments.
- Avoid duplicate entries for the same obvious item.
- Keep each item short because user will review/edit before saving.
- source_image_index must be 0 for first uploaded image, 1 for second, etc.
""".strip()


AI_GALLERY_QUICK_ADD_PROMPT = """
You are a fashion-aware AI wardrobe assistant.
The user selected multiple photos from their phone gallery. Each photo may or may not be a wardrobe item.
Analyze each uploaded image independently and return ONLY valid JSON.

Return format:
{
  "items": [
    {
      "source_image_index": 0,
      "is_clothing_image": true,
      "confidence": 0,
      "rejection_reason": "",
      "name": "short item name",
      "category": "simple custom category",
      "color": "main visible color",
      "tags": ["tag 1", "tag 2"],
      "garment_type": "specific garment type",
      "aesthetic": "fashion vibe",
      "fit_silhouette": "short fit/silhouette if visible",
      "occasion": "best occasion",
      "season": "best season",
      "accessories": ["accessory idea 1", "accessory idea 2"],
      "is_complete_outfit": false,
      "styling_notes": "one short practical styling line"
    }
  ]
}

Rules:
- Return exactly one item object per uploaded image.
- If an image is not clothing, footwear, bag, jewelry, accessory, or outfit, set is_clothing_image=false.
- Do not guess from unclear/blurred/non-fashion images.
- If image contains a full outfit or two main garments together, set category as Complete Outfit or Two-piece Outfit and mention pieces in tags.
- Keep output short because user will swipe right to save or left to skip.
- confidence must be 0-100.
""".strip()


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("email", "An account with this email already exists.")
        else:
            login(request, user)
            return redirect("dashboard")
    return render(request, "register.html", {"form": form})


@login_required(login_url="login")
def dashboard_view(request):
    clothing_items = ClothingItem.objects.filter(user=request.user)
    wishlist_items = WishlistItem.objects.filter(user=request.user, is_purchased=False)
    categories = (
        clothing_items.values("category")
        .annotate(item_count=Count("id"))
        .order_by("category")
    )
    return render(
        request,
        "dashboard.html",
        {
            "clothing_items": clothing_items,
            "categories": categories,
            "wishlist_items": wishlist_items[:4],
            "wishlist_count": wishlist_items.count(),
            "total_items": clothing_items.count(),
            "total_categories": categories.count(),
            "total_outfits": OutfitGroup.objects.filter(user=request.user).count(),
        },
    )


@login_required(login_url="login")
def clothing_item_detail_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)

    related_items = (
        ClothingItem.objects.filter(user=request.user, category=clothing_item.category)
        .exclude(id=clothing_item.id)[:4]
    )

    outfit_group = clothing_item.outfit_group
    paired_items = (
        outfit_group.pieces.exclude(id=clothing_item.id)[:8]
        if outfit_group else []
    )
    return render(
        request,
        "clothing_item_detail.html",
        {
            "clothing_item": clothing_item,
            "related_items": related_items,
            "outfit_group": outfit_group,
            "paired_items": paired_items,
        },
    )


@login_required(login_url="login")
def add_clothing_item_view(request):
    return render(request, "add_clothing_item.html")


@login_required(login_url="login")
def add_clothing_item_manual_view(request):
    if request.method == "POST":
        form = ClothingItemForm(request.POST, request.FILES)
        if form.is_valid():
            clothing_item = form.save(commit=False)
            clothing_item.user = request.user
            clothing_item.save()
            messages.success(request, "Clothing item added successfully.")
            return redirect("dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ClothingItemForm()
    return render(request, "add_clothing_item_manual.html", {"form": form})


def _analyze_clothing_image(image_bytes, content_type):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "error": "OPENAI_API_KEY is missing on Render. Add it in Environment Variables to enable Vision AI.",
        }

    try:
        from openai import OpenAI
    except ImportError:
        return {
            "error": "The openai package is missing. Add openai to requirements.txt and redeploy.",
        }

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:{content_type};base64,{encoded_image}"

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": AI_STYLIST_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url,
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=700,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception as exc:
        return {"error": f"AI analysis failed: {exc}"}

    return {
        "is_clothing_image": bool(data.get("is_clothing_image", True)),
        "confidence": data.get("confidence", 0),
        "rejection_reason": str(data.get("rejection_reason") or "").strip(),
        "name": str(data.get("name") or "").strip(),
        "category": str(data.get("category") or "").strip(),
        "color": str(data.get("color") or "").strip(),
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
        "garment_type": str(data.get("garment_type") or "").strip(),
        "aesthetic": str(data.get("aesthetic") or "").strip(),
        "fit_silhouette": str(data.get("fit_silhouette") or "").strip(),
        "occasion": str(data.get("occasion") or "").strip(),
        "season": str(data.get("season") or "").strip(),
        "accessories": data.get("accessories") if isinstance(data.get("accessories"), list) else [],
        "is_complete_outfit": bool(data.get("is_complete_outfit")),
        "styling_notes": str(data.get("styling_notes") or "").strip(),
    }



def _analyze_wardrobe_scan_images(image_payloads):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "error": "OPENAI_API_KEY is missing. Add it in Render Environment Variables to enable AI wardrobe scanning.",
        }

    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "The openai package is missing. Add openai to requirements.txt and redeploy."}

    content = [{"type": "text", "text": AI_WARDROBE_SCAN_PROMPT}]
    for payload in image_payloads:
        encoded_image = base64.b64encode(payload["bytes"]).decode("utf-8")
        image_data_url = f"data:{payload['content_type']};base64,{encoded_image}"
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_data_url, "detail": "high"},
            }
        )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2200,
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": f"AI wardrobe scan failed: {exc}"}

    items = data.get("items") if isinstance(data.get("items"), list) else []
    cleaned_items = []
    for item in items[:40]:
        if not isinstance(item, dict):
            continue
        try:
            source_index = int(item.get("source_image_index", 0))
        except (TypeError, ValueError):
            source_index = 0
        cleaned_items.append(
            {
                "source_image_index": max(0, min(source_index, len(image_payloads) - 1)),
                "name": str(item.get("name") or "").strip(),
                "category": str(item.get("category") or "Uncategorized").strip(),
                "color": str(item.get("color") or "Not specified").strip(),
                "tags": ", ".join(item.get("tags", [])) if isinstance(item.get("tags"), list) else str(item.get("tags") or ""),
                "garment_type": str(item.get("garment_type") or "").strip(),
                "aesthetic": str(item.get("aesthetic") or "").strip(),
                "fit_silhouette": str(item.get("fit_silhouette") or "").strip(),
                "occasion": str(item.get("occasion") or "").strip(),
                "season": str(item.get("season") or "").strip(),
                "accessories": ", ".join(item.get("accessories", [])) if isinstance(item.get("accessories"), list) else str(item.get("accessories") or ""),
                "is_complete_outfit": bool(item.get("is_complete_outfit")),
                "styling_notes": str(item.get("styling_notes") or "").strip(),
            }
        )

    return {
        "is_wardrobe_image": bool(data.get("is_wardrobe_image", True)),
        "rejection_reason": str(data.get("rejection_reason") or "").strip(),
        "items": cleaned_items,
    }


@login_required(login_url="login")
def scan_wardrobe_ai_view(request):
    """Website bulk builder. Images are analysed sequentially to limit memory."""
    context = {"detected_items": [], "image_urls": [], "source_summaries": []}

    if request.method == "POST" and request.POST.get("action") == "save_detected_items":
        selected_indexes = request.POST.getlist("selected_items")
        save_mode = request.POST.get("save_mode", "separate")
        grouped = {}
        for index in selected_indexes:
            prefix = f"item_{index}_"
            name = request.POST.get(prefix + "name", "").strip()
            if len(name) < 2:
                continue
            source_path = request.POST.get(prefix + "source_image_path", "").strip()
            piece = {
                "selected": True,
                "name": name,
                "category": request.POST.get(prefix + "category", "").strip() or "Uncategorized",
                "color": request.POST.get(prefix + "color", "").strip() or "Not specified",
                "image_path": request.POST.get(prefix + "image_path", "").strip(),
                "tags": request.POST.get(prefix + "tags", "").strip(),
                "garment_type": request.POST.get(prefix + "garment_type", "").strip(),
                "aesthetic": request.POST.get(prefix + "aesthetic", "").strip(),
                "fit_silhouette": request.POST.get(prefix + "fit_silhouette", "").strip(),
                "occasion": request.POST.get(prefix + "occasion", "").strip(),
                "season": request.POST.get(prefix + "season", "").strip(),
                "accessories": request.POST.get(prefix + "accessories", "").strip(),
                "styling_notes": request.POST.get(prefix + "styling_notes", "").strip(),
                "is_complete_outfit": request.POST.get(prefix + "is_complete_outfit") == "true",
            }
            grouped.setdefault(source_path, {"pieces": [], "outfit": {}})["pieces"].append(piece)
            try:
                grouped[source_path]["outfit"] = json.loads(request.POST.get(prefix + "outfit_json", "{}"))
            except json.JSONDecodeError:
                pass

        saved_count = 0
        for source_path, group_data in grouped.items():
            try:
                _, created = save_multigarment_selection(
                    user=request.user,
                    source_image_path=source_path,
                    pieces_payload=group_data["pieces"],
                    outfit_payload=group_data["outfit"],
                    save_mode=save_mode,
                    source_type="wardrobe_scan",
                )
                saved_count += len(created)
            except ValueError as exc:
                messages.error(request, str(exc))

        if saved_count:
            messages.success(request, f"Saved {saved_count} wardrobe item{'s' if saved_count != 1 else ''}.")
            return redirect("dashboard")
        messages.error(request, "Please select at least one detected item to save.")
        return render(request, "scan_wardrobe_ai.html", context)

    if request.method == "POST":
        uploaded_images = request.FILES.getlist("images")
        if not uploaded_images:
            messages.error(request, "Please upload 1 to 5 wardrobe photos.")
            return render(request, "scan_wardrobe_ai.html", context)
        if len(uploaded_images) > 5:
            messages.error(request, "Please upload maximum 5 photos at once.")
            return render(request, "scan_wardrobe_ai.html", context)

        detected_items = []
        image_urls = []
        rejected = 0
        for source_index, uploaded_image in enumerate(uploaded_images):
            if uploaded_image.size > 8 * 1024 * 1024:
                messages.warning(request, f"Skipped {uploaded_image.name}: image is over 8 MB.")
                rejected += 1
                continue
            raw = uploaded_image.read()
            result = analyse_and_store(raw, request.user.id)
            if result.get("error"):
                messages.warning(request, f"Skipped {uploaded_image.name}: {result['error']}")
                rejected += 1
                continue
            if not result.get("is_clothing_image", True):
                messages.warning(request, result.get("rejection_reason") or f"Skipped {uploaded_image.name}: no fashion item found.")
                rejected += 1
                continue

            source_url = result.get("source_image_url", "")
            if source_url:
                image_urls.append(source_url)
            outfit = result.get("outfit", {})
            for piece in result.get("pieces", []):
                row = dict(piece)
                row.update({
                    "review_index": len(detected_items),
                    "source_image_index": source_index,
                    "source_image_path": result.get("source_image_path", ""),
                    "source_image_url": source_url,
                    "outfit": outfit,
                    "outfit_json": json.dumps(outfit),
                    "tags": ", ".join(piece.get("tags", [])) if isinstance(piece.get("tags"), list) else str(piece.get("tags") or ""),
                    "accessories": ", ".join(piece.get("accessories", [])) if isinstance(piece.get("accessories"), list) else str(piece.get("accessories") or ""),
                })
                detected_items.append(row)

        context["detected_items"] = detected_items
        context["image_urls"] = image_urls
        context["rejected_count"] = rejected
        if detected_items:
            messages.success(request, f"AI found {len(detected_items)} reusable wardrobe piece{'s' if len(detected_items) != 1 else ''}. Review before saving.")
        elif not rejected:
            messages.error(request, "AI could not confidently detect wardrobe items. Try clearer photos.")

    return render(request, "scan_wardrobe_ai.html", context)


@login_required(login_url="login")
def add_clothing_item_ai_view(request):
    context = {"analysis": None, "image_path": "", "image_url": ""}

    if request.method == "POST" and request.POST.get("action") == "save_ai_items":
        source_path = request.POST.get("source_image_path", "").strip()
        save_mode = request.POST.get("save_mode", "separate")
        try:
            piece_count = int(request.POST.get("piece_count", "0"))
        except ValueError:
            piece_count = 0
        pieces = []
        for i in range(max(0, min(piece_count, 12))):
            prefix = f"piece_{i}_"
            pieces.append({
                "selected": request.POST.get(prefix + "selected") == "on",
                "name": request.POST.get(prefix + "name", "").strip(),
                "category": request.POST.get(prefix + "category", "").strip(),
                "color": request.POST.get(prefix + "color", "").strip(),
                "image_path": request.POST.get(prefix + "image_path", "").strip(),
                "tags": request.POST.get(prefix + "tags", "").strip(),
                "garment_type": request.POST.get(prefix + "garment_type", "").strip(),
                "aesthetic": request.POST.get(prefix + "aesthetic", "").strip(),
                "fit_silhouette": request.POST.get(prefix + "fit_silhouette", "").strip(),
                "occasion": request.POST.get(prefix + "occasion", "").strip(),
                "season": request.POST.get(prefix + "season", "").strip(),
                "accessories": request.POST.get(prefix + "accessories", "").strip(),
                "styling_notes": request.POST.get(prefix + "styling_notes", "").strip(),
                "is_complete_outfit": request.POST.get(prefix + "is_complete_outfit") == "true",
            })
        try:
            outfit = json.loads(request.POST.get("outfit_json", "{}"))
        except json.JSONDecodeError:
            outfit = {}
        # Allow user to edit the whole-look name on the review screen.
        outfit["name"] = request.POST.get("outfit_name", outfit.get("name", "")).strip()
        outfit["styling_notes"] = request.POST.get("outfit_styling_notes", outfit.get("styling_notes", "")).strip()
        try:
            _, created = save_multigarment_selection(
                user=request.user,
                source_image_path=source_path,
                pieces_payload=pieces,
                outfit_payload=outfit,
                save_mode=save_mode,
                source_type="ai_add",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Saved {len(created)} wardrobe item{'s' if len(created) != 1 else ''}. The original look is remembered for future styling.")
            return redirect("dashboard")

    elif request.method == "POST":
        uploaded_image = request.FILES.get("image")
        if not uploaded_image:
            messages.error(request, "Please upload a clothing image first.")
            return render(request, "add_clothing_item_ai.html", context)
        if uploaded_image.size > 8 * 1024 * 1024:
            messages.error(request, "Image size must be less than 8 MB.")
            return render(request, "add_clothing_item_ai.html", context)

        result = analyse_and_store(uploaded_image.read(), request.user.id)
        if result.get("error"):
            messages.error(request, result["error"])
        elif not result.get("is_clothing_image", True):
            messages.error(request, result.get("rejection_reason") or "Please upload a clear fashion image.")
        else:
            result["outfit_json"] = json.dumps(result.get("outfit", {}))
            context.update({
                "analysis": result,
                "image_path": result.get("source_image_path", ""),
                "image_url": result.get("source_image_url", ""),
            })
            messages.success(request, f"AI found {len(result.get('pieces', []))} wardrobe piece{'s' if len(result.get('pieces', [])) != 1 else ''}. Review each piece before saving.")

    return render(request, "add_clothing_item_ai.html", context)


def _analyze_gallery_quick_add_images(image_payloads, user_id):
    """Analyse each selected gallery photo one-by-one; one photo may yield many pieces."""
    items = []
    rejected = 0
    for source_index, payload in enumerate(image_payloads):
        result = analyse_and_store(payload["bytes"], user_id)
        if result.get("error"):
            return {"error": result["error"]}
        if not result.get("is_clothing_image", True):
            rejected += 1
            continue
        outfit = result.get("outfit", {})
        for piece in result.get("pieces", []):
            row = dict(piece)
            row.update({
                "source_image_index": source_index,
                "source_image_path": result.get("source_image_path", ""),
                "source_image_url": result.get("source_image_url", ""),
                "outfit": outfit,
                "outfit_json": json.dumps(outfit),
                "is_clothing_image": True,
                "confidence": result.get("confidence", 0),
                "tags": ", ".join(piece.get("tags", [])) if isinstance(piece.get("tags"), list) else str(piece.get("tags") or ""),
                "accessories": ", ".join(piece.get("accessories", [])) if isinstance(piece.get("accessories"), list) else str(piece.get("accessories") or ""),
            })
            items.append(row)
    return {"items": items, "rejected_count": rejected}


@login_required(login_url="login")
def quick_add_gallery_view(request):
    context = {"gallery_items": []}

    if request.method == "POST" and request.POST.get("action") == "save_swiped_items":
        selected_indexes = request.POST.getlist("selected_items")
        save_mode = request.POST.get("save_mode", "separate")
        grouped = {}
        for index in selected_indexes:
            prefix = f"item_{index}_"
            source_path = request.POST.get(prefix + "source_image_path", "").strip()
            name = request.POST.get(prefix + "name", "").strip()
            if len(name) < 2:
                continue
            piece = {
                "selected": True,
                "name": name,
                "category": request.POST.get(prefix + "category", "").strip() or "Uncategorized",
                "color": request.POST.get(prefix + "color", "").strip() or "Not specified",
                "image_path": request.POST.get(prefix + "image_path", "").strip(),
                "tags": request.POST.get(prefix + "tags", "").strip(),
                "garment_type": request.POST.get(prefix + "garment_type", "").strip(),
                "aesthetic": request.POST.get(prefix + "aesthetic", "").strip(),
                "fit_silhouette": request.POST.get(prefix + "fit_silhouette", "").strip(),
                "occasion": request.POST.get(prefix + "occasion", "").strip(),
                "season": request.POST.get(prefix + "season", "").strip(),
                "accessories": request.POST.get(prefix + "accessories", "").strip(),
                "styling_notes": request.POST.get(prefix + "styling_notes", "").strip(),
                "is_complete_outfit": request.POST.get(prefix + "is_complete_outfit") == "true",
            }
            group = grouped.setdefault(source_path, {"pieces": [], "outfit": {}})
            group["pieces"].append(piece)
            try:
                group["outfit"] = json.loads(request.POST.get(prefix + "outfit_json", "{}"))
            except json.JSONDecodeError:
                pass

        saved_count = 0
        for source_path, data in grouped.items():
            try:
                _, created = save_multigarment_selection(
                    user=request.user,
                    source_image_path=source_path,
                    pieces_payload=data["pieces"],
                    outfit_payload=data["outfit"],
                    save_mode=save_mode,
                    source_type="gallery",
                )
                saved_count += len(created)
            except ValueError as exc:
                messages.error(request, str(exc))
        if saved_count:
            messages.success(request, f"Saved {saved_count} wardrobe item{'s' if saved_count != 1 else ''} from gallery.")
            return redirect("dashboard")
        messages.error(request, "Swipe right on at least one detected piece before saving.")
        return render(request, "quick_add_gallery.html", context)

    if request.method == "POST":
        uploaded_images = request.FILES.getlist("images")
        if not uploaded_images:
            messages.error(request, "Please choose photos from your gallery first.")
            return render(request, "quick_add_gallery.html", context)
        if len(uploaded_images) > 20:
            messages.error(request, "Please choose maximum 20 photos at once.")
            return render(request, "quick_add_gallery.html", context)

        payloads = []
        for uploaded_image in uploaded_images:
            if uploaded_image.size > 8 * 1024 * 1024:
                messages.error(request, f"{uploaded_image.name} is over 8 MB.")
                return render(request, "quick_add_gallery.html", context)
            payloads.append({"bytes": uploaded_image.read(), "name": uploaded_image.name})

        result = _analyze_gallery_quick_add_images(payloads, request.user.id)
        if result.get("error"):
            messages.error(request, result["error"])
            return render(request, "quick_add_gallery.html", context)

        gallery_items = []
        for idx, item in enumerate(result.get("items", [])):
            item["review_index"] = idx
            gallery_items.append(item)
        context["gallery_items"] = gallery_items
        context["rejected_count"] = result.get("rejected_count", 0)
        messages.success(request, f"AI found {len(gallery_items)} reusable piece{'s' if len(gallery_items) != 1 else ''}. Swipe right to keep, left to skip.")

    return render(request, "quick_add_gallery.html", context)


@login_required(login_url="login")
def edit_clothing_item_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)
    if request.method == "POST":
        form = ClothingItemForm(request.POST, request.FILES, instance=clothing_item)
        if form.is_valid():
            form.save()
            messages.success(request, "Clothing item updated successfully.")
            return redirect("clothing_item_detail", item_id=clothing_item.id)
        messages.error(request, "Please correct the errors below.")
    else:
        form = ClothingItemForm(instance=clothing_item)
    return render(request, "edit_clothing_item.html", {"form": form, "clothing_item": clothing_item})


@login_required(login_url="login")
def delete_clothing_item_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)
    if request.method == "POST":
        clothing_item.delete()
        messages.success(request, "Clothing item deleted successfully.")
        return redirect("dashboard")
    return render(request, "delete_clothing_item.html", {"clothing_item": clothing_item})




def _wardrobe_context_for_ai(clothing_items):
    if not clothing_items.exists():
        return "User has no wardrobe items yet. Ask them to add clothes first."

    lines = []
    for item in clothing_items[:80]:
        details = [
            f"name: {item.name}",
            f"category: {item.category}",
            f"color: {item.color}",
        ]
        optional_fields = [
            ("tags", getattr(item, "tags", "")),
            ("garment_type", getattr(item, "garment_type", "")),
            ("aesthetic", getattr(item, "aesthetic", "")),
            ("fit", getattr(item, "fit_silhouette", "")),
            ("occasion", getattr(item, "occasion", "")),
            ("season", getattr(item, "season", "")),
            ("accessories", getattr(item, "accessories", "")),
            ("styling_notes", getattr(item, "styling_notes", "")),
        ]
        for label, value in optional_fields:
            value = str(value or "").strip()
            if value:
                details.append(f"{label}: {value}")
        if getattr(item, "is_complete_outfit", False):
            details.append("complete_outfit: yes")
        lines.append("- " + " | ".join(details))
    return "\n".join(lines)


def _local_stylist_reply(question, clothing_items):
    total = clothing_items.count()
    if total == 0:
        return (
            "Add at least 3-5 clothing items first so I can style from your actual wardrobe. "
            "Start with one top, one bottom, footwear, and one occasion piece."
        )

    first_items = list(clothing_items[:5])
    names = ", ".join([item.name for item in first_items])
    return (
        "I can see your saved wardrobe, but AI chat is not active yet because OPENAI_API_KEY is missing or quota is unavailable.\n\n"
        f"Quick closet-based idea: start with {first_items[0].name}, then match it with items in similar or neutral colors. "
        f"Some items I can use from your closet are: {names}.\n\n"
        "For full personal stylist answers, add API billing/credits and keep OPENAI_API_KEY in Render Environment Variables."
    )


def _generate_stylist_reply(question, clothing_items):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _local_stylist_reply(question, clothing_items)

    try:
        from openai import OpenAI
    except ImportError:
        return "The openai package is missing. Add openai to requirements.txt, redeploy, and try again."

    wardrobe_context = _wardrobe_context_for_ai(clothing_items)
    system_prompt = """
You are a warm, practical personal AI fashion stylist inside a digital wardrobe app.
Answer using the user's saved wardrobe context first.
Keep responses very short and visual-card friendly.
Use this format exactly:
✨ Style Summary: one short line
👗 Use from your wardrobe: item names from saved closet only
🧩 Add / Wishlist: missing pieces if needed
👜 Accessories: short accessories ideas
☀️ Best for: occasion + season/weather
Avoid long paragraphs. Never give generic advice. Never claim you can see live images in chat; use saved item data.
""".strip()

    user_prompt = f"""
User question:
{question}

Saved wardrobe items:
{wardrobe_context}
""".strip()

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_STYLIST_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.45,
            max_tokens=650,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        message = str(exc)
        if "insufficient_quota" in message or "429" in message:
            return (
                "AI stylist could not run because the OpenAI API quota/credits are unavailable. "
                "Add billing or credits in OpenAI Platform, then try again.\n\n"
                + _local_stylist_reply(question, clothing_items)
            )
        return f"AI stylist failed: {exc}"



def _visual_items_for_reply(question, assistant_reply, clothing_items):
    text_blob = f"{question} {assistant_reply}".lower()
    matched = []
    for item in clothing_items:
        checks = [item.name, item.category, item.color, getattr(item, "garment_type", ""), getattr(item, "tags", "")]
        if any(str(value or "").lower() and str(value or "").lower() in text_blob for value in checks):
            matched.append(item)
        if len(matched) >= 6:
            break
    if not matched:
        matched = list(clothing_items[:6])
    return matched


@login_required(login_url="login")
def stylist_view(request):
    clothing_items = ClothingItem.objects.filter(user=request.user)
    categories = (
        clothing_items.values("category")
        .annotate(item_count=Count("id"))
        .order_by("category")
    )
    colors = (
        clothing_items.values("color")
        .annotate(item_count=Count("id"))
        .order_by("color")
    )
    featured_items = clothing_items[:8]

    user_question = ""
    assistant_reply = ""

    if request.method == "POST":
        user_question = request.POST.get("question", "").strip()
        if len(user_question) < 3:
            messages.error(request, "Please ask a slightly longer styling question.")
        else:
            assistant_reply = _generate_stylist_reply(user_question, clothing_items)

    visual_suggestion_items = _visual_items_for_reply(user_question, assistant_reply, clothing_items) if assistant_reply else []

    if clothing_items.exists():
        suggestion = "Ask anything like: What should I wear for college, office, a party, winter, summer, or with one saved item?"
    else:
        suggestion = "Add a few wardrobe items first. Then your stylist can understand your closet better."

    suggested_questions = [
        "What should I wear today from my wardrobe?",
        "Create a casual outfit using my saved clothes.",
        "Suggest a party look from my closet.",
        "What accessories or footwear should I add?",
    ]

    return render(
        request,
        "stylist.html",
        {
            "suggestion": suggestion,
            "categories": categories,
            "colors": colors,
            "featured_items": featured_items,
            "user_question": user_question,
            "assistant_reply": assistant_reply,
            "visual_suggestion_items": visual_suggestion_items,
            "suggested_questions": suggested_questions,
            "total_items": clothing_items.count(),
        },
    )



@login_required(login_url="login")
def wishlist_view(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user)
    active_items = wishlist_items.filter(is_purchased=False)
    purchased_items = wishlist_items.filter(is_purchased=True)

    return render(
        request,
        "wishlist.html",
        {
            "wishlist_items": wishlist_items,
            "active_items": active_items,
            "purchased_items": purchased_items,
            "active_count": active_items.count(),
            "purchased_count": purchased_items.count(),
        },
    )


@login_required(login_url="login")
def add_wishlist_item_view(request):
    if request.method == "POST":
        form = WishlistItemForm(request.POST, request.FILES)
        if form.is_valid():
            wishlist_item = form.save(commit=False)
            wishlist_item.user = request.user
            wishlist_item.save()
            messages.success(request, "Wishlist item saved for future purchase.")
            return redirect("wishlist")
        messages.error(request, "Please correct the errors below.")
    else:
        initial = {
            "source": request.GET.get("source", "future_purchase"),
            "title": request.GET.get("title", ""),
            "category": request.GET.get("category", ""),
            "reason": request.GET.get("reason", ""),
        }
        form = WishlistItemForm(initial=initial)

    return render(request, "add_wishlist_item.html", {"form": form})


@login_required(login_url="login")
def save_ai_suggestion_to_wishlist_view(request):
    if request.method != "POST":
        return redirect("stylist")

    title = request.POST.get("title", "").strip() or "AI outfit suggestion"
    reason = request.POST.get("reason", "").strip()

    WishlistItem.objects.create(
        user=request.user,
        title=title[:140],
        category="AI Suggestion",
        reason=reason,
        source="ai_suggestion",
        priority="medium",
    )

    messages.success(request, "AI suggestion saved to your Wishlist.")
    return redirect("wishlist")


@login_required(login_url="login")
def toggle_wishlist_purchased_view(request, item_id):
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, user=request.user)

    if request.method == "POST":
        wishlist_item.is_purchased = not wishlist_item.is_purchased
        wishlist_item.save(update_fields=["is_purchased"])

        if wishlist_item.is_purchased:
            messages.success(request, "Marked as purchased.")
        else:
            messages.success(request, "Moved back to future purchases.")

    return redirect("wishlist")


@login_required(login_url="login")
def delete_wishlist_item_view(request, item_id):
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, user=request.user)

    if request.method == "POST":
        wishlist_item.delete()
        messages.success(request, "Wishlist item removed.")

    return redirect("wishlist")


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    return redirect("login")
