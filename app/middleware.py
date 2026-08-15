import threading
from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection

_thread_locals = threading.local()

def get_current_tenant():
    """Retrieve current tenant from thread-local storage."""
    return getattr(_thread_locals, 'tenant', None)

def set_current_tenant(tenant):
    """Set current tenant in thread-local storage."""
    _thread_locals.tenant = tenant

def clear_current_tenant():
    """Clear tenant from thread-local storage."""
    if hasattr(_thread_locals, 'tenant'):
        del _thread_locals.tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .models import Tenant

        clear_current_tenant()
        tenant_id = request.headers.get('X-Tenant-ID')

        if request.path.startswith('/api/'):
            if not tenant_id:
                if hasattr(connection, 'set_schema_to_public'):
                    connection.set_schema_to_public()
                return JsonResponse({'detail': 'X-Tenant-ID header is required.'}, status=404)

            cache_key = f"tenant_pk:{tenant_id}"
            tenant_pk = cache.get(cache_key)

            if not tenant_pk:
                try:
                    tenant = Tenant.objects.get(tenant_id=tenant_id)
                    cache.set(cache_key, tenant.pk, timeout=3600)
                except Tenant.DoesNotExist:
                    if hasattr(connection, 'set_schema_to_public'):
                        connection.set_schema_to_public()
                    return JsonResponse({'detail': 'Tenant not found.'}, status=404)
            else:
                try:
                    tenant = Tenant.objects.get(pk=tenant_pk)
                except Tenant.DoesNotExist:
                    tenant = Tenant.objects.get(tenant_id=tenant_id)
                    cache.set(cache_key, tenant.pk, timeout=3600)

            request.tenant = tenant
            set_current_tenant(tenant)

            # --- THE ARCHITECTURE FIX ---
            if request.path.startswith('/api/schema/'):
                # For Schema Isolation: Set path to tenant's schema, but keep public for FK lookups
                if hasattr(connection, 'set_schema'):
                    pass 
                else:
                    with connection.cursor() as cursor:
                        cursor.execute(f'SET search_path TO "{tenant.db_schema}", public;')
            else:
                # For RLS routes (/api/rls/): Keep search_path restricted to public!
                if hasattr(connection, 'set_schema_to_public'):
                    connection.set_schema_to_public()
                else:
                    with connection.cursor() as cursor:
                        cursor.execute('SET search_path TO public;')

        else:
            if hasattr(connection, 'set_schema_to_public'):
                connection.set_schema_to_public()
            else:
                with connection.cursor() as cursor:
                    cursor.execute('SET search_path TO public;')

        try:
            response = self.get_response(request)
        finally:
            if hasattr(connection, 'set_schema_to_public'):
                connection.set_schema_to_public()
            else:
                with connection.cursor() as cursor:
                    cursor.execute('SET search_path TO public;')
            clear_current_tenant()

        return response