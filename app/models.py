# app/models.py
from django.db import models
from .managers import TenantManager

class Tenant(models.Model):
    name = models.CharField(max_length=255)
    tenant_id = models.CharField(max_length=100, unique=True)
    db_schema = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'tenants'  # Maps to our seeded PostgreSQL table

    def __str__(self):
        return self.name


class Project(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()     # Custom tenant-scoped manager (For RLS)
    all_objects = models.Manager() # Default unscoped manager (For Schema Strategy)

    def __str__(self):
        # Safely handle projects that have no tenant associated
        if self.tenant:
            return f"{self.name} ({self.tenant.tenant_id})"
        return f"{self.name} (Schema Isolated)"