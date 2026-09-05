from django import forms
from io import BytesIO
from PIL import Image, UnidentifiedImageError

from .models import ClothingItem, WishlistItem


class ClothingItemForm(forms.ModelForm):
    class Meta:
        model = ClothingItem
        fields = [
            "name",
            "category",
            "color",
            "image",
            "tags",
            "garment_type",
            "aesthetic",
            "fit_silhouette",
            "occasion",
            "season",
            "accessories",
            "styling_notes",
            "is_complete_outfit",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Example: Burgundy fitted top", "autocomplete": "off"}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tops, Jeans, Dresses, Shoes...", "autocomplete": "off"}),
            "color": forms.TextInput(attrs={"class": "form-control", "placeholder": "Burgundy, Black, Beige...", "autocomplete": "off"}),
            "image": forms.FileInput(attrs={"class": "form-control file-input", "accept": "image/jpeg,image/png,image/webp"}),
            "tags": forms.TextInput(attrs={"class": "form-control", "placeholder": "casual, fitted, ribbed, evening"}),
            "garment_type": forms.TextInput(attrs={"class": "form-control", "placeholder": "Top, Straight jeans, Blazer..."}),
            "aesthetic": forms.TextInput(attrs={"class": "form-control", "placeholder": "Minimal, Smart casual, Classic..."}),
            "fit_silhouette": forms.TextInput(attrs={"class": "form-control", "placeholder": "Fitted, Relaxed, Straight..."}),
            "occasion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Casual, Office, Party..."}),
            "season": forms.TextInput(attrs={"class": "form-control", "placeholder": "Summer, Winter, All season..."}),
            "accessories": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hoops, black bag, sneakers..."}),
            "styling_notes": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Specific styling notes for this item"}),
            "is_complete_outfit": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in [
            "category",
            "color",
            "image",
            "tags",
            "garment_type",
            "aesthetic",
            "fit_silhouette",
            "occasion",
            "season",
            "accessories",
            "styling_notes",
            "is_complete_outfit",
        ]:
            self.fields[field].required = False

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
        if image.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Image size must be less than 8 MB.")
        try:
            raw = image.read()
            with Image.open(BytesIO(raw)) as parsed:
                fmt = (parsed.format or "").upper()
                parsed.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError("The selected file is not a valid image.")
        finally:
            try:
                image.seek(0)
            except Exception:
                pass
        if fmt not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Only JPG, PNG, or WEBP images are allowed.")
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
        if image.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Image size must be less than 8 MB.")
        try:
            raw = image.read()
            with Image.open(BytesIO(raw)) as parsed:
                fmt = (parsed.format or "").upper()
                parsed.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError("The selected file is not a valid image.")
        finally:
            try:
                image.seek(0)
            except Exception:
                pass
        if fmt not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Only JPG, PNG, or WEBP images are allowed.")
        return image
