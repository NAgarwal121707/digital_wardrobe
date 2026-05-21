from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from wardrobe.forms import ClothingItemForm
from wardrobe.models import ClothingItem

from .forms import LoginForm, RegisterForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("email", "An account with this email already exists.")
        else:
            login(request, user)
            return redirect("dashboard")
    return render(request, "register.html", {"form": form})


@login_required(login_url="login")
def dashboard_view(request):
    clothing_items = ClothingItem.objects.filter(user=request.user)
    categories = (
        clothing_items.values("category")
        .annotate(item_count=Count("id"))
        .order_by("category")
    )
    return render(
        request,
        "dashboard.html",
        {
            "clothing_items": clothing_items,
            "categories": categories,
            "total_items": clothing_items.count(),
            "total_categories": categories.count(),
            "total_outfits": 0,
        },
    )


@login_required(login_url="login")
def clothing_item_detail_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)
    return render(request, "clothing_item_detail.html", {"clothing_item": clothing_item})


@login_required(login_url="login")
def add_clothing_item_view(request):
    if request.method == "POST":
        form = ClothingItemForm(request.POST, request.FILES)
        if form.is_valid():
            clothing_item = form.save(commit=False)
            clothing_item.user = request.user
            clothing_item.save()
            messages.success(request, "Clothing item added successfully.")
            return redirect("dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ClothingItemForm()
    return render(request, "add_clothing_item.html", {"form": form})


@login_required(login_url="login")
def edit_clothing_item_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)
    if request.method == "POST":
        form = ClothingItemForm(request.POST, request.FILES, instance=clothing_item)
        if form.is_valid():
            form.save()
            messages.success(request, "Clothing item updated successfully.")
            return redirect("clothing_item_detail", item_id=clothing_item.id)
        messages.error(request, "Please correct the errors below.")
    else:
        form = ClothingItemForm(instance=clothing_item)
    return render(request, "edit_clothing_item.html", {"form": form, "clothing_item": clothing_item})


@login_required(login_url="login")
def delete_clothing_item_view(request, item_id):
    clothing_item = get_object_or_404(ClothingItem, id=item_id, user=request.user)
    if request.method == "POST":
        clothing_item.delete()
        messages.success(request, "Clothing item deleted successfully.")
        return redirect("dashboard")
    return render(request, "delete_clothing_item.html", {"clothing_item": clothing_item})


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    return redirect("login")
