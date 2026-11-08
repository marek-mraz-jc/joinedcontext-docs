BEGIN; SET LOCAL ROLE app;
SELECT set_config('jc.org', md5('o3')::text::uuid::text, true), set_config('jc.catalogue', md5('c3-1')::text::uuid::text, true) \gset
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, SUMMARY ON)
WITH q AS (SELECT to_tsquery('jc_simple', 'ovzdus:* & mesto') AS q),
hit AS (SELECT d.* FROM cat_dataset d, q WHERE d.search @@ q.q AND d.state = 'active' AND (NOT d.private OR d.owner_group = ANY('{}'::uuid[])))
SELECT (SELECT count(*) FROM hit) AS total,
       (SELECT jsonb_object_agg(f, n) FROM (SELECT unnest(formats) f, count(*) n FROM hit GROUP BY 1) x) AS format_facet,
       (SELECT jsonb_agg(name) FROM (SELECT name FROM hit, q ORDER BY ts_rank_cd(search, q.q) DESC, modified DESC LIMIT 20) p) AS page;
SELECT count(*) AS visible_rows FROM cat_dataset;
COMMIT;
