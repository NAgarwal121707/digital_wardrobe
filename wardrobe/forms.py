from django import forms

from .models import ClothingItem


class ClothingItemForm(forms.ModelForm):
    class Meta:
        model = ClothingItem
        fields = ["name", "category", "color", "image"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Blue Denim Jacket",
                }
            ),
            "category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Casual Wear, Office Wear, Party Wear",
                }
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Black, White, Red",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if len(name) < 2:
            raise forms.ValidationError("Item name must be at least 2 characters long.")

        return name

    def clean_category(self):
        category = self.cleaned_data.get("category", "").strip()

        if len(category) < 2:
            raise forms.ValidationError("Category must be at least 2 characters long.")

        return category

    def clean_color(self):
        color = self.cleaned_data.get("color", "").strip()

        if len(color) < 2:
            raise forms.ValidationError("Color must be at least 2 characters long.")

        return color

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if not image:
            return image

        if not hasattr(image, "content_type"):
            return image

        allowed_content_types = ["image/jpeg", "image/png", "image/webp"]

        if image.content_type not in allowed_content_types:
            raise forms.ValidationError("Only JPG, PNG, or WEBP images are allowed.")

        max_size = 5 * 1024 * 1024

        if image.size > max_size:
            raise forms.ValidationError("Image size must be less than 5 MB.")

        return image