-- Migration v5: Fix security advisories for function search_path and SECURITY DEFINER exposure
-- Date: 2026-07-29
--
-- Fixes:
--   1. update_fires_geom: mutable search_path → lock it down
--   2. st_estimatedextent: SECURITY DEFINER callable by anon/authenticated → revoke

BEGIN;

-- 1. Fix mutable search_path on the trigger function
--    This prevents search-path injection attacks by locking the function's
--    search_path to only pg_catalog and pg_temp.
CREATE OR REPLACE FUNCTION update_fires_geom()
RETURNS TRIGGER
SET search_path = pg_catalog, pg_temp
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

-- 2. Revoke EXECUTE on PostGIS SECURITY DEFINER functions exposed via REST API
--    This project uses direct psycopg2 connections, never the Supabase REST API,
--    so these functions should not be callable by anon or authenticated roles.
REVOKE EXECUTE ON FUNCTION public.st_estimatedextent(text, text) FROM PUBLIC, anon, authenticated;

--    Revoke from other commonly flagged PostGIS SECURITY DEFINER functions too,
--    in case the scanner picks them up in a future scan.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS sig
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
          AND p.prosecdef = true
          AND p.proname LIKE 'st_%'
    LOOP
        EXECUTE 'REVOKE EXECUTE ON FUNCTION public.' || r.sig || ' FROM PUBLIC, anon, authenticated';
    END LOOP;
END;
$$;

COMMIT;
