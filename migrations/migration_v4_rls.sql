-- Migration v4: Enable Row-Level Security on public tables
-- Date: 2026-07-29
--
-- Supabase auto-exposes every table in the `public` schema via its REST API.
-- Without RLS, anyone with the project anon key can read/write/delete all rows.
--
-- This project uses direct PostgreSQL connections (psycopg2 via DATABASE_URL),
-- which bypass RLS entirely. So we enable RLS and add NO anon/authenticated
-- policies — effectively blocking all access via the Supabase REST API.
--
-- The pipeline and dashboard remain unaffected because they connect directly
-- via the PostgreSQL connection string with the postgres role.

BEGIN;

-- Enable RLS on both tables
ALTER TABLE fires ENABLE ROW LEVEL SECURITY;
ALTER TABLE citizen_reports ENABLE ROW LEVEL SECURITY;

-- Deny all public access: no SELECT/INSERT/UPDATE/DELETE policies for
-- the anon or authenticated roles. The direct PostgreSQL connection
-- used by the pipeline bypasses RLS and continues to work.

-- If you later need to expose these tables via the Supabase REST API
-- (e.g., for a public dashboard), add granular policies here, such as:
--
--   CREATE POLICY "anon_read_fires" ON fires
--       FOR SELECT TO anon
--       USING (true);
--
-- But only after confirming the data is safe for public consumption.

COMMIT;
