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
from wardrobe.models import ClothingItem, WishlistItem

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
            "total_outfits": 0,
        },
    )


@login_required(login_url="login")
def clothing_item_detail_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)

    related_items = (
        ClothingItem.objects.filter(user=request.user, category=clothing_item.category)
        .exclude(id=clothing_item.id)[:4]
    )

    return render(
        request,
        "clothing_item_detail.html",
        {
            "clothing_item": clothing_item,
            "related_items": related_items,
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
    context = {"detected_items": [], "image_paths": [], "image_urls": []}

    if request.method == "POST" and request.POST.get("action") == "save_detected_items":
        selected_indexes = request.POST.getlist("selected_items")
        saved_count = 0

        for index in selected_indexes:
            prefix = f"item_{index}_"
            name = request.POST.get(prefix + "name", "").strip()
            if len(name) < 2:
                continue
            ClothingItem.objects.create(
                user=request.user,
                name=name,
                category=request.POST.get(prefix + "category", "").strip() or "Uncategorized",
                color=request.POST.get(prefix + "color", "").strip() or "Not specified",
                image=request.POST.get(prefix + "image_path", "").strip() or None,
                tags=request.POST.get(prefix + "tags", "").strip(),
                garment_type=request.POST.get(prefix + "garment_type", "").strip(),
                aesthetic=request.POST.get(prefix + "aesthetic", "").strip(),
                fit_silhouette=request.POST.get(prefix + "fit_silhouette", "").strip(),
                occasion=request.POST.get(prefix + "occasion", "").strip(),
                season=request.POST.get(prefix + "season", "").strip(),
                accessories=request.POST.get(prefix + "accessories", "").strip(),
                styling_notes=request.POST.get(prefix + "styling_notes", "").strip(),
                is_complete_outfit=request.POST.get(prefix + "is_complete_outfit") == "true",
            )
            saved_count += 1

        if saved_count:
            messages.success(request, f"Saved {saved_count} detected wardrobe item{'s' if saved_count != 1 else ''}.")
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

        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        image_payloads = []
        saved_paths = []
        image_urls = []

        for uploaded_image in uploaded_images:
            if getattr(uploaded_image, "content_type", "") not in allowed_types:
                messages.error(request, "Only JPG, PNG, or WEBP images are allowed.")
                return render(request, "scan_wardrobe_ai.html", context)
            if uploaded_image.size > 7 * 1024 * 1024:
                messages.error(request, "Each image must be less than 7 MB.")
                return render(request, "scan_wardrobe_ai.html", context)

            image_bytes = uploaded_image.read()
            ext = os.path.splitext(uploaded_image.name)[1] or ".jpg"
            safe_path = f"wardrobe_scans/{request.user.id}/{uuid.uuid4().hex}{ext}"
            saved_path = default_storage.save(safe_path, ContentFile(image_bytes))
            saved_paths.append(saved_path)
            image_urls.append(default_storage.url(saved_path))
            image_payloads.append(
                {"bytes": image_bytes, "content_type": uploaded_image.content_type, "saved_path": saved_path}
            )

        scan_result = _analyze_wardrobe_scan_images(image_payloads)
        if scan_result.get("error"):
            messages.error(request, scan_result["error"])
        elif not scan_result.get("is_wardrobe_image", True):
            messages.error(request, scan_result.get("rejection_reason") or "Please upload clear wardrobe or clothing photos.")
        elif not scan_result.get("items"):
            messages.error(request, "AI could not confidently detect clothing items. Try clearer, brighter wardrobe photos.")
        else:
            messages.success(request, f"AI detected {len(scan_result['items'])} possible wardrobe items. Review, edit, then save selected items.")
            detected_items = []
            for item in scan_result["items"]:
                source_index = item.get("source_image_index", 0)
                item["image_path"] = saved_paths[source_index] if saved_paths else ""
                item["image_url"] = image_urls[source_index] if image_urls else ""
                detected_items.append(item)
            context["detected_items"] = detected_items

        context["image_paths"] = saved_paths
        context["image_urls"] = image_urls

    return render(request, "scan_wardrobe_ai.html", context)


@login_required(login_url="login")
def add_clothing_item_ai_view(request):
    context = {
        "analysis": None,
        "image_path": "",
        "image_url": "",
    }

    if request.method == "POST" and request.POST.get("action") == "save_ai_item":
        image_path = request.POST.get("ai_image_path", "").strip()
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip() or "Uncategorized"
        color = request.POST.get("color", "").strip() or "Not specified"

        if len(name) < 2:
            messages.error(request, "Please add a valid item name before saving.")
            context.update(
                {
                    "analysis": request.POST,
                    "image_path": image_path,
                    "image_url": default_storage.url(image_path) if image_path else "",
                }
            )
            return render(request, "add_clothing_item_ai.html", context)

        ClothingItem.objects.create(
            user=request.user,
            name=name,
            category=category,
            color=color,
            image=image_path or None,
            tags=request.POST.get("tags", "").strip(),
            garment_type=request.POST.get("garment_type", "").strip(),
            aesthetic=request.POST.get("aesthetic", "").strip(),
            fit_silhouette=request.POST.get("fit_silhouette", "").strip(),
            occasion=request.POST.get("occasion", "").strip(),
            season=request.POST.get("season", "").strip(),
            accessories=request.POST.get("accessories", "").strip(),
            styling_notes=request.POST.get("styling_notes", "").strip(),
            is_complete_outfit=request.POST.get("is_complete_outfit") == "true",
        )
        messages.success(request, "AI-filled clothing item saved successfully.")
        return redirect("dashboard")

    if request.method == "POST":
        uploaded_image = request.FILES.get("image")
        if not uploaded_image:
            messages.error(request, "Please upload a clothing image first.")
            return render(request, "add_clothing_item_ai.html", context)

        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if getattr(uploaded_image, "content_type", "") not in allowed_types:
            messages.error(request, "Only JPG, PNG, or WEBP images are allowed.")
            return render(request, "add_clothing_item_ai.html", context)

        if uploaded_image.size > 5 * 1024 * 1024:
            messages.error(request, "Image size must be less than 5 MB.")
            return render(request, "add_clothing_item_ai.html", context)

        image_bytes = uploaded_image.read()
        ext = os.path.splitext(uploaded_image.name)[1] or ".jpg"
        safe_path = f"ai_clothing_uploads/{request.user.id}/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(safe_path, ContentFile(image_bytes))
        image_url = default_storage.url(saved_path)

        analysis = _analyze_clothing_image(image_bytes, uploaded_image.content_type)
        if analysis.get("error"):
            messages.error(request, analysis["error"])
        elif not analysis.get("is_clothing_image", True):
            messages.error(
                request,
                analysis.get("rejection_reason") or "Please upload a clear clothing, outfit, footwear, bag, or fashion accessory image.",
            )
            analysis = None
            saved_path = ""
            image_url = ""
        else:
            messages.success(request, "AI analyzed your image. Review the details and edit anything before saving.")

        context.update(
            {
                "analysis": analysis,
                "image_path": saved_path,
                "image_url": image_url,
            }
        )

    return render(request, "add_clothing_item_ai.html", context)


def _analyze_gallery_quick_add_images(image_payloads):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY is missing. Add it in Render Environment Variables to enable AI Quick Add."}

    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "The openai package is missing. Add openai to requirements.txt and redeploy."}

    content = [{"type": "text", "text": AI_GALLERY_QUICK_ADD_PROMPT}]
    for payload in image_payloads:
        encoded_image = base64.b64encode(payload["bytes"]).decode("utf-8")
        image_data_url = f"data:{payload['content_type']};base64,{encoded_image}"
        content.append({"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}})

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2600,
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": f"AI gallery analysis failed: {exc}"}

    raw_items = data.get("items") if isinstance(data.get("items"), list) else []
    normalized = []
    for pos, item in enumerate(raw_items[:len(image_payloads)]):
        if not isinstance(item, dict):
            item = {}
        try:
            source_index = int(item.get("source_image_index", pos))
        except (TypeError, ValueError):
            source_index = pos
        source_index = max(0, min(source_index, len(image_payloads) - 1))
        tags = item.get("tags", [])
        accessories = item.get("accessories", [])
        normalized.append(
            {
                "source_image_index": source_index,
                "is_clothing_image": bool(item.get("is_clothing_image", True)),
                "confidence": item.get("confidence", 0),
                "rejection_reason": str(item.get("rejection_reason") or "").strip(),
                "name": str(item.get("name") or "").strip(),
                "category": str(item.get("category") or "Uncategorized").strip(),
                "color": str(item.get("color") or "Not specified").strip(),
                "tags": ", ".join(tags) if isinstance(tags, list) else str(tags or ""),
                "garment_type": str(item.get("garment_type") or "").strip(),
                "aesthetic": str(item.get("aesthetic") or "").strip(),
                "fit_silhouette": str(item.get("fit_silhouette") or "").strip(),
                "occasion": str(item.get("occasion") or "").strip(),
                "season": str(item.get("season") or "").strip(),
                "accessories": ", ".join(accessories) if isinstance(accessories, list) else str(accessories or ""),
                "is_complete_outfit": bool(item.get("is_complete_outfit")),
                "styling_notes": str(item.get("styling_notes") or "").strip(),
            }
        )

    # Guarantee one review card per uploaded image even if AI returns fewer entries.
    existing_indexes = {item["source_image_index"] for item in normalized}
    for idx in range(len(image_payloads)):
        if idx not in existing_indexes:
            normalized.append(
                {
                    "source_image_index": idx,
                    "is_clothing_image": False,
                    "confidence": 0,
                    "rejection_reason": "AI could not confidently identify a clothing item in this photo.",
                    "name": "",
                    "category": "Uncategorized",
                    "color": "Not specified",
                    "tags": "",
                    "garment_type": "",
                    "aesthetic": "",
                    "fit_silhouette": "",
                    "occasion": "",
                    "season": "",
                    "accessories": "",
                    "is_complete_outfit": False,
                    "styling_notes": "",
                }
            )

    normalized.sort(key=lambda item: item["source_image_index"])
    return {"items": normalized}


@login_required(login_url="login")
def quick_add_gallery_view(request):
    context = {"gallery_items": []}

    if request.method == "POST" and request.POST.get("action") == "save_swiped_items":
        selected_indexes = request.POST.getlist("selected_items")
        saved_count = 0
        for index in selected_indexes:
            prefix = f"item_{index}_"
            name = request.POST.get(prefix + "name", "").strip()
            if len(name) < 2:
                continue
            ClothingItem.objects.create(
                user=request.user,
                name=name,
                category=request.POST.get(prefix + "category", "").strip() or "Uncategorized",
                color=request.POST.get(prefix + "color", "").strip() or "Not specified",
                image=request.POST.get(prefix + "image_path", "").strip() or None,
                tags=request.POST.get(prefix + "tags", "").strip(),
                garment_type=request.POST.get(prefix + "garment_type", "").strip(),
                aesthetic=request.POST.get(prefix + "aesthetic", "").strip(),
                fit_silhouette=request.POST.get(prefix + "fit_silhouette", "").strip(),
                occasion=request.POST.get(prefix + "occasion", "").strip(),
                season=request.POST.get(prefix + "season", "").strip(),
                accessories=request.POST.get(prefix + "accessories", "").strip(),
                styling_notes=request.POST.get(prefix + "styling_notes", "").strip(),
                is_complete_outfit=request.POST.get(prefix + "is_complete_outfit") == "true",
            )
            saved_count += 1

        if saved_count:
            messages.success(request, f"Saved {saved_count} gallery item{'s' if saved_count != 1 else ''} to your wardrobe.")
            return redirect("dashboard")
        messages.error(request, "Swipe right or select at least one clothing item before saving.")
        return render(request, "quick_add_gallery.html", context)

    if request.method == "POST":
        uploaded_images = request.FILES.getlist("images")
        if not uploaded_images:
            messages.error(request, "Please choose photos from your gallery first.")
            return render(request, "quick_add_gallery.html", context)
        if len(uploaded_images) > 20:
            messages.error(request, "Please choose maximum 20 photos at once for smooth AI review.")
            return render(request, "quick_add_gallery.html", context)

        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        image_payloads = []
        saved_paths = []
        image_urls = []

        for uploaded_image in uploaded_images:
            if getattr(uploaded_image, "content_type", "") not in allowed_types:
                messages.error(request, "Only JPG, PNG, or WEBP images are allowed.")
                return render(request, "quick_add_gallery.html", context)
            if uploaded_image.size > 7 * 1024 * 1024:
                messages.error(request, "Each image must be less than 7 MB.")
                return render(request, "quick_add_gallery.html", context)

            image_bytes = uploaded_image.read()
            ext = os.path.splitext(uploaded_image.name)[1] or ".jpg"
            safe_path = f"gallery_quick_add/{request.user.id}/{uuid.uuid4().hex}{ext}"
            saved_path = default_storage.save(safe_path, ContentFile(image_bytes))
            saved_paths.append(saved_path)
            image_urls.append(default_storage.url(saved_path))
            image_payloads.append({"bytes": image_bytes, "content_type": uploaded_image.content_type})

        result = _analyze_gallery_quick_add_images(image_payloads)
        if result.get("error"):
            messages.error(request, result["error"])
            return render(request, "quick_add_gallery.html", context)

        gallery_items = []
        for idx, item in enumerate(result.get("items", [])):
            source_index = item.get("source_image_index", idx)
            source_index = max(0, min(source_index, len(saved_paths) - 1))
            item["image_path"] = saved_paths[source_index]
            item["image_url"] = image_urls[source_index]
            item["review_index"] = idx
            gallery_items.append(item)

        clothing_count = sum(1 for item in gallery_items if item.get("is_clothing_image"))
        messages.success(request, f"AI reviewed {len(gallery_items)} photos. Swipe right to save clothes, left to skip. {clothing_count} look like fashion items.")
        context["gallery_items"] = gallery_items

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
