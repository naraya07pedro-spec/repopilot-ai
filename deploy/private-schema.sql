-- One-time administrator bootstrap, only in the explicitly selected database.
-- Atomic; fails if either object already exists. Do not drop/recreate existing objects.
-- No password here. Enable login and set its generated password through a secure
-- administrator connection after reviewing this script. Never use the postgres
-- administrator connection as the application's DATABASE_URL.
BEGIN;
CREATE ROLE repopilot_service NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS NOINHERIT;
CREATE SCHEMA repopilot_private AUTHORIZATION repopilot_service;
REVOKE ALL ON SCHEMA repopilot_private FROM PUBLIC;
ALTER ROLE repopilot_service SET search_path = repopilot_private, pg_catalog;
ALTER ROLE repopilot_service SET statement_timeout = '15s';
ALTER ROLE repopilot_service SET lock_timeout = '5s';
COMMIT;
-- Startup migrations enable RLS and revoke PUBLIC/anon/authenticated access on
-- RepoPilot tables and this schema. The table owner is the trusted backend role.
-- Do not expose this schema through the Supabase Data API or Realtime.
