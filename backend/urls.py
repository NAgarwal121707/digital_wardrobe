from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
]

# Quick Render fix: lets uploaded media images load from /media/ even when DEBUG=False.
# For a production app with permanent storage, use Cloudinary/S3 instead.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
