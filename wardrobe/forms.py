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
                    "placeholder": "Example: Blue denim jacket",
                    "autocomplete": "off",
                }
            ),
            "category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Choose chip or type custom category",
                    "autocomplete": "off",
                }
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Choose chip or type color",
                    "autocomplete": "off",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "class": "form-control file-input",
                    "accept": "image/*",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["color"].required = False
        self.fields["image"].required = False

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Item name must be at least 2 characters long.")
        return name

    def clean_category(self):
        category = self.cleaned_data.get("category", "").strip()
        return category or "Uncategorized"

    def clean_color(self):
        color = self.cleaned_data.get("color", "").strip()
        return color or "Not specified"

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
