from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'name', 'google_id']
    readonly_fields = ['id', 'google_id', 'created_at', 'updated_at']
    fieldsets = [
        ('Identity', {'fields': ['id', 'google_id', 'email']}),
        ('Profile', {'fields': ['name', 'bio', 'avatar_url']}),
        ('Role & Status', {'fields': ['role', 'is_active', 'is_staff', 'is_superuser']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at']}),
    ]
