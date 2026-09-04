-- ==============================================================================
-- HealthWatch Database Initialization
-- Enables PostGIS Spatial Extensions and UUID Generator
-- ==============================================================================

\echo 'Enabling PostGIS and UUID extensions...'

-- Enable PostGIS spatial extension (includes geometry and geography types)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable PostGIS topology support
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable UUID extension for unique primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify spatial extension version
SELECT postgis_full_version();
