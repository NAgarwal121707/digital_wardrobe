from django import forms

from .models import ClothingItem, WishlistItem


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



class WishlistItemForm(forms.ModelForm):
    class Meta:
        model = WishlistItem
        fields = [
            "title",
            "category",
            "color",
            "image",
            "reason",
            "source",
            "priority",
            "purchase_link",
            "expected_budget",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: White crop top / Silver hoops / Denim jacket",
                    "autocomplete": "off",
                }
            ),
            "category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Top, Shoes, Bag, Accessories, Outfit idea...",
                    "autocomplete": "off",
                }
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "White, black, beige, silver...",
                    "autocomplete": "off",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "class": "form-control file-input",
                    "accept": "image/*",
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Why do you want this? Example: AI suggested it with my blue jeans.",
                }
            ),
            "source": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "purchase_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional shopping link",
                }
            ),
            "expected_budget": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional budget, e.g. ₹1500",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ["category", "color", "image", "reason", "purchase_link", "expected_budget"]:
            self.fields[field].required = False

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 2:
            raise forms.ValidationError("Wishlist item name must be at least 2 characters long.")
        return title

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        allowed_content_types = ["image/jpeg", "image/png", "image/webp"]
        if hasattr(image, "content_type") and image.content_type not in allowed_content_types:
            raise forms.ValidationError("Only JPG, PNG, or WEBP images are allowed.")
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image size must be less than 5 MB.")
        return image
