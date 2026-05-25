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
You must answer using the user's saved wardrobe context first.
Do not give generic fashion advice unless the closet has no matching item.
If a suitable item is missing, say it clearly as a missing piece suggestion.
For every outfit suggestion, include:
- exact saved clothing items to use when possible
- occasion
- season/weather suitability
- accessories/footwear
- why the combination works
Keep answer friendly, concise, and useful on mobile.
Never claim you can see images live in this chat; use saved item data only.
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
            "suggested_questions": suggested_questions,
            "total_items": clothing_items.count(),
        },
    )


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    return redirect("login")
