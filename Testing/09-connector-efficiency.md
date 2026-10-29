---
sidebar_position: 10
title: Connector Efficiency
description: What an MCP connector costs a client in tokens and turns, measured from the model-lane transcripts and the public-door probe, and the five changes that save the most.
---

# Connector Efficiency

This page measures what the joinedcontext platform's MCP doors cost the model on the other side: the tool definitions it carries every turn, the answers it reads, the calls it repeats or has refused, and why graded scenarios fail. The numbers come from the transcripts the Portal model lane saved (`joinedcontext-portal/tests/connector_scenarios/model.rs`) and from one anonymous probe of the public door on `dev`. `scripts/connector-efficiency.py` writes every table below from `scripts/connector-efficiency.json`; no number in them is typed by hand (T-6030).

## 1. Sources

| Source | What it holds | Where |
| --- | --- | --- |
| T-6037 run 1 and run 2 | 55 scenarios each with `claude-haiku-5.5` and `gemini-3.8-flash`, 8 turns, the model read the whole JSON-RPC envelope cut at 20,000 characters | board `evidence/T-6037/transcripts`, `evidence/T-6037/run2` |
| T-6040 final | 7 haiku scenarios after the description changes | `evidence/T-6040/final` |
| T-6042 8 and 16 turns | the 24 gemini scenarios that ran out of turns, the model reads the text content alone up to 60,000 characters | `evidence/T-6042/run8`, `evidence/T-6042/run16` |
| Tool definitions | the function list each scenario's door sends, measured on Portal `0023cec1` by `the_tool_definitions_a_model_reads_are_measured` | `connector-efficiency.json` `tools` |
| Public door | `initialize`, `tools/list`, `list_endpoints` and `search` of `https://api.dev.joinedcontext.com/api/mcp`, anonymous, 2026-10-29 | `connector-efficiency.json` `public` |

Rows still missing: Claude Code with full access (T-6025) and claude.ai (T-6024). Both wait for their live runs on `dev`; their rows join the tables when the transcripts exist. No new OpenRouter run was made for this page.

The JSON holds counts only: tool names, byte sizes, token counts, verdicts, the grader's reason and a refusal class per call. No answer text, call argument, token or person leaves the transcripts.

## 2. Reproduce

```sh
# Portal: the tool definitions each scenario's door sends (no model call)
JC_MODEL_EVAL_TOOLS=/tmp/tools.json cargo test --test connector_scenarios -- \
  --ignored --exact model::the_tool_definitions_a_model_reads_are_measured
# docs: transcripts and grader tables to counts, then counts to this page
python3 scripts/connector-efficiency.py extract --out scripts/connector-efficiency.json \
  --tools /tmp/tools.json --public-init init.json --public-tools tools-list.json \
  --public-answer 'list_endpoints|le.json' --public-answer 'search "bike counters"|se.json' \
  --run "T-6037 run 2|envelope|20000|8|evidence/T-6037/run2|evidence/T-6037/final-tables.md"
python3 scripts/connector-efficiency.py render --write Testing/09-connector-efficiency.md
python3 scripts/connector-efficiency.py render --check Testing/09-connector-efficiency.md
```

Each `--run` names the label, what the model read (`envelope` or `text`), the answer cap, the turn cap, the transcript folder and the grader's table of that run (a `JC_MODEL_EVAL_FROM` regrade prints the same table). Rerunning `extract` over the same folders gives the same JSON.

How the tables count:

- A call is cut when the model read fewer characters than the door answered.
- "Same answer again" is a call whose tool and answer equal an earlier call of the same scenario, timestamps aside.
- "Where the tokens go" divides each run's measured tokens. Transcripts before T-6030 hold no per-turn usage, so the table takes bytes per token from the scenarios that ended without a call (their tokens are the definitions, the system prompt and the request) and assumes one call per turn. It is a reading, not a count; the lane records `turns[]` from T-6030 on, and the next run replaces the estimate with each turn's `prompt_tokens`.

