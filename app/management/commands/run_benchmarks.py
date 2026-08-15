# app/management/commands/run_benchmarks.py
import time
import json
import os
from django.db import connection, transaction
from django.core.management.base import BaseCommand
from app.models import Tenant, Project

class Command(BaseCommand):
    help = 'Runs performance benchmarks for RLS vs Schema Isolation'

    def handle(self, *args, **options):
        self.stdout.write("Starting benchmarks... Please wait, inserting test data.")
        
        # We will use the existing tenant_a for our tests
        try:
            tenant = Tenant.objects.get(tenant_id='tenant_a')
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("tenant_a not found. Please seed the database first."))
            return

        # 1. Setup Test Data: Ensure we have a decent amount of data for testing
        project_count = Project.all_objects.filter(tenant=tenant).count()
        if project_count < 1000:
            self.stdout.write(f"Generating bulk data for RLS testing (currently {project_count} rows)...")
            projects_to_create = [
                Project(tenant=tenant, name=f"Bulk RLS Project {i}") 
                for i in range(1000)
            ]
            Project.all_objects.bulk_create(projects_to_create)
            
        with connection.cursor() as cursor:
            # Generate Schema Data
            cursor.execute(f'SET search_path TO "{tenant.db_schema}";')
            cursor.execute('SELECT COUNT(*) FROM app_project;')
            schema_count = cursor.fetchone()[0]
            if schema_count < 1000:
                self.stdout.write(f"Generating bulk data for Schema testing...")
                cursor.execute(
                    f"INSERT INTO app_project (name, created_at) "
                    f"SELECT 'Bulk Schema Project ' || generate_series(1, 1000), NOW();"
                )
            cursor.execute('SET search_path TO public;')

        results = {}

        # --- RLS Benchmarking ---
        self.stdout.write("Running RLS Benchmarks...")
        
        # Query without index
        start_time = time.time()
        list(Project.all_objects.filter(tenant=tenant))
        rls_without_index_time = (time.time() - start_time) * 1000

        # Add index via raw SQL
        with connection.cursor() as cursor:
            cursor.execute("CREATE INDEX IF NOT EXISTS rls_tenant_idx ON app_project (tenant_id, created_at);")
            
        # Query with index
        start_time = time.time()
        list(Project.all_objects.filter(tenant=tenant))
        rls_with_index_time = (time.time() - start_time) * 1000

        # Get index size via SQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_relation_size('rls_tenant_idx');")
            rls_index_bytes = cursor.fetchone()[0]
            rls_index_kb = rls_index_bytes / 1024.0

        results["row_level"] = {
            "query_time_ms": {
                "without_index": round(rls_without_index_time, 2),
                "with_index": round(rls_with_index_time, 2)
            },
            "index_size_kb": round(rls_index_kb, 2)
        }

        # --- Schema Isolation Benchmarking ---
        self.stdout.write("Running Schema Isolation Benchmarks...")
        
        with connection.cursor() as cursor:
            cursor.execute(f'SET search_path TO "{tenant.db_schema}";')
            
            start_time = time.time()
            cursor.execute('SELECT * FROM app_project;')
            cursor.fetchall()
            schema_query_time = (time.time() - start_time) * 1000
            
            # Check primary key index size as baseline for schema
            cursor.execute("SELECT pg_relation_size('app_project_pkey');")
            schema_index_bytes = cursor.fetchone()[0]
            schema_index_kb = schema_index_bytes / 1024.0
            
            cursor.execute('SET search_path TO public;')

        results["schema_isolation"] = {
            "query_time_ms": round(schema_query_time, 2),
            "index_size_kb": round(schema_index_kb, 2)
        }

        # --- Overhead Measurement ---
        self.stdout.write("Measuring connection overhead...")
        iterations = 1000
        start_time = time.time()
        with connection.cursor() as cursor:
            for _ in range(iterations):
                cursor.execute(f'SET search_path TO "{tenant.db_schema}";')
                cursor.execute('SET search_path TO public;')
        
        # Divide by total operations (2 per iteration) to get per-command cost
        overhead_ms = ((time.time() - start_time) * 1000) / (iterations * 2)

        results["connection_overhead_ms"] = {
            "set_search_path": round(overhead_ms, 4)
        }

        # Write results to results/benchmarks.json
        os.makedirs('results', exist_ok=True)
        with open('results/benchmarks.json', 'w') as f:
            json.dump(results, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Benchmarks complete. Results saved to results/benchmarks.json'))