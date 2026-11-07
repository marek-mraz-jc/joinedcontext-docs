-- Research/rust/tenancy-foundation.md §5.3: one database, a schema and role per module,
-- forced RLS on (org_id, instance_id), and which operators reach an index under RLS.
-- Run: psql -v ON_ERROR_STOP=1 -f tenancy-foundation-rls.sql  (as a superuser, on a scratch database)
\pset footer off
SELECT p.oprname, l.typname AS left_t, r.typname AS right_t, f.proname, f.proleakproof
  FROM pg_operator p JOIN pg_proc f ON f.oid = p.oprcode
  JOIN pg_type l ON l.oid = p.oprleft JOIN pg_type r ON r.oid = p.oprright
 WHERE (p.oprname, l.typname, r.typname) IN (('=','uuid','uuid'),('=','text','text'),('<','text','text'),
       ('=','int8','int8'),('<','timestamptz','timestamptz'),('~~','text','text'),('~','text','text'),
       ('@>','jsonb','jsonb'),('?','jsonb','text'),('@>','anyarray','anyarray'),('@@','tsvector','tsquery'))
 ORDER BY f.proleakproof DESC, p.oprname;

CREATE ROLE jc_catalogue NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE ROLE jc_catalogue_app LOGIN NOSUPERUSER NOBYPASSRLS IN ROLE jc_catalogue;
CREATE SCHEMA catalogue AUTHORIZATION jc_catalogue;
SET ROLE jc_catalogue;
CREATE TABLE catalogue.datasets (
  org_id uuid NOT NULL, instance_id uuid NOT NULL, id uuid NOT NULL,
  name text NOT NULL, title text NOT NULL, doc jsonb NOT NULL, modified timestamptz NOT NULL,
  theme text GENERATED ALWAYS AS (doc->>'theme') STORED,
  PRIMARY KEY (org_id, instance_id, id));
CREATE UNIQUE INDEX ON catalogue.datasets (org_id, instance_id, name COLLATE "C");
CREATE INDEX ON catalogue.datasets (org_id, instance_id, modified);
CREATE INDEX ON catalogue.datasets (org_id, instance_id, theme);
CREATE INDEX ON catalogue.datasets USING gin (doc jsonb_path_ops);
ALTER TABLE catalogue.datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogue.datasets FORCE ROW LEVEL SECURITY;
CREATE POLICY by_org_instance ON catalogue.datasets
  USING (org_id = current_setting('jc.org', true)::uuid
     AND instance_id = current_setting('jc.instance', true)::uuid)
  WITH CHECK (org_id = current_setting('jc.org', true)::uuid
     AND instance_id = current_setting('jc.instance', true)::uuid);
RESET ROLE;
-- 100 organizations x 2 instances x 1000 datasets, org and instance ids derived from their number
INSERT INTO catalogue.datasets (org_id, instance_id, id, name, title, doc, modified)
SELECT md5('org' || o)::uuid, md5('inst' || o || '-' || i)::uuid, gen_random_uuid(),
       'ds-' || d, 'Dataset ' || d, jsonb_build_object('theme', 'theme-' || (d % 20), 'n', d),
       now() - make_interval(mins => d)
  FROM generate_series(1,100) o, generate_series(1,2) i, generate_series(1,1000) d;
ANALYZE catalogue.datasets;

SET ROLE jc_catalogue_app;
BEGIN;
SELECT set_config('jc.org', md5('org1')::uuid::text, true), set_config('jc.instance', md5('inst1-1')::uuid::text, true);
SELECT 'visible rows' AS check, count(*) FROM catalogue.datasets;
SELECT 'rows of org 2 by explicit filter' AS check, count(*) FROM catalogue.datasets WHERE org_id = md5('org2')::uuid;
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets WHERE name = 'ds-7';
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets WHERE name COLLATE "C" = 'ds-7';
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets WHERE name LIKE 'ds-7%';
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets ORDER BY modified DESC LIMIT 20;
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets WHERE doc @> '{"theme":"theme-3"}';
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets WHERE theme = 'theme-3';
EXPLAIN (COSTS OFF) SELECT * FROM catalogue.datasets WHERE org_id = current_setting('jc.org')::uuid
  AND instance_id = current_setting('jc.instance')::uuid AND doc @> '{"theme":"theme-3"}';
SAVEPOINT s;
\set ON_ERROR_STOP 0
INSERT INTO catalogue.datasets (org_id, instance_id, id, name, title, doc, modified) VALUES (md5('org2')::uuid, md5('inst2-1')::uuid, gen_random_uuid(), 'x', 'x', '{}', now());
\set ON_ERROR_STOP 1
ROLLBACK TO s;
COMMIT;
BEGIN;
SELECT 'no org set: visible rows' AS check, count(*) FROM catalogue.datasets;
COMMIT;
RESET ROLE;