## 3. Measured

<!-- connector-efficiency:begin (scripts/connector-efficiency.py render --write) -->

### Runs

| run | model | scenarios | graded | passed | calls | tokens | tokens per scenario | USD | seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-6037 run 1 | claude-haiku-5.5 | 55 | 33 | 3 | 219 | 1,503,879 | 27,343 | 0.18 | 433 |
| T-6037 run 1 | gemini-3.8-flash | 55 | 35 | 1 | 498 | 2,076,463 | 37,753 | 1.35 | 1651 |
| T-6037 run 2 | claude-haiku-5.5 | 55 | 33 | 8 | 252 | 1,982,376 | 36,043 | 0.23 | 527 |
| T-6037 run 2 | gemini-3.8-flash | 55 | 33 | 3 | 517 | 2,224,162 | 40,439 | 1.43 | 1710 |
| T-6040 final | claude-haiku-5.5 | 7 | 7 | 2 | 30 | 248,654 | 35,522 | 0.03 | 75 |
| T-6042 8 turns | gemini-3.8-flash | 24 | 24 | 3 | 214 | 1,017,722 | 42,405 | 0.51 | 918 |
| T-6042 16 turns | gemini-3.8-flash | 24 | 24 | 5 | 286 | 1,867,456 | 77,810 | 0.90 | 1559 |

### Tool definitions per turn, Portal doors

| segment | door | scenarios | tools | bytes min | bytes max | largest three |
| --- | --- | --- | --- | --- | --- | --- |
| access | mcp | 6 | 6-7 | 6,199 | 6,943 | `jc_change_plan` 2,384, `jc_schema_get` 1,061, `jc_resource_list` 777 |
| apps | mcp | 4 | 7-8 | 7,184 | 7,928 | `jc_change_plan` 2,384, `jc_schema_get` 1,061, `jc_run_list` 1,005 |
| connector | mcp | 6 | 35-73 | 26,129 | 62,157 | `jc_data_query` 2,571, `jc_change_plan` 2,384, `jc_endpoint_propose` 2,384 |
| context | mcp | 8 | 6-7 | 6,155 | 7,125 | `jc_change_plan` 2,384, `jc_schema_get` 1,061, `jc_model_infer` 969 |
| data-read | connector | 8 | 5-5 | 6,465 | 6,465 | `jc_data_query` 2,571, `jc_kpi_compute` 1,307, `jc_schema_get` 1,061 |
| data-read | mcp | 1 | 0-0 | 2 | 2 |  |
| operate | mcp | 5 | 6-12 | 4,306 | 10,858 | `jc_change_plan` 2,384, `jc_workspace_open` 1,641, `jc_activity_list` 1,297 |
| pipeline | mcp | 12 | 11-13 | 11,925 | 13,632 | `jc_change_plan` 2,384, `jc_pipeline_try_mapping` 1,660, `jc_pipeline_test` 1,325 |
| publish | mcp | 5 | 8-9 | 7,880 | 8,624 | `jc_change_plan` 2,384, `jc_kpi_compute` 1,307, `jc_schema_get` 1,061 |

### Public door (`/api/mcp`): what a client loads before the first question

| tool | bytes | description | input schema |
| --- | --- | --- | --- |
| `query_temporal` | 4,203 | 400 | 3,441 |
| `query_entities` | 3,752 | 193 | 3,197 |
| `retrieve_temporal` | 2,730 | 371 | 1,992 |
| `list_endpoints` | 2,014 | 235 | 1,422 |
| `summarize` | 1,980 | 266 | 1,369 |
| `get_entity` | 1,913 | 91 | 1,476 |
| all 19 tools | 28,352 | 3,664 | 18,343 |
| server `instructions` (initialize) | 4,261 |  |  |

### Public door answers

| tool | bytes on the wire | content text | structuredContent |
| --- | --- | --- | --- |
| `list_endpoints` | 24,396 | 9,821 | 14,350 |
| `search "bike counters"` | 9,109 | 2,998 | 5,978 |

