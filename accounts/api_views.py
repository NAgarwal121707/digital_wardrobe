from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
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
from .views import _generate_stylist_reply, _visual_items_for_reply
from wardrobe.models import ClothingItem, OutfitGroup, WishlistItem
from .ai_multigarment import analyse_and_store, save_multigarment_selection


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
        "outfit_group_id": item.outfit_group_id,
        "outfit_group_name": item.outfit_group.name if item.outfit_group_id else "",
        "original_look_url": _image_url(request, item.outfit_group.original_image) if item.outfit_group_id else None,
        "paired_with": [
            {"id": other.id, "name": other.name, "category": other.category, "image_url": _image_url(request, other.image)}
            for other in (item.outfit_group.pieces.exclude(id=item.id)[:6] if item.outfit_group_id else [])
        ],
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
                "total_outfits": OutfitGroup.objects.filter(user=request.user).count(),
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
        if image.size > 8 * 1024 * 1024:
            return Response({"detail": "Image must be under 8 MB."}, status=400)

        raw = image.read()
        # IMPORTANT: this is the same shared Vision pipeline used by the
        # Django website AI Add / Quick Gallery / Wardrobe Scanner. Flutter
        # never runs a second prompt or a separate garment classifier.
        result = analyse_and_store(raw, request.user.id)
        if result.get("error"):
            return Response(result, status=503 if "AI" in result.get("error", "") else 400)
        if not result.get("is_clothing_image", True):
            return Response(result, status=422)

        # Convert storage-relative URLs to absolute URLs for Flutter web/mobile.
        for key in ("source_image_url",):
            url = result.get(key)
            if url and str(url).startswith("/"):
                result[key] = request.build_absolute_uri(url)
        for piece in result.get("pieces", []):
            url = piece.get("image_url")
            if url and str(url).startswith("/"):
                piece["image_url"] = request.build_absolute_uri(url)

        # Flutter should not have to trust/interpret Cloudinary storage paths.
        # The token proves that these paths were generated by this server for
        # this authenticated user during this AI analysis.
        allowed_paths = [
            str(result.get("source_image_path") or "").strip(),
            *[str(piece.get("image_path") or "").strip() for piece in result.get("pieces", [])],
        ]
        allowed_paths = [path for path in allowed_paths if path]
        result["analysis_token"] = signing.dumps(
            {
                "user_id": request.user.id,
                "source_image_path": str(result.get("source_image_path") or "").strip(),
                "allowed_image_paths": allowed_paths,
            },
            salt="digital-wardrobe-ai-analysis",
            compress=True,
        )
        return Response(result)


class AISaveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        source_image_path = str(request.data.get("source_image_path") or "").strip()
        analysis_token = str(request.data.get("analysis_token") or "").strip()
        pieces = request.data.get("pieces") or []
        outfit = request.data.get("outfit") or {}
        save_mode = str(request.data.get("save_mode") or "separate").strip()
        source_type = str(request.data.get("source_type") or "ai_add").strip()
        if not isinstance(pieces, list):
            return Response({"detail": "Invalid detected pieces."}, status=400)

        allowed_image_paths = None
        if analysis_token:
            try:
                token_data = signing.loads(
                    analysis_token,
                    salt="digital-wardrobe-ai-analysis",
                    max_age=6 * 60 * 60,
                )
            except SignatureExpired:
                return Response(
                    {"detail": "This AI analysis has expired. Please analyse the photo again."},
                    status=400,
                )
            except BadSignature:
                return Response(
                    {"detail": "Invalid AI analysis token. Please analyse the photo again."},
                    status=400,
                )

            if int(token_data.get("user_id") or 0) != request.user.id:
                return Response({"detail": "This AI analysis belongs to another session."}, status=403)

            source_image_path = str(token_data.get("source_image_path") or "").strip()
            allowed_image_paths = {
                str(path).strip()
                for path in (token_data.get("allowed_image_paths") or [])
                if str(path).strip()
            }
            if source_image_path:
                allowed_image_paths.add(source_image_path)

        try:
            group, created = save_multigarment_selection(
                user=request.user,
                source_image_path=source_image_path,
                pieces_payload=pieces,
                outfit_payload=outfit if isinstance(outfit, dict) else {},
                save_mode=save_mode,
                source_type=source_type if source_type in {"ai_add", "gallery", "wardrobe_scan"} else "ai_add",
                allowed_image_paths=allowed_image_paths,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({
            "message": f"Saved {len(created)} wardrobe item{'s' if len(created) != 1 else ''}.",
            "outfit_group_id": group.id if group else None,
            "items": [_clothing_json(request, item) for item in created],
        }, status=201)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "wardrobe_count": ClothingItem.objects.filter(user=request.user).count(),
            "outfit_count": OutfitGroup.objects.filter(user=request.user).count(),
            "wishlist_count": WishlistItem.objects.filter(user=request.user, is_purchased=False).count(),
        })


class AIStylistAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        question=str(request.data.get("question") or "").strip()
        if not question: return Response({"detail":"Ask me something about your wardrobe."},status=400)
        items=ClothingItem.objects.filter(user=request.user)
        reply=_generate_stylist_reply(question,items)
        visuals=_visual_items_for_reply(question,reply,items)
        return Response({"reply":reply,"items":[_clothing_json(request,x) for x in visuals]})

