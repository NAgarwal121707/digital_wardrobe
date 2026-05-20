from django.contrib import admin
from django.utils.html import format_html

from .models import ClothingItem


@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "category",
        "color",
        "image_preview",
        "created_at",
    )
    list_filter = (
        "category",
        "color",
        "created_at",
    )
    search_fields = (
        "name",
        "color",
        "user__email",
    )
    readonly_fields = (
        "created_at",
        "image_preview",
    )
    autocomplete_fields = (
        "user",
    )
    ordering = (
        "-created_at",
    )

    fieldsets = (
        ("Owner", {
            "fields": ("user",),
        }),
        ("Clothing Details", {
            "fields": (
                "name",
                "category",
                "color",
                "image",
                "image_preview",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 12px;" />',
                obj.image.url,
            )

        return "No image"

    image_preview.short_description = "Preview"