### Where the tokens go

| run | model | zero-call runs | bytes per token | tokens | tool definitions | answers | model text and prompt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-6037 run 1 | claude-haiku-5.5 | 7 | 2.83 | 1,503,879 | 58 % | 29 % | 13 % |
| T-6037 run 1 | gemini-3.8-flash | 2 | 6.37 | 2,076,463 | 32 % | 28 % | 40 % |
| T-6037 run 2 | claude-haiku-5.5 | 6 | 2.78 | 1,982,376 | 51 % | 35 % | 14 % |
| T-6037 run 2 | gemini-3.8-flash | 1 | 6.38 | 2,224,162 | 32 % | 28 % | 40 % |
| T-6042 16 turns | gemini-3.8-flash | 2 | 6.48 | 1,867,456 | 19 % | 45 % | 36 % |

### Largest answers by tool (all runs)

| tool | calls | largest bytes | mean bytes | cut | content text | structuredContent | _meta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `jc_schema_get` | 195 | 60,000 | 25,791 | 126 | 534,782 | 529,617 | 6,466 |
| `jc_resource_list` | 696 | 20,000 | 832 | 2 | 192,559 | 152,123 | 91,828 |
| `jc_change_plan` | 118 | 7,990 | 1,681 | 0 | 69,553 | 92,767 | 15,038 |
| `jc_activity_list` | 39 | 5,006 | 1,837 | 0 | 31,129 | 26,488 | 5,499 |
| `jc_catalog_search` | 15 | 4,092 | 925 | 0 | 5,563 | 3,778 | 2,115 |
| `jc_kpi_compute` | 5 | 3,452 | 3,400 | 0 | 7,807 | 7,212 | 705 |
| `jc_federation_graph` | 4 | 2,958 | 2,958 | 0 | 5,268 | 4,792 | 564 |
| `jc_resource_get` | 538 | 2,502 | 1,117 | 0 | 242,449 | 193,568 | 74,878 |
| `jc_change_get` | 11 | 1,732 | 899 | 0 | 2,882 | 4,021 | 1,391 |
| `jc_change_list` | 22 | 1,566 | 726 | 0 | 6,150 | 3,532 | 3,102 |

### Answer bytes the model read, by tool

| run | model | answer bytes | first | second | third |
| --- | --- | --- | --- | --- | --- |
| T-6037 run 1 | claude-haiku-5.5 | 591,870 | `jc_schema_get` 416,762 (70 %) | `jc_resource_list` 67,588 (11 %) | `jc_resource_get` 41,993 (7 %) |
| T-6037 run 1 | gemini-3.8-flash | 1,415,710 | `jc_schema_get` 1,013,858 (72 %) | `jc_resource_list` 155,067 (11 %) | `jc_resource_get` 149,037 (11 %) |
| T-6037 run 2 | claude-haiku-5.5 | 691,206 | `jc_schema_get` 492,339 (71 %) | `jc_resource_list` 57,219 (8 %) | `jc_resource_get` 56,262 (8 %) |
| T-6037 run 2 | gemini-3.8-flash | 1,348,306 | `jc_schema_get` 932,224 (69 %) | `jc_resource_list` 152,417 (11 %) | `jc_resource_get` 147,358 (11 %) |
| T-6040 final | claude-haiku-5.5 | 71,608 | `jc_schema_get` 40,000 (56 %) | `jc_resource_get` 10,582 (15 %) | `jc_change_plan` 9,567 (13 %) |
| T-6042 8 turns | gemini-3.8-flash | 715,500 | `jc_schema_get` 634,090 (89 %) | `jc_resource_get` 36,796 (5 %) | `jc_resource_list` 25,120 (4 %) |
| T-6042 16 turns | gemini-3.8-flash | 730,157 | `jc_schema_get` 611,379 (84 %) | `jc_resource_get` 45,928 (6 %) | `jc_resource_list` 29,611 (4 %) |

### Calls lost to repeats and refusals

