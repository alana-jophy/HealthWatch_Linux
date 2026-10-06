# HealthWatch Database Architecture & Backup Management

HealthWatch utilizes **PostgreSQL 16 with PostGIS 3.4** to store disease surveillance records, administrative boundaries (Districts, Local Bodies, Wards), discrete patient movement trajectories, and contact tracing clusters.

---

## Directory Structure

```
database/
├── backups/
│   ├── healthwatch_production_dump.sql     # Full uncompressed PostGIS SQL dump (32MB)
│   └── healthwatch_production_dump.sql.gz  # Gzip-compressed dump for deployment (4.0MB)
├── init/
│   └── 01_init_postgis.sql                 # Automated extension bootstrap script
├── restore_db.sh                           # Production restore automation script
└── README.md
```

---

## Restoring to Production

### Method 1: Using the Automated Script (Recommended)

The utility script `restore_db.sh` automatically reads credentials from `.env.production`, checks container health, applies PostGIS extensions, restores tables, and prints verified row counts:

```bash
# Interactive restore from default compressed backup:
./database/restore_db.sh

# Or restore specific dump file non-interactively:
./database/restore_db.sh -f database/backups/healthwatch_production_dump.sql.gz -y
```

### Method 2: Native Docker Exec & `psql` (Single Command)

If deploying manually on a remote server:

```bash
# Using compressed dump (.sql.gz):
gunzip -c database/backups/healthwatch_production_dump.sql.gz | docker exec -i healthwatch-db psql -U healthwatch_admin -d healthwatch_db

# Or using plain .sql dump:
docker exec -i healthwatch-db psql -U healthwatch_admin -d healthwatch_db < database/backups/healthwatch_production_dump.sql
```

### Method 3: Transferring Dump to Remote Server via SCP

```bash
# 1. Copy compressed dump to production server
scp database/backups/healthwatch_production_dump.sql.gz user@your-server-ip:/path/to/healthwatch/database/backups/

# 2. SSH into production server and execute restore
ssh user@your-server-ip "cd /path/to/healthwatch && ./database/restore_db.sh -y"
```

---

## Creating a New Database Dump

To generate a new database dump at any time:

```bash
# Uncompressed SQL dump (portable, no owner restrictions):
docker exec healthwatch-db pg_dump -U healthwatch_user -d healthwatch_db --no-owner --no-acl > database/backups/healthwatch_production_dump.sql

# Compress for distribution:
gzip -k -9 -f database/backups/healthwatch_production_dump.sql
```
