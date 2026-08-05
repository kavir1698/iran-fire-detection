-- Migration v6: Fix update_fires_geom trigger broken by migration v5 search_path lock
-- Date: 2026-08-05
--
-- Problem:
--   Migration v5 locked the trigger function's search_path to pg_catalog, pg_temp.
--   On Supabase, the PostGIS `geography` type and ST_* functions live in the `public`
--   schema, so inside the function they could no longer be resolved. Result: every
--   INSERT/UPDATE on the `fires` table failed with `type "geography" does not exist`,
--   which silently suppressed all Telegram alerts (save_fire() returned None).
--
-- Fix:
--   Keep the locked search_path (preserves the v5 security hardening) but
--   schema-qualify the PostGIS references with the `public` prefix.

BEGIN;

CREATE OR REPLACE FUNCTION update_fires_geom()
RETURNS TRIGGER
SET search_path = pg_catalog, pg_temp
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.geom := public.ST_SetSRID(public.ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::public.geography;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

COMMIT;
