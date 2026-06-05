# Generated manually for Digital Wardrobe wishlist feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("wardrobe", "0003_remove_clothingitem_wardrobe_cl_user_id_acb10a_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WishlistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("category", models.CharField(blank=True, default="", max_length=80)),
                ("color", models.CharField(blank=True, default="", max_length=60)),
                ("image", models.ImageField(blank=True, null=True, upload_to="wishlist_items/")),
                ("reason", models.TextField(blank=True, default="")),
                ("source", models.CharField(choices=[("manual", "Manual"), ("ai_suggestion", "AI Suggestion"), ("trend", "Trend"), ("future_purchase", "Future Purchase")], default="future_purchase", max_length=30)),
                ("priority", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=20)),
                ("purchase_link", models.URLField(blank=True, default="")),
                ("expected_budget", models.CharField(blank=True, default="", max_length=60)),
                ("is_purchased", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wishlist_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["is_purchased", "-created_at"],
                "indexes": [
                    models.Index(fields=["user", "is_purchased"], name="wardrobe_wi_user_id_7f6d_idx"),
                    models.Index(fields=["user", "category"], name="wardrobe_wi_user_id_9ad4_idx"),
                ],
            },
        ),
    ]
