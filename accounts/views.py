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

from wardrobe.forms import ClothingItemForm
from wardrobe.models import ClothingItem

from .forms import LoginForm, RegisterForm


AI_STYLIST_PROMPT = """
You are a professional AI fashion stylist with visual understanding.
Analyze the uploaded clothing image visually.

Return ONLY valid JSON with these keys:
{
  "name": "short natural item name",
  "category": "custom but simple category",
  "color": "main visible colors",
  "tags": ["tag 1", "tag 2", "tag 3"],
  "garment_type": "specific garment type",
  "aesthetic": "fashion vibe",
  "fit_silhouette": "fit and silhouette",
  "occasion": "best occasion",
  "season": "best season",
  "is_complete_outfit": true or false,
  "styling_notes": "2-3 useful stylist sentences"
}

Rules:
- Be visually specific.
- Do not invent luxury brands.
- If it is a complete outfit like saree, gown, lehenga, jumpsuit, dress, or frock, do not force clothing pairings. Suggest accessories, footwear, layering, hairstyle, and occasion styling.
- If it is a pairable item like shirt, top, jeans, skirt, trouser, blazer, jacket, shoes, or bag, suggest realistic pairings.
- Keep name, category, and color short enough for a wardrobe form.
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
        "name": str(data.get("name") or "").strip(),
        "category": str(data.get("category") or "").strip(),
        "color": str(data.get("color") or "").strip(),
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
        "garment_type": str(data.get("garment_type") or "").strip(),
        "aesthetic": str(data.get("aesthetic") or "").strip(),
        "fit_silhouette": str(data.get("fit_silhouette") or "").strip(),
        "occasion": str(data.get("occasion") or "").strip(),
        "season": str(data.get("season") or "").strip(),
        "is_complete_outfit": bool(data.get("is_complete_outfit")),
        "styling_notes": str(data.get("styling_notes") or "").strip(),
    }


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
    featured_items = clothing_items[:6]

    if clothing_items.exists():
        suggestion = (
            "Pick one favorite item, then build around its color and occasion. "
            "Soon this page can become your full AI personal stylist chatbot."
        )
    else:
        suggestion = (
            "Add a few wardrobe items first. Then your stylist can understand your closet better."
        )

    return render(
        request,
        "stylist.html",
        {
            "suggestion": suggestion,
            "categories": categories,
            "colors": colors,
            "featured_items": featured_items,
        },
    )


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    return redirect("login")