| run | model | calls | same answer again | refused | argument refused | outside the grant | unknown kind | not served in the harness | unknown name | state conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-6037 run 1 | claude-haiku-5.5 | 219 | 15 | 48 | 12 | 3 | 19 | 4 | 10 | 0 |
| T-6037 run 1 | gemini-3.8-flash | 498 | 22 | 95 | 10 | 13 | 38 | 20 | 14 | 0 |
| T-6037 run 2 | claude-haiku-5.5 | 252 | 23 | 62 | 18 | 4 | 24 | 5 | 11 | 0 |
| T-6037 run 2 | gemini-3.8-flash | 517 | 21 | 93 | 7 | 12 | 39 | 18 | 16 | 1 |
| T-6040 final | claude-haiku-5.5 | 30 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| T-6042 8 turns | gemini-3.8-flash | 214 | 9 | 45 | 12 | 4 | 16 | 7 | 6 | 0 |
| T-6042 16 turns | gemini-3.8-flash | 286 | 16 | 58 | 19 | 4 | 12 | 6 | 16 | 1 |

### Failure classes of graded fails

| run | model | fails | answer too large | argument refused | auth | description misread | model API error | ran out of turns | stopped before a call | unclear error | wrong tool chosen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-6037 run 1 | claude-haiku-5.5 | 30 | 14 | 1 | 1 | 2 | 0 | 0 | 3 | 0 | 9 |
| T-6037 run 1 | gemini-3.8-flash | 34 | 18 | 2 | 0 | 5 | 2 | 3 | 1 | 1 | 2 |
| T-6037 run 2 | claude-haiku-5.5 | 25 | 10 | 2 | 2 | 3 | 0 | 0 | 2 | 2 | 4 |
| T-6037 run 2 | gemini-3.8-flash | 30 | 16 | 2 | 0 | 6 | 0 | 1 | 0 | 5 | 0 |
| T-6040 final | claude-haiku-5.5 | 5 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 |
| T-6042 8 turns | gemini-3.8-flash | 21 | 0 | 4 | 1 | 1 | 2 | 10 | 0 | 1 | 2 |
| T-6042 16 turns | gemini-3.8-flash | 19 | 0 | 3 | 1 | 4 | 3 | 3 | 2 | 1 | 2 |

### Every graded fail

