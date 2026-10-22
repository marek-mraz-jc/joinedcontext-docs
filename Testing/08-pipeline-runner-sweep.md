---
sidebar_position: 9
title: Pipeline Runner Security Sweep
description: Every input, processor and output of the pinned Bento runner, what a manifest may do with it, and the test that holds the rule.
---

# Pipeline Runner Security Sweep

One runner pod runs every project's streams, and its environment holds every project's pipeline credentials. This page lists each component the pinned runner (`ghcr.io/warpstreamlabs/bento` 1.22.0, by digest in `joinedcontext-deployment/components/pipeline-runner/images.yaml`) ships, the verdict jc-core gives a manifest that names it, and the test that fails when the rule breaks. Read off the runner's own `bento list --format json-full` and jc-core on 2026-10-19 (T-3833).

## 1. How a manifest reaches the runner

A `DataSource`'s `spec.input` and a pipeline step's processor reach the runner verbatim: `jc-manifest` renders `input: { <type>: <spec.input> }`, and the Portal's streams reconciler takes the same path. jc-core's `DataSourceSpec::validate` and `pipeline::validate_processor_reading` are therefore the one gate (PL-50, PL-52, PL-16). Outputs never reach the runner as written: the stream's output is the platform's write to the pipeline's `targetEndpoint`, with the pipeline's own token (PL-18).

The cluster holds the second line. The runner's NetworkPolicy lets it reach the gateway, the Portal's internal listener, its token sidecar, DNS and public port 443 with every private, link-local and loopback range excepted, so no step reaches the broker or the Kubernetes API (deployment `tests/test_networkpolicies.py`). The runner's ServiceAccount token is not mounted, and every route of the Portal's internal listener authenticates its caller.

## 2. Measured on the pinned image

Each probe ran the pinned image with a fake secret in its environment and a file beside it, on 2026-10-19:

| Component | What it did | Verdict |
| --- | --- | --- |
| `template` processor | `{{ env "X" }}` and `expandenv` returned the secret | refused |
| `awk` processor | `getline` read the file, `ENVIRON` the secret, `system()` ran a shell | refused |
| `javascript` processor | `require` loaded the file; `bento.v0_fetch` fetches a URL built at run time | refused |
| Bloblang `file_rel_json` | returned the file | refused |
| Bloblang `"""…"""` string before `env("…")` | hid the call from a quote-tracking scan; Bento printed the variable (T-5223) | refused: the scan reads strings and comments too |
| Bloblang `import "…"`, `from "…"` | loaded a mapping from the runner's disk (T-5223) | refused |
| `python` processor | no environment, `No such file`; `while True: pass` held a core and the runner's streams API (T-5223) | refused: no CPU or memory cap per stream |
| `sql_raw` with `duckdb` | the image is not built with DuckDB | n/a |
| `sql_raw` with `sqlite` | `readfile()` is not loaded | allowed |

## 3. Inputs

