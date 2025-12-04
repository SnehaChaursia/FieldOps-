from django.contrib import admin
from .models import Asset, Reservation, Maintenance, AuditLog

admin.site.register(Asset)
admin.site.register(Reservation)
admin.site.register(Maintenance)
admin.site.register(AuditLog)
