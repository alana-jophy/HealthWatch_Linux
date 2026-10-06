-- ==============================================================================
-- HealthWatch - Multi-Role DB Access Safeguard
-- Ensures both healthwatch_user and healthwatch_admin exist with full permissions
-- ==============================================================================

\echo 'Verifying and configuring HealthWatch database access roles...'

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'healthwatch_admin') THEN
    CREATE ROLE healthwatch_admin WITH LOGIN SUPERUSER PASSWORD 'HealthWatch_Prod_Secret_Pass_2026!';
  ELSE
    ALTER ROLE healthwatch_admin WITH LOGIN SUPERUSER PASSWORD 'HealthWatch_Prod_Secret_Pass_2026!';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'healthwatch_user') THEN
    CREATE ROLE healthwatch_user WITH LOGIN SUPERUSER PASSWORD 'healthwatch_secure_password_123';
  ELSE
    ALTER ROLE healthwatch_user WITH LOGIN SUPERUSER PASSWORD 'healthwatch_secure_password_123';
  END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE healthwatch_db TO healthwatch_admin;
GRANT ALL PRIVILEGES ON DATABASE healthwatch_db TO healthwatch_user;
