from django.contrib import admin
from django.db.models import Count, Q
from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'start_time', 'end_time', 'capacity', 'active_bookings', 'created_at']
    list_filter = ['creator']
    search_fields = ['title', 'creator__name', 'creator__email']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _active_bookings=Count('bookings', filter=Q(bookings__status='active'))
        )

    def active_bookings(self, obj):
        return obj._active_bookings
    active_bookings.short_description = 'Active Bookings'
    active_bookings.admin_order_field = '_active_bookings'