| Input | Verdict | Test |
| --- | --- | --- |
| `amqp_0_9` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `amqp_1` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `aws_kinesis` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `aws_s3` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `aws_sqs` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `azure_blob_storage` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `azure_cosmosdb` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `azure_queue_storage` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `azure_service_bus_queue` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `azure_table_storage` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `batched` | allowed; every child input meets the top-level rules | `pipeline_sweep_tests::an_input_nested_in_a_wrapper_is_checked_as_a_top_level_one` |
| `beanstalkd` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `broker` | allowed; every child input meets the top-level rules | `pipeline_sweep_tests::an_input_nested_in_a_wrapper_is_checked_as_a_top_level_one` |
| `cassandra` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `cockroachdb_changefeed` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `csv` | allowed under `/data/` only | `pipeline_sweep_tests::fsevent_watches_only_the_files_volume`, `data_source_serde_tests::file_reader_paths_must_start_with_data_and_have_no_dotdot` |
| `cypher` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `discord` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `dynamic` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `etcd` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `file` | allowed under `/data/` only | `pipeline_sweep_tests::fsevent_watches_only_the_files_volume`, `data_source_serde_tests::file_reader_paths_must_start_with_data_and_have_no_dotdot` |
| `file_tail` | allowed under `/data/` only | `pipeline_sweep_tests::fsevent_watches_only_the_files_volume`, `data_source_serde_tests::file_reader_paths_must_start_with_data_and_have_no_dotdot` |
| `fsevent` | allowed under `/data/` only | `pipeline_sweep_tests::fsevent_watches_only_the_files_volume`, `data_source_serde_tests::file_reader_paths_must_start_with_data_and_have_no_dotdot` |
| `gcp_bigquery_select` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `gcp_cloud_storage` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `gcp_pubsub` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `gcp_spanner_cdc` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `generate` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `grpc_client` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `hdfs` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `http_client` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `http_server` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `inproc` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `kafka` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `kafka_franz` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `kubernetes_watch` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `mongodb` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `mqtt` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `mqtt_v5` | refused: not in the jc-core list (catalog v1.21.1) | `data_source_serde_tests::unknown_type_nope_is_refused_and_names_accepted_types` |
| `nanomsg` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `nats` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `nats_jetstream` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `nats_kv` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `nats_object_store` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `nats_stream` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `nsq` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `parquet` | allowed under `/data/` only | `pipeline_sweep_tests::fsevent_watches_only_the_files_volume`, `data_source_serde_tests::file_reader_paths_must_start_with_data_and_have_no_dotdot` |
| `pulsar` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `read_until` | allowed; every child input meets the top-level rules | `pipeline_sweep_tests::an_input_nested_in_a_wrapper_is_checked_as_a_top_level_one` |
| `redis_list` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `redis_pubsub` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `redis_scan` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `redis_streams` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `resource` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `s2` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `sequence` | allowed; every child input meets the top-level rules | `pipeline_sweep_tests::an_input_nested_in_a_wrapper_is_checked_as_a_top_level_one` |
| `sftp` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `socket` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `socket_server` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `sql_raw` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `sql_select` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `stdin` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `subprocess` | refused: works on the runner (program, own input, cluster API, another stream, a listener) | `pipeline_sweep_tests::inputs_that_reach_the_runner_itself_are_refused` |
| `twitter_search` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `websocket` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |
| `zmq4n` | allowed; URL host checks, secret fields as `${VAR}`, Bloblang host rule, processors as steps; egress public 443 only | `pipeline_sweep_tests::an_inputs_bloblang_reads_neither_env_nor_files`, `an_inputs_processors_are_held_to_the_step_rules` |

## 4. Processors

| Processor | Verdict | Test |
| --- | --- | --- |
| `archive` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `avro` | allowed; as `json_schema` | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `awk` | refused: reads the runner's files or environment (measured on the pin) | `pipeline_sweep_tests::processors_that_read_the_runner_are_refused_in_a_step` |
| `aws_bedrock_invoke` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `aws_dynamodb_partiql` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `aws_lambda` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `aws_s3` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `azure_cosmosdb` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `bloblang` | allowed; Bloblang host rule | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `bounds_check` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `branch` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `cache` | allowed; the runner's caches are shared across projects (parked: T-later-pipeline-runner-project-isolation) | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `cached` | allowed; shared caches as for `cache` | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `catch` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `command` | refused: not on the platform's list | `pipeline_escape_tests::a_processor_that_runs_a_program_or_opens_a_file_is_not_a_step` |
| `compress` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `couchbase` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `decompress` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `dedupe` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `elasticsearch` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `file` | refused: not on the platform's list | `pipeline_escape_tests::a_processor_that_runs_a_program_or_opens_a_file_is_not_a_step` |
| `for_each` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `gcp_bigquery_select` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `grok` | allowed; `pattern_paths` loads pattern files and echoes none | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `group_by` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `group_by_value` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `http` | allowed; `url` written out, host checks (no loopback, private, link-local, token Service, message host) | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `insert_part` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `javascript` | refused: reads the runner's files or environment (measured on the pin) | `pipeline_sweep_tests::processors_that_read_the_runner_are_refused_in_a_step` |
| `jmespath` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `jq` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `json_schema` | allowed; `schema_path` loads a schema and echoes none | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `log` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `mapping` | allowed; Bloblang host rule | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `metric` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `mongodb` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `msgpack` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `mutation` | allowed; Bloblang host rule | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `nats_kv` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `nats_object_store` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `nats_request_reply` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `nlp_classify_text` | allowed; `path` loads an ONNX model and echoes none | `pipeline_escape_tests` |
| `nlp_classify_tokens` | allowed; `path` loads an ONNX model and echoes none | `pipeline_escape_tests` |
| `nlp_extract_features` | allowed; `path` loads an ONNX model and echoes none | `pipeline_escape_tests` |
| `nlp_zero_shot_classify` | allowed; `path` loads an ONNX model and echoes none | `pipeline_escape_tests` |
| `noop` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `opensnowcat` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `parallel` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `parquet_decode` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `parquet_encode` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `parse_log` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `processors` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `protobuf` | allowed; `import_paths` is `/proto` in the seeds | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `python` | refused; WASM runtime with no environment and no files, but no CPU or memory cap in the shared runner (T-5223) | `pipeline_escape_tests` |
| `rate_limit` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `redis` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `redis_script` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `resource` | allowed; names the runner's shared resources only | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `retry` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `schema_registry_decode` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `schema_registry_encode` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `select_parts` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `sentry_capture` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `sleep` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `split` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `sql` | refused: not on the platform's list | `pipeline_escape_tests::a_processor_that_runs_a_program_or_opens_a_file_is_not_a_step` |
| `sql_insert` | allowed; DuckDB is not in the pinned image, SQLite has no `readfile`; a `/data/` file DB is shared (parked) | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `sql_raw` | as `sql_insert` | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `sql_select` | as `sql_insert` | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `subprocess` | refused: not on the platform's list | `pipeline_escape_tests::a_processor_that_runs_a_program_or_opens_a_file_is_not_a_step` |
| `switch` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `sync_response` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `template` | refused: reads the runner's files or environment (measured on the pin) | `pipeline_sweep_tests::processors_that_read_the_runner_are_refused_in_a_step` |
| `try` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `unarchive` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `wasm` | refused: not on the platform's list | `pipeline_escape_tests::a_processor_that_runs_a_program_or_opens_a_file_is_not_a_step` |
| `while` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `workflow` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |
| `xml` | allowed; every string through the Bloblang host rule, `${VAR}` and URL host checks | `pipeline_escape_tests`, `pipeline_sweep_tests` |

