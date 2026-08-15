# app/views.py
from rest_framework import viewsets
from .models import Project
from .serializers import ProjectSerializer
from .middleware import get_current_tenant

class RLSProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        # Evaluates dynamically at request time using the scoped manager
        return Project.objects.all()

    def perform_create(self, serializer):
        tenant = get_current_tenant()
        serializer.save(tenant=tenant)

class SchemaProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        # Use 'all_objects' to bypass the RLS TenantManager logic.
        # The database search_path handles the isolation automatically!
        return Project.all_objects.all()