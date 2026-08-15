# Multi-Tenant SaaS Backend Architecture

This repository contains a highly advanced, containerized multi-tenant Django application that implements and contrasts two distinct data isolation strategies: **Row-Level Security (RLS)** and **Schema-per-Tenant Isolation**.

The backend is built with Django REST Framework, backed by PostgreSQL for data persistence and Redis for tenant context caching. The entire application is orchestrated using Docker and Docker Compose.

## Architecture Overview

* **Row-Level Security (RLS):** Tenants share the same database tables, separated logically by a `tenant_id` foreign key. Querysets are dynamically filtered using a custom Django Model Manager and middleware.
* **Schema Isolation:** Each tenant is allocated a dedicated PostgreSQL schema. The database `search_path` is dynamically switched at runtime by custom middleware, ensuring physical table separation within the same database instance.

##  Prerequisites

Before you begin, ensure you have the following installed on your host machine:

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* [Git](https://git-scm.com/downloads)

##  Setup & Installation Guide

### 1. Clone the Repository

Clone the project to your local machine and navigate into the project directory:

```bash
git clone https://github.com/Ravindra-Reddy27/Production-Ready-Multi-Tenant-Django-Application-with-PostgreSQL.git
cd Production-Ready-Multi-Tenant-Django-Application-with-PostgreSQL
```

### 2. Environment Configuration

Copy the example environment variables file to create your active `.env` file:

```bash
cp .env.example .env
```

> **Windows PowerShell:**
>
> ```powershell
> Copy-Item .env.example .env
> ```

Ensure your `.env` file contains the necessary database and application configurations, such as:

```env
POSTGRES_DB=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

### 3. Build and Start the Containers

Spin up the application, database, and Redis cache in detached mode:

```bash
docker-compose up --build -d
```

> **Note on Database Seeding:**
> On the first startup, the PostgreSQL container will automatically execute `seeds/initial_tenants.sql`. This seeds the public database with `tenant_a` and `tenant_b`.

### 4. Apply Base Migrations

Once the containers are healthy, apply the base Django migrations to the public schema:

```bash
docker-compose exec app python manage.py migrate
```

### 5. Provision Tenant Schemas

For **Schema Isolation**, provision isolated schemas for your tenants. This custom command creates the PostgreSQL schema, clones the migration history, and builds the isolated tables:

```bash
docker-compose exec app python manage.py provision_tenant tenant_a
docker-compose exec app python manage.py provision_tenant tenant_b
```

##  API Usage & Endpoints

All endpoints are protected by custom middleware that strictly requires the `X-Tenant-ID` HTTP header.

If the header is omitted or contains an invalid tenant ID, the API returns:

```http
404 Not Found
```

**Base URL:**

```text
http://localhost:8002
```

## Part A: Row-Level Security (RLS) Endpoints

These endpoints interact with shared tables and rely on the custom `TenantManager` to filter data dynamically.

### Create a Project

**POST**

```bash
Invoke-RestMethod -Uri "http://localhost:8002/api/rls/projects/" `
  -Method POST `
  -Headers @{ "X-Tenant-ID" = "tenant_a" } `
  -ContentType "application/json" `
  -Body '{"name": "RLS Project One"}'
```

### List Projects

**GET**

```bash
Invoke-RestMethod -Uri "http://localhost:8002/api/rls/projects/" `
  -Method GET `
  -Headers @{ "X-Tenant-ID" = "tenant_a" }
```

## Part B: Schema Isolation Endpoints

These endpoints interact with isolated PostgreSQL schemas. Middleware dynamically executes:

```sql
SET search_path TO "schema_tenant_x";
```

### Create a Project

**POST**

```bash
Invoke-RestMethod -Uri "http://localhost:8002/api/schema/projects/" `
  -Method POST `
  -Headers @{ "X-Tenant-ID" = "tenant_b" } `
  -ContentType "application/json" `
  -Body '{"name": "Tenant B Secret Project"}'

```

### List Projects

**GET**

```bash
Invoke-RestMethod -Uri "http://localhost:8002/api/schema/projects/" `
  -Method GET `
  -Headers @{ "X-Tenant-ID" = "tenant_b" }
```

##  Performance Benchmarks

The project includes an automated benchmarking suite to evaluate query times and index sizes between the RLS and Schema Isolation models.

### Run the Benchmarks

```bash
docker-compose exec app python manage.py run_benchmarks
```

### View the Results

The command generates or overwrites:

```text
results/benchmarks.json
```

View the results from the host machine or inspect them inside the container:

```bash
docker-compose exec app cat results/benchmarks.json
```

### Example Output

```json
{
  "row_level": {
    "query_time_ms": {
      "without_index": 123.45,
      "with_index": 12.34
    },
    "index_size_kb": 512.0
  },
  "schema_isolation": {
    "query_time_ms": 5.67,
    "index_size_kb": 50.0
  },
  "connection_overhead_ms": {
    "set_search_path": 0.12
  }
}
```

##  Teardown and Cleanup

To completely destroy the environment, stop the containers, and wipe all database volumes:

> **Warning:** This deletes all seeded data, schemas, and projects.

```bash
docker-compose down -v
```
