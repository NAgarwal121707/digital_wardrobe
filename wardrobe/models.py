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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "category"]),
            models.Index(fields=["user", "color"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"