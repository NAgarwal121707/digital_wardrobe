from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import (
    ClothingDetailAPIView,
    ClothingListAPIView,
    DashboardAPIView,
    LoginAPIView,
    RegisterAPIView,
    WishlistListAPIView,
    WishlistDetailAPIView,
    AIAnalyzeAPIView,
    AISaveAPIView,
    AIStylistAPIView,
    ProfileAPIView,
)

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="api_register"),
    path("auth/login/", LoginAPIView.as_view(), name="api_login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("dashboard/", DashboardAPIView.as_view(), name="api_dashboard"),
    path("wardrobe/", ClothingListAPIView.as_view(), name="api_wardrobe"),
    path("wardrobe/<int:item_id>/", ClothingDetailAPIView.as_view(), name="api_wardrobe_detail"),
    path("wishlist/", WishlistListAPIView.as_view(), name="api_wishlist"),
    path("wishlist/<int:item_id>/", WishlistDetailAPIView.as_view(), name="api_wishlist_detail"),
    path("ai/analyze/", AIAnalyzeAPIView.as_view(), name="api_ai_analyze"),
    path("ai/save/", AISaveAPIView.as_view(), name="api_ai_save"),
    path("profile/", ProfileAPIView.as_view(), name="api_profile"),
    path("ai/stylist/", AIStylistAPIView.as_view(), name="api_ai_stylist"),
]
