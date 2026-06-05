from django.conf import settings
from django.db import models


class ClothingItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clothing_items",
    )

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80)
    color = models.CharField(max_length=50)

    image = models.ImageField(
        upload_to="clothing_items/",
        blank=True,
        null=True,
    )

    tags = models.TextField(blank=True, default="")
    garment_type = models.CharField(max_length=120, blank=True, default="")
    aesthetic = models.CharField(max_length=120, blank=True, default="")
    fit_silhouette = models.CharField(max_length=160, blank=True, default="")
    occasion = models.CharField(max_length=120, blank=True, default="")
    season = models.CharField(max_length=120, blank=True, default="")
    accessories = models.TextField(blank=True, default="")
    styling_notes = models.TextField(blank=True, default="")
    is_complete_outfit = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.category})"


class WishlistItem(models.Model):
    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("ai_suggestion", "AI Suggestion"),
        ("trend", "Trend"),
        ("future_purchase", "Future Purchase"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )

    title = models.CharField(max_length=140)
    category = models.CharField(max_length=80, blank=True, default="")
    color = models.CharField(max_length=60, blank=True, default="")
    image = models.ImageField(
        upload_to="wishlist_items/",
        blank=True,
        null=True,
    )

    reason = models.TextField(blank=True, default="")
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="future_purchase")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    purchase_link = models.URLField(blank=True, default="")
    expected_budget = models.CharField(max_length=60, blank=True, default="")
    is_purchased = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_purchased", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_purchased"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return self.title
