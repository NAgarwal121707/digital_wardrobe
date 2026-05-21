from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("add-item/", views.add_item_choice_view, name="add_clothing_item"),
    path("add-item/manual/", views.add_clothing_item_view, name="add_clothing_item_manual"),
    path("add-item/ai/", views.ai_add_clothing_item_view, name="ai_add_clothing_item"),
    path("stylist/", views.stylist_view, name="stylist"),
    path("item/<int:item_id>/", views.clothing_item_detail_view, name="clothing_item_detail"),
    path("item/<int:item_id>/edit/", views.edit_clothing_item_view, name="edit_clothing_item"),
    path("item/<int:item_id>/delete/", views.delete_clothing_item_view, name="delete_clothing_item"),
    path("logout/", views.logout_view, name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset.html",
            email_template_name="password_reset_email.html",
            subject_template_name="password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
            success_url="/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
