# app/management/commands/provision_tenant.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.core import management
from app.models import Tenant

class Command(BaseCommand):
    help = 'Provisions a new tenant by creating a schema and running migrations.'

    def add_arguments(self, parser):
        parser.add_argument('tenant_id', type=str, help='The ID of the tenant to provision')

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        try:
            tenant = Tenant.objects.get(tenant_id=tenant_id)
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Tenant "{tenant_id}" not found in public schema.'))
            return

        schema_name = tenant.db_schema

        with connection.cursor() as cursor:
            # 1. Create the isolated schema
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";')
            self.stdout.write(self.style.SUCCESS(f'Schema "{schema_name}" created.'))
            
            # 2. THE FIX: Clone an empty migrations table into the new schema
            # This forces Django to run migrations from scratch here, instead of looking at the public schema.
            cursor.execute(f'CREATE TABLE IF NOT EXISTS "{schema_name}".django_migrations (LIKE public.django_migrations INCLUDING ALL);')

            # 3. Set search path to the new schema FIRST, but keep public SECOND 
            # so PostgreSQL can find the tenants table for the foreign key constraint.
            cursor.execute(f'SET search_path TO "{schema_name}", public;')

        # 4. Apply standard Django migrations to build schema tables[cite: 4]
        management.call_command('migrate', interactive=False)
        self.stdout.write(self.style.SUCCESS(f'Migrations applied successfully to schema "{schema_name}".'))

        # 5. Reset search path back to public
        with connection.cursor() as cursor:
            cursor.execute('SET search_path TO public;')