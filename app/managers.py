# app/managers.py
from django.db import models

class TenantManager(models.Manager):
    def get_queryset(self):
        from .middleware import get_current_tenant  # Lazy import
        queryset = super().get_queryset()
        tenant = get_current_tenant()
        if tenant:
            return queryset.filter(tenant=tenant)
        return queryset.none()