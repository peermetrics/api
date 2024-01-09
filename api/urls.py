from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from app.views.warmup import WarmupView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('_ah/warmup/', WarmupView.as_view(), name='warmup'),
    path('v1/', include('app.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