| run | model | scenario | segment | calls | tokens | class |
| --- | --- | --- | --- | --- | --- | --- |
| T-6037 run 1 | claude-haiku-5.5 | S-01 | data-read | 5 | 14,020 | description misread |
| T-6037 run 1 | claude-haiku-5.5 | S-03 | data-read | 1 | 7,188 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-04 | data-read | 1 | 7,488 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-09 | context | 4 | 28,915 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-10 | context | 4 | 21,634 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-11 | context | 0 | 2,738 | stopped before a call |
| T-6037 run 1 | claude-haiku-5.5 | S-12 | context | 3 | 39,560 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-13 | context | 7 | 69,098 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-14 | context | 10 | 66,265 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-15 | context | 4 | 21,024 | description misread |
| T-6037 run 1 | claude-haiku-5.5 | S-16 | context | 6 | 28,639 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-17 | pipeline | 1 | 17,551 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-20 | pipeline | 6 | 37,027 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-22 | pipeline | 5 | 34,350 | argument refused |
| T-6037 run 1 | claude-haiku-5.5 | S-25 | pipeline | 4 | 37,989 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-27 | access | 3 | 7,280 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-28 | access | 6 | 66,816 | auth |
| T-6037 run 1 | claude-haiku-5.5 | S-29 | access | 2 | 15,752 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-33 | publish | 2 | 6,503 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-34 | publish | 2 | 6,556 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-35 | publish | 4 | 41,663 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-36 | publish | 7 | 23,377 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-37 | publish | 2 | 15,261 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-38 | apps | 12 | 127,056 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-41 | apps | 1 | 6,603 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-43 | operate | 0 | 3,600 | stopped before a call |
| T-6037 run 1 | claude-haiku-5.5 | S-45 | operate | 0 | 3,083 | stopped before a call |
| T-6037 run 1 | claude-haiku-5.5 | S-51 | pipeline | 1 | 17,930 | answer too large |
| T-6037 run 1 | claude-haiku-5.5 | S-52 | pipeline | 3 | 20,034 | wrong tool chosen |
| T-6037 run 1 | claude-haiku-5.5 | S-53 | operate | 6 | 19,613 | wrong tool chosen |
| T-6037 run 1 | gemini-3.8-flash | S-01 | data-read | 17 | 48,689 | description misread |
| T-6037 run 1 | gemini-3.8-flash | S-03 | data-read | 8 | 19,805 | description misread |
| T-6037 run 1 | gemini-3.8-flash | S-04 | data-read | 11 | 21,723 | description misread |
| T-6037 run 1 | gemini-3.8-flash | S-05 | data-read | 8 | 18,625 | unclear error |
| T-6037 run 1 | gemini-3.8-flash | S-09 | context | 10 | 49,458 | argument refused |
| T-6037 run 1 | gemini-3.8-flash | S-10 | context | 6 | 25,963 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-11 | context | 6 | 12,526 | wrong tool chosen |
| T-6037 run 1 | gemini-3.8-flash | S-12 | context | 7 | 53,103 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-13 | context | 1 | 992 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-14 | context | 15 | 62,594 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-15 | context | 8 | 30,233 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-16 | context | 8 | 46,821 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-17 | pipeline | 11 | 58,949 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-19 | pipeline | 9 | 10,895 | model API error |
| T-6037 run 1 | gemini-3.8-flash | S-20 | pipeline | 16 | 46,138 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-22 | pipeline | 10 | 55,902 | argument refused |
| T-6037 run 1 | gemini-3.8-flash | S-23 | pipeline | 4 | 13,718 | model API error |
| T-6037 run 1 | gemini-3.8-flash | S-25 | pipeline | 5 | 12,031 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-27 | access | 8 | 38,243 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-28 | access | 8 | 42,442 | ran out of turns |
| T-6037 run 1 | gemini-3.8-flash | S-29 | access | 17 | 78,288 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-33 | publish | 13 | 80,127 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-34 | publish | 11 | 42,521 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-35 | publish | 17 | 97,130 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-36 | publish | 17 | 45,472 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-37 | publish | 11 | 56,225 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-38 | apps | 17 | 84,432 | description misread |
| T-6037 run 1 | gemini-3.8-flash | S-41 | apps | 8 | 17,278 | ran out of turns |
| T-6037 run 1 | gemini-3.8-flash | S-42 | operate | 3 | 6,505 | description misread |
| T-6037 run 1 | gemini-3.8-flash | S-43 | operate | 3 | 6,856 | wrong tool chosen |
| T-6037 run 1 | gemini-3.8-flash | S-45 | operate | 0 | 1,611 | stopped before a call |
| T-6037 run 1 | gemini-3.8-flash | S-51 | pipeline | 3 | 11,007 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-52 | pipeline | 8 | 27,874 | answer too large |
| T-6037 run 1 | gemini-3.8-flash | S-53 | operate | 8 | 25,199 | ran out of turns |
| T-6037 run 2 | claude-haiku-5.5 | S-01 | data-read | 5 | 14,055 | description misread |
| T-6037 run 2 | claude-haiku-5.5 | S-03 | data-read | 2 | 11,316 | unclear error |
| T-6037 run 2 | claude-haiku-5.5 | S-09 | context | 4 | 40,826 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-11 | context | 0 | 2,909 | stopped before a call |
| T-6037 run 2 | claude-haiku-5.5 | S-13 | context | 11 | 105,972 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-14 | context | 11 | 85,915 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-15 | context | 6 | 37,856 | description misread |
| T-6037 run 2 | claude-haiku-5.5 | S-16 | context | 6 | 23,425 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-20 | pipeline | 10 | 98,884 | argument refused |
| T-6037 run 2 | claude-haiku-5.5 | S-22 | pipeline | 7 | 51,639 | argument refused |
| T-6037 run 2 | claude-haiku-5.5 | S-25 | pipeline | 2 | 14,281 | description misread |
| T-6037 run 2 | claude-haiku-5.5 | S-27 | access | 7 | 65,017 | wrong tool chosen |
| T-6037 run 2 | claude-haiku-5.5 | S-28 | access | 4 | 41,264 | auth |
| T-6037 run 2 | claude-haiku-5.5 | S-29 | access | 11 | 94,718 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-34 | publish | 2 | 6,863 | auth |
| T-6037 run 2 | claude-haiku-5.5 | S-35 | publish | 4 | 38,767 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-36 | publish | 3 | 27,406 | wrong tool chosen |
| T-6037 run 2 | claude-haiku-5.5 | S-37 | publish | 3 | 29,134 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-38 | apps | 12 | 129,565 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-41 | apps | 1 | 7,234 | wrong tool chosen |
| T-6037 run 2 | claude-haiku-5.5 | S-43 | operate | 0 | 4,261 | stopped before a call |
| T-6037 run 2 | claude-haiku-5.5 | S-45 | operate | 2 | 11,699 | unclear error |
| T-6037 run 2 | claude-haiku-5.5 | S-51 | pipeline | 1 | 17,850 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-52 | pipeline | 2 | 19,198 | answer too large |
| T-6037 run 2 | claude-haiku-5.5 | S-53 | operate | 5 | 21,682 | wrong tool chosen |
| T-6037 run 2 | gemini-3.8-flash | S-01 | data-read | 17 | 48,689 | description misread |
| T-6037 run 2 | gemini-3.8-flash | S-03 | data-read | 8 | 19,174 | unclear error |
| T-6037 run 2 | gemini-3.8-flash | S-04 | data-read | 8 | 18,667 | unclear error |
| T-6037 run 2 | gemini-3.8-flash | S-05 | data-read | 8 | 18,625 | unclear error |
| T-6037 run 2 | gemini-3.8-flash | S-09 | context | 14 | 52,176 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-11 | context | 8 | 18,737 | description misread |
| T-6037 run 2 | gemini-3.8-flash | S-12 | context | 7 | 53,103 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-13 | context | 14 | 81,317 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-14 | context | 8 | 55,180 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-15 | context | 10 | 40,980 | argument refused |
| T-6037 run 2 | gemini-3.8-flash | S-16 | context | 15 | 69,877 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-17 | pipeline | 8 | 76,320 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-20 | pipeline | 17 | 79,015 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-22 | pipeline | 8 | 50,892 | argument refused |
| T-6037 run 2 | gemini-3.8-flash | S-25 | pipeline | 3 | 10,168 | description misread |
| T-6037 run 2 | gemini-3.8-flash | S-27 | access | 8 | 49,148 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-28 | access | 8 | 41,179 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-29 | access | 13 | 104,150 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-34 | publish | 11 | 58,911 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-35 | publish | 10 | 32,821 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-36 | publish | 8 | 22,934 | description misread |
| T-6037 run 2 | gemini-3.8-flash | S-37 | publish | 8 | 42,991 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-38 | apps | 22 | 86,544 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-41 | apps | 12 | 34,292 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-42 | operate | 3 | 6,505 | description misread |
| T-6037 run 2 | gemini-3.8-flash | S-43 | operate | 10 | 37,298 | description misread |
| T-6037 run 2 | gemini-3.8-flash | S-45 | operate | 8 | 20,154 | unclear error |
| T-6037 run 2 | gemini-3.8-flash | S-51 | pipeline | 3 | 11,007 | answer too large |
| T-6037 run 2 | gemini-3.8-flash | S-52 | pipeline | 12 | 29,798 | ran out of turns |
| T-6037 run 2 | gemini-3.8-flash | S-53 | operate | 11 | 30,112 | unclear error |
| T-6040 final | claude-haiku-5.5 | S-12 | context | 3 | 41,554 | answer too large |
| T-6040 final | claude-haiku-5.5 | S-15 | context | 6 | 41,711 | description misread |
| T-6040 final | claude-haiku-5.5 | S-20 | pipeline | 7 | 63,360 | answer too large |
| T-6040 final | claude-haiku-5.5 | S-22 | pipeline | 4 | 34,529 | wrong tool chosen |
| T-6040 final | claude-haiku-5.5 | S-45 | operate | 3 | 21,697 | description misread |
| T-6042 8 turns | gemini-3.8-flash | S-04 | data-read | 8 | 14,890 | unclear error |
| T-6042 8 turns | gemini-3.8-flash | S-09 | context | 8 | 28,035 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-11 | context | 5 | 9,606 | wrong tool chosen |
| T-6042 8 turns | gemini-3.8-flash | S-14 | context | 10 | 86,191 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-15 | context | 6 | 13,454 | model API error |
| T-6042 8 turns | gemini-3.8-flash | S-17 | pipeline | 6 | 47,031 | wrong tool chosen |
| T-6042 8 turns | gemini-3.8-flash | S-20 | pipeline | 13 | 90,452 | argument refused |
| T-6042 8 turns | gemini-3.8-flash | S-22 | pipeline | 8 | 45,106 | argument refused |
| T-6042 8 turns | gemini-3.8-flash | S-27 | access | 13 | 100,010 | argument refused |
| T-6042 8 turns | gemini-3.8-flash | S-28 | access | 8 | 28,107 | argument refused |
| T-6042 8 turns | gemini-3.8-flash | S-29 | access | 16 | 90,120 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-34 | publish | 11 | 82,820 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-35 | publish | 8 | 23,127 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-36 | publish | 7 | 13,581 | description misread |
| T-6042 8 turns | gemini-3.8-flash | S-37 | publish | 13 | 77,435 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-38 | apps | 8 | 11,236 | model API error |
| T-6042 8 turns | gemini-3.8-flash | S-41 | apps | 10 | 32,592 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-43 | operate | 11 | 26,146 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-45 | operate | 5 | 8,960 | auth |
| T-6042 8 turns | gemini-3.8-flash | S-52 | pipeline | 8 | 35,505 | ran out of turns |
| T-6042 8 turns | gemini-3.8-flash | S-53 | operate | 8 | 16,062 | ran out of turns |
| T-6042 16 turns | gemini-3.8-flash | S-04 | data-read | 16 | 45,298 | description misread |
| T-6042 16 turns | gemini-3.8-flash | S-09 | context | 16 | 80,166 | ran out of turns |
| T-6042 16 turns | gemini-3.8-flash | S-11 | context | 0 | 1,193 | stopped before a call |
| T-6042 16 turns | gemini-3.8-flash | S-15 | context | 13 | 28,713 | model API error |
| T-6042 16 turns | gemini-3.8-flash | S-17 | pipeline | 7 | 39,833 | argument refused |
| T-6042 16 turns | gemini-3.8-flash | S-20 | pipeline | 21 | 185,435 | argument refused |
| T-6042 16 turns | gemini-3.8-flash | S-22 | pipeline | 16 | 115,017 | argument refused |
| T-6042 16 turns | gemini-3.8-flash | S-27 | access | 16 | 202,034 | ran out of turns |
| T-6042 16 turns | gemini-3.8-flash | S-28 | access | 16 | 144,524 | ran out of turns |
| T-6042 16 turns | gemini-3.8-flash | S-29 | access | 13 | 46,455 | model API error |
| T-6042 16 turns | gemini-3.8-flash | S-35 | publish | 18 | 168,984 | description misread |
| T-6042 16 turns | gemini-3.8-flash | S-36 | publish | 9 | 34,121 | description misread |
| T-6042 16 turns | gemini-3.8-flash | S-37 | publish | 5 | 25,156 | model API error |
| T-6042 16 turns | gemini-3.8-flash | S-38 | apps | 25 | 134,130 | description misread |
| T-6042 16 turns | gemini-3.8-flash | S-41 | apps | 9 | 31,612 | wrong tool chosen |
| T-6042 16 turns | gemini-3.8-flash | S-43 | operate | 2 | 7,456 | wrong tool chosen |
| T-6042 16 turns | gemini-3.8-flash | S-45 | operate | 5 | 8,916 | auth |
| T-6042 16 turns | gemini-3.8-flash | S-52 | pipeline | 0 | 2,008 | stopped before a call |
| T-6042 16 turns | gemini-3.8-flash | S-53 | operate | 24 | 83,861 | unclear error |

