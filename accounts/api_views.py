from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os, uuid
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from .views import _analyze_clothing_image, _generate_stylist_reply, _visual_items_for_reply
from wardrobe.models import ClothingItem, WishlistItem


User = get_user_model()


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = str(request.data.get("email") or "").strip().lower()
        password = str(request.data.get("password") or "")

        if not email:
            return Response({"email": ["Email is required."]}, status=status.HTTP_400_BAD_REQUEST)

        if "@" not in email:
            return Response({"email": ["Enter a valid email address."]}, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            return Response({"password": ["Password is required."]}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"email": ["An account with this email already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_user = User(email=email)
        try:
            validate_password(password, user=temp_user)
        except ValidationError as exc:
            return Response({"password": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(email=email, password=password)

        return Response(
            {
                "message": "Account created successfully.",
                "user": {"id": user.id, "email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = str(request.data.get("email") or "").strip().lower()
        password = str(request.data.get("password") or "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request=request, username=email, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {"id": user.id, "email": user.email},
            },
            status=status.HTTP_200_OK,
        )



def _image_url(request, image_field):
    if not image_field:
        return None
    try:
        url = image_field.url
    except Exception:
        return None
    return request.build_absolute_uri(url) if url.startswith("/") else url


def _clothing_json(request, item):
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "color": item.color,
        "image_url": _image_url(request, item.image),
        "tags": item.tags,
        "garment_type": item.garment_type,
        "aesthetic": item.aesthetic,
        "fit_silhouette": item.fit_silhouette,
        "occasion": item.occasion,
        "season": item.season,
        "accessories": item.accessories,
        "styling_notes": item.styling_notes,
        "is_complete_outfit": item.is_complete_outfit,
        "created_at": item.created_at.isoformat(),
    }


def _wishlist_json(request, item):
    return {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "color": item.color,
        "image_url": _image_url(request, item.image),
        "reason": item.reason,
        "source": item.source,
        "priority": item.priority,
        "purchase_link": item.purchase_link,
        "expected_budget": item.expected_budget,
        "is_purchased": item.is_purchased,
        "created_at": item.created_at.isoformat(),
    }


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = ClothingItem.objects.filter(user=request.user)
        wishlist = WishlistItem.objects.filter(user=request.user, is_purchased=False)
        categories = list(
            items.values("category")
            .annotate(item_count=Count("id"))
            .order_by("category")
        )
        return Response({
            "user": {"id": request.user.id, "email": request.user.email},
            "stats": {
                "total_items": items.count(),
                "total_categories": len(categories),
                "wishlist_count": wishlist.count(),
                "total_outfits": items.filter(is_complete_outfit=True).count(),
            },
            "categories": categories,
            "recent_items": [_clothing_json(request, x) for x in items[:8]],
            "wishlist_preview": [_wishlist_json(request, x) for x in wishlist[:4]],
        })


class ClothingListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = ClothingItem.objects.filter(user=request.user)
        category = str(request.query_params.get("category") or "").strip()
        if category:
            items = items.filter(category__iexact=category)
        return Response({"items": [_clothing_json(request, x) for x in items]})


    def post(self, request):
        name = str(request.data.get("name") or "").strip()
        if len(name) < 2:
            return Response({"name": ["Item name must be at least 2 characters long."]}, status=400)
        item = ClothingItem.objects.create(
            user=request.user, name=name,
            category=str(request.data.get("category") or "Uncategorized").strip() or "Uncategorized",
            color=str(request.data.get("color") or "Not specified").strip() or "Not specified",
            image=request.FILES.get("image"),
            tags=str(request.data.get("tags") or "").strip(), garment_type=str(request.data.get("garment_type") or "").strip(),
            aesthetic=str(request.data.get("aesthetic") or "").strip(), fit_silhouette=str(request.data.get("fit_silhouette") or "").strip(),
            occasion=str(request.data.get("occasion") or "").strip(), season=str(request.data.get("season") or "").strip(),
            accessories=str(request.data.get("accessories") or "").strip(), styling_notes=str(request.data.get("styling_notes") or "").strip(),
            is_complete_outfit=str(request.data.get("is_complete_outfit") or "").lower() in ("true","1","yes"),
        )
        return Response(_clothing_json(request, item), status=201)


class ClothingDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, item_id):
        return ClothingItem.objects.filter(user=request.user, id=item_id).first()

    def get(self, request, item_id):
        item = self.get_object(request, item_id)
        if item is None:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_clothing_json(request, item))

    def patch(self, request, item_id):
        item = self.get_object(request, item_id)
        if item is None:
            return Response({"detail": "Item not found."}, status=404)
        for field in ["name","category","color","tags","garment_type","aesthetic","fit_silhouette","occasion","season","accessories","styling_notes"]:
            if field in request.data:
                setattr(item, field, str(request.data.get(field) or "").strip())
        if "is_complete_outfit" in request.data:
            item.is_complete_outfit = str(request.data.get("is_complete_outfit")).lower() in ("true","1","yes")
        if request.FILES.get("image"):
            item.image = request.FILES["image"]
        item.save()
        return Response(_clothing_json(request, item))

    def delete(self, request, item_id):
        item = self.get_object(request, item_id)
        if item is None:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = WishlistItem.objects.filter(user=request.user)
        return Response({"items": [_wishlist_json(request, x) for x in items]})

    def post(self, request):
        title = str(request.data.get("title") or "").strip()
        if len(title) < 2:
            return Response({"title": ["Wishlist item name must be at least 2 characters long."]}, status=400)
        item = WishlistItem.objects.create(
            user=request.user, title=title, category=str(request.data.get("category") or "").strip(),
            color=str(request.data.get("color") or "").strip(), image=request.FILES.get("image"),
            reason=str(request.data.get("reason") or "").strip(), source=str(request.data.get("source") or "future_purchase"),
            priority=str(request.data.get("priority") or "medium"), purchase_link=str(request.data.get("purchase_link") or "").strip(),
            expected_budget=str(request.data.get("expected_budget") or "").strip())
        return Response(_wishlist_json(request, item), status=201)


class WishlistDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, request, item_id):
        return WishlistItem.objects.filter(user=request.user, id=item_id).first()
    def patch(self, request, item_id):
        item=self.get_object(request,item_id)
        if not item: return Response({"detail":"Item not found."},status=404)
        for field in ["title","category","color","reason","source","priority","purchase_link","expected_budget"]:
            if field in request.data: setattr(item,field,str(request.data.get(field) or "").strip())
        if "is_purchased" in request.data: item.is_purchased=str(request.data.get("is_purchased")).lower() in ("true","1","yes")
        item.save(); return Response(_wishlist_json(request,item))
    def delete(self, request, item_id):
        item=self.get_object(request,item_id)
        if not item: return Response({"detail":"Item not found."},status=404)
        item.delete(); return Response(status=204)


class AIAnalyzeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response({"detail": "Please choose an image."}, status=400)

        if image.size > 5 * 1024 * 1024:
            return Response({"detail": "Image must be under 5 MB."}, status=400)

        # Flutter Web multipart uploads can arrive as application/octet-stream
        # even when the selected file is a valid JPG/PNG/WEBP. Validate the
        # actual image bytes instead of trusting the browser MIME header.
        raw = image.read()
        try:
            with Image.open(BytesIO(raw)) as detected_image:
                detected_format = (detected_image.format or "").upper()
        except (UnidentifiedImageError, OSError, ValueError):
            return Response(
                {"detail": "The selected file is not a valid image."},
                status=400,
            )

        mime_by_format = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        extension_by_format = {
            "JPEG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp",
        }

        content_type = mime_by_format.get(detected_format)
        if content_type is None:
            return Response(
                {"detail": "Only JPG, PNG or WEBP images are allowed."},
                status=400,
            )

        result = _analyze_clothing_image(raw, content_type)
        if result.get("error"):
            return Response(result, status=503)
        if not result.get("is_clothing_image", True):
            return Response(result, status=422)

        ext = extension_by_format[detected_format]
        path = default_storage.save(
            f"ai_clothing_uploads/{request.user.id}/{uuid.uuid4().hex}{ext}",
            ContentFile(raw),
        )
        result["image_path"] = path
        saved_url = default_storage.url(path)
        result["image_url"] = (
            request.build_absolute_uri(saved_url)
            if saved_url.startswith("/")
            else saved_url
        )
        return Response(result)


class AIStylistAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        question=str(request.data.get("question") or "").strip()
        if not question: return Response({"detail":"Ask me something about your wardrobe."},status=400)
        items=ClothingItem.objects.filter(user=request.user)
        reply=_generate_stylist_reply(question,items)
        visuals=_visual_items_for_reply(question,reply,items)
        return Response({"reply":reply,"items":[_clothing_json(request,x) for x in visuals]})

