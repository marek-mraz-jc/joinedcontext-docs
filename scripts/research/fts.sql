CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE TEXT SEARCH CONFIGURATION jc_simple (COPY = simple);
ALTER TEXT SEARCH CONFIGURATION jc_simple ALTER MAPPING FOR hword, hword_part, word WITH unaccent, simple;
-- array_to_string is STABLE; a generated column needs an IMMUTABLE expression.
CREATE FUNCTION jc_words(text[]) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT array_to_string($1, ' ') $$;
CREATE TABLE cat_dataset (
  org_id uuid NOT NULL, catalogue_id uuid NOT NULL, id uuid NOT NULL,
  name text NOT NULL, state text NOT NULL DEFAULT 'active', private boolean NOT NULL DEFAULT false,
  owner_group uuid NOT NULL, title jsonb NOT NULL, notes jsonb NOT NULL, tags text[] NOT NULL,
  formats text[] NOT NULL, themes text[] NOT NULL, license_id text, modified timestamptz NOT NULL,
  search tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('jc_simple', coalesce(title->>'sk','') || ' ' || coalesce(title->>'en','')), 'A') ||
    setweight(to_tsvector('jc_simple', jc_words(tags)), 'B') ||
    setweight(to_tsvector('jc_simple', coalesce(notes->>'sk','') || ' ' || coalesce(notes->>'en','')), 'C')) STORED,
  PRIMARY KEY (org_id, catalogue_id, id), UNIQUE (org_id, catalogue_id, name));
CREATE INDEX cat_dataset_search ON cat_dataset USING gin (search);
CREATE INDEX cat_dataset_facets ON cat_dataset USING gin (tags, formats, themes);
ALTER TABLE cat_dataset ENABLE ROW LEVEL SECURITY; ALTER TABLE cat_dataset FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant ON cat_dataset USING (org_id = current_setting('jc.org')::uuid AND catalogue_id = current_setting('jc.catalogue')::uuid);
CREATE ROLE app NOLOGIN; GRANT SELECT ON cat_dataset TO app;
-- 20 organizations x 2 catalogues x 1250 datasets = 50 000 rows
INSERT INTO cat_dataset (org_id, catalogue_id, id, name, private, owner_group, title, notes, tags, formats, themes, license_id, modified)
SELECT md5('o'||o)::uuid, md5('c'||o||'-'||c)::uuid, gen_random_uuid(), 'ds-'||o||'-'||c||'-'||i, i % 10 = 0, md5('g'||(i%7))::uuid,
  jsonb_build_object('sk', (array['Doprava','Ovzdušie','Parkovanie','Školy','Rozpočet'])[1+i%5] || ' ' || i, 'en', (array['Transport','Air quality','Parking','Schools','Budget'])[1+i%5] || ' ' || i),
  jsonb_build_object('sk', 'Údaje mesta o téme ' || i, 'en', 'City data about topic ' || i),
  array[(array['doprava','ovzdusie','parking','skoly','rozpocet'])[1+i%5], 'mesto'],
  array[(array['CSV','JSON','GeoJSON','NGSI-LD'])[1+i%4]], array[(array['TRAN','ENVI','GOVE','EDUC'])[1+i%4]], 'cc-by', now() - (i||' hours')::interval
FROM generate_series(1,20) o, generate_series(1,2) c, generate_series(1,1250) i;
ANALYZE cat_dataset;
