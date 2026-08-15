# app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RLSProjectViewSet, SchemaProjectViewSet

router = DefaultRouter()
# Existing RLS Endpoint
router.register(r'rls/projects', RLSProjectViewSet, basename='rls-projects')

# NEW: Schema Isolation Endpoint
router.register(r'schema/projects', SchemaProjectViewSet, basename='schema-projects')

urlpatterns = [
    path('', include(router.urls)),
]