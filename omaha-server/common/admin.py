
from django.contrib import admin
from .models import RequestLog

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'method', 'path', 'status_code', 'user', 'ip_address')
    list_filter = ('method', 'status_code', 'user', 'timestamp')
    search_fields = ('path', 'query_params', 'body', 'headers', 'ip_address')
    readonly_fields = ('timestamp', 'method', 'path', 'query_params', 'body', 'headers', 'status_code', 'user', 'ip_address')
    actions = ['delete_selected']  # Enable bulk delete action
    
    def has_delete_permission(self, request, obj=None):
        return True 
        
    def has_add_permission(self, request):
        return False  # Prevent manual addition of logs

    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing logs
