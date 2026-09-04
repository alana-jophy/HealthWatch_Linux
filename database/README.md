# HealthWatch Database Architecture

HealthWatch uses **PostgreSQL with the PostGIS extension** to store disease surveillance records, geospatial coordinates (latitude/longitude), patient location trajectories, geofences, and hotspot clusters.

## Features
- **PostGIS Extension**: Provides spatial database capabilities, enabling GIS queries such as `ST_DWithin`, `ST_Contains`, `ST_Distance`, and spatial indexing (`GIST`).
- **UUID Support**: Uses `uuid-ossp` for secure, non-sequential entity identifiers.
- **Docker Integration**: Automatically initialized via Docker Compose entrypoint scripts in `./init/`.

## Directory Structure
```
database/
├── init/
│   └── 01_init_postgis.sql  # Auto-executed on PostgreSQL container creation
└── README.md
```

## Connection Parameters
Default local environment settings (configured in `.env`):
- **Host**: `localhost` (or `db` inside Docker)
- **Port**: `5432`
- **Database**: `healthwatch_db`
- **User**: `healthwatch_user`