## 5. Outputs

The platform writes every stream's output, so none of the runner's outputs is a manifest's choice: an output in an author's `bento.yaml` is replaced by the Endpoint write (Portal `reconciler/streams.rs`, `a_bento_cannot_serve_or_answer_http_requests`). The runner ships `amqp_0_9`, `amqp_1`, `aws_dynamodb`, `aws_kinesis`, `aws_kinesis_firehose`, `aws_s3`, `aws_s3_stream`, `aws_sns`, `aws_sqs`, `azure_blob_storage`, `azure_cosmosdb`, `azure_queue_storage`, `azure_table_storage`, `beanstalkd`, `broker`, `cache`, `cassandra`, `couchbase`, `cypher`, `datadog_logs`, `discord`, `drop`, `drop_on`, `dynamic`, `elasticsearch`, `elasticsearch_v2`, `fallback`, `file`, `gcp_bigquery`, `gcp_bigquery_write_api`, `gcp_bigtable`, `gcp_cloud_storage`, `gcp_pubsub`, `grpc_client`, `hdfs`, `http_client`, `http_server`, `inproc`, `kafka`, `kafka_franz`, `mongodb`, `mqtt`, `mqtt_v5`, `nanomsg`, `nats`, `nats_jetstream`, `nats_kv`, `nats_object_store`, `nats_stream`, `nsq`, `opensearch`, `pulsar`, `pusher`, `questdb`, `redis_hash`, `redis_list`, `redis_pubsub`, `redis_streams`, `reject`, `reject_errored`, `resource`, `retry`, `s2`, `sftp`, `slack_webhook`, `snowflake_put`, `socket`, `splunk_hec`, `sql`, `sql_insert`, `sql_raw`, `stdout`, `subprocess`, `switch`, `sync_response`, `websocket`, `zmq4n`
.

## 6. Still open

- The runner's memory caches (`fleet`, `departures`, `gtfs`) and its `/data` volume are shared by every project's streams: one project's step can read or overwrite another's cached values, and one project's file source can read another's file. Parked in `tasks/later/T-later-pipeline-runner-project-isolation.md`.
- jc-core's catalogues are generated from runner v1.21.1 while the pin is 1.22.0; a component new in 1.22.0 is unknown and refused until the catalogue is regenerated.

## Related

- [Pipelines](../Architecture/08-pipelines.md)
- [Pipeline requirements](../Requirements/pipelines.md)
- [Security Testing & Penetration Verification](06-security-tests.md)
