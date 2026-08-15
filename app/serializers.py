# app/serializers.py
from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    tenant_id = serializers.CharField(source='tenant.tenant_id', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'tenant_id', 'created_at']