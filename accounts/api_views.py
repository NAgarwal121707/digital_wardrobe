from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count
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


class ClothingDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, item_id):
        return ClothingItem.objects.filter(user=request.user, id=item_id).first()

    def get(self, request, item_id):
        item = self.get_object(request, item_id)
        if item is None:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
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
