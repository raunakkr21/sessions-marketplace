"""
Root URL configuration.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/', include('apps.sessions.urls')),
    path('api/', include('apps.bookings.urls')),
]
