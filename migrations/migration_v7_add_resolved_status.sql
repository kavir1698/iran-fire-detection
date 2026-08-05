-- Migration v7: Allow 'RESOLVED' status so old fires can be auto-resolved & cleaned up
-- Date: 2026-08-05
--
-- Problem:
--   resolve_old_fires() (src/db_client.py) marks fires as 'RESOLVED' after 24h without
--   re-detection, and cleanup_resolved_fires() deletes them after 30 days. But the
--   chk_status CHECK constraint only allowed ('PENDING', 'CONFIRMED', 'FALSE_POSITIVE'),
--   so every resolve UPDATE violated the constraint, rolled back, and old fires were
--   never removed from the map.
--
-- Fix:
--   Recreate chk_status to include 'RESOLVED'.

BEGIN;

ALTER TABLE fires DROP CONSTRAINT IF EXISTS chk_status;
ALTER TABLE fires ADD CONSTRAINT chk_status CHECK (status IN ('PENDING', 'CONFIRMED', 'FALSE_POSITIVE', 'RESOLVED'));

COMMIT;
