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