<!-- connector-efficiency:end -->

## 4. The five changes

Ranked by what they save. Each is a task in group `connectors` and in T-5963's `depends-on`.

1. **`jc_schema_get` answers a compact schema** (T-6057). It is the largest answer by far: 70 % of the answer bytes the model read in every T-6037 run, 84 % and 89 % in the T-6042 runs, mean 27,789 bytes per call there. 126 of its answers were cut before T-6042 raised the cap, and a cut schema sent the model back for another. Answer the required fields, each field's type in one line and one minimal valid manifest; a `path` argument returns one field's full schema. A 3,000-byte answer saves about 24,000 bytes per call, read again in every later turn.
2. **Tool definitions shrink** (T-6058). The door re-sends the definitions every turn. The whole Portal set is 73 tools and 62,157 bytes, about 22,000 tokens per turn at haiku's 2.78 bytes per token; `jc_change_plan` alone is 2,384 bytes in every segment. On the public door 18,343 of the 28,352 definition bytes are input schemas, and `initialize` adds 4,261 bytes of instructions before the first question. By the estimate above, definitions are 51 % of haiku's tokens in T-6037 run 2. Move per-property prose the descriptions repeat out of the schemas, share one definition of the NGSI-LD query parameters, and gate each door's bytes in a test.
3. **The `kind` argument lists the kinds the caller may read** (T-6059). Models guessed kinds that do not exist (`Role`, `RoleBinding`, `Blueprint`, `Mapping`): 63 "unknown kind" refusals in T-6037 run 2, 12 in the 16-turn run, each a lost turn. Since T-6042 the refusal names the readable kinds; an `enum` in `jc_resource_list` and `jc_resource_get` input schemas, built per caller, saves the call itself.
4. **One copy of each answer** (T-6060). Every Portal answer carries its data twice, as text and as `structuredContent`: 534,782 and 529,617 bytes for `jc_schema_get`, 242,449 and 193,568 for `jc_resource_get`, plus 74,878 bytes of `_meta` grounding on the latter. The public `list_endpoints` answer is 24,396 bytes for 9,821 bytes of text. Claude clients hand the model the text alone, so the copy costs wire bytes and the client's output cap; a client that passes `structuredContent` pays it twice in tokens. Keep `structuredContent` for tools with an `outputSchema`, send the grounding once per session.
5. **The public `list_endpoints` answers a page** (T-6061). Its anonymous answer lists every public Endpoint, 50 rows and 24,396 bytes, the second largest answer a public client reads after a schema. A default page of 20 rows with a cursor and the `search` tool named for narrowing keeps the first call under 10,000 bytes.

What the tables also show, outside the five: the 8-turn cap ends gemini runs early (10 of 21 fails in the 8-turn run, 3 of 19 at 16 turns), which is the owner's model choice recorded in T-6042; "not served in the harness" refusals (5 to 20 per run) are the lane's missing gateway for `jc_data_query`, which T-5962 covers live.

## Related

- [07-workflow-coverage.md](07-workflow-coverage.md) — the scenarios the model lane runs.
- [02-conformance-tests.md](02-conformance-tests.md) — the MCP conformance suite of the public door.
- [agents.md](../Requirements/agents.md) — AG-146, the schema tool this page measures.
