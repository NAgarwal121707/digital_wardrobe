from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("wardrobe", "0005_rename_wardrobe_wi_user_id_7f6d_idx_wardrobe_wi_user_id_49cc2c_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OutfitGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, default="Original look", max_length=140)),
                ("source_type", models.CharField(choices=[("ai_add", "AI Add"), ("gallery", "Gallery Builder"), ("wardrobe_scan", "Wardrobe Scan"), ("manual", "Manual")], default="ai_add", max_length=30)),
                ("original_image", models.ImageField(blank=True, null=True, upload_to="outfit_sources/")),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outfit_groups", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="clothingitem",
            name="outfit_group",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pieces", to="wardrobe.outfitgroup"),
        ),
        migrations.AddField(
            model_name="clothingitem",
            name="source_item_index",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
