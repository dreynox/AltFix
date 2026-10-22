# Graph Report - MLH  (2026-10-22)

## Corpus Check
- Corpus is ~24,014 words - fits in a single context window. You may not need a graph.

## Summary
- 541 nodes · 1114 edges · 33 communities (17 shown, 16 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Patching and Edits
- Quality Checking
- Client and Caching
- Scanning Tests
- Pipeline Orchestration
- Image Classification
- CLI Interface
- Configuration Management
- Scanning Logic
- Eval Fixtures
- Core Utilities
- Client Networking
- Eval Metrics
- Image Tasks
- File Iteration
- Local Vision Client
- Planning and Results
- Project Goals
- Deployment Process
- Package Root
- Smoke Test Dashboard

## God Nodes (most connected - your core abstractions)
1. `plan_edit()` - 30 edges
2. `run_fix()` - 30 edges
3. `DescriptionCache` - 23 edges
4. `Config` - 23 edges
5. `load_config()` - 22 edges
6. `scan_markdown()` - 21 edges
7. `check()` - 19 edges
8. `ImageOccurrence` - 19 edges
9. `scan_text()` - 19 edges
10. `occurrence_for()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `run()` --uses--> `LocalVisionClient`  [INFERRED]
  eval/run.py → src/altfix/client.py
- `TestClient` --uses--> `ModelUnavailable`  [INFERRED]
  tests/test_client_cache.py → src/altfix/client.py
- `StubClient` --uses--> `ModelResponse`  [INFERRED]
  tests/test_pipeline.py → src/altfix/client.py
- `make_client()` --uses--> `LocalVisionClient`  [INFERRED]
  tests/test_client_cache.py → src/altfix/client.py
- `make_client()` --uses--> `Config`  [INFERRED]
  tests/test_client_cache.py → src/altfix/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **AltFix Implementation Phases** — plan_phase_1_scaffold, plan_phase_2_scanner_classifier_patcher, plan_phase_3_describer_quality_cache, plan_phase_4_evaluation_infrastructure, plan_phase_5_iterate_prompts_rules, plan_phase_6_pr_review_commands, plan_phase_7_demo_polish [EXTRACTED 1.00]

## Communities (33 total, 16 thin omitted)

### Community 0 - "Patching and Edits"
Cohesion: 0.06
Nodes (23): AltEdit, apply_edits(), build_patch(), diff_only_alt_text(), escape_html_attr(), escape_markdown_alt(), escape_rst_alt(), FilePatch (+15 more)

### Community 1 - "Quality Checking"
Cohesion: 0.06
Nodes (12): check(), clean(), QualityResult, _strip_filler(), _strip_markdown(), strip_think(), truncate(), validate() (+4 more)

### Community 2 - "Client and Caching"
Cohesion: 0.08
Nodes (13): ImageOutcome, run(), CacheStats, DescriptionCache, ModelResponse, ModelUnavailable, build_context(), Describer (+5 more)

### Community 3 - "Scanning Tests"
Cohesion: 0.08
Nodes (8): scan_html(), scan_markdown(), scan_rst(), TestCodeFences, TestHtml, TestMarkdown, TestRst, TestSpans

### Community 4 - "Pipeline Orchestration"
Cohesion: 0.09
Nodes (8): resolve_image_path(), run_fix(), sample_image(), docs(), make_config(), StubClient, TestCli, TestPipeline

### Community 5 - "Image Classification"
Cohesion: 0.08
Nodes (10): _basename(), classify(), ImageClass, is_badge(), is_decorative(), is_filename_echo(), is_generic(), _stem() (+2 more)

### Community 6 - "CLI Interface"
Cohesion: 0.12
Nodes (10): _config(), _default_pr_body(), demo(), fix(), model_info(), pr(), _print_manual_pr(), review() (+2 more)

### Community 7 - "Configuration Management"
Cohesion: 0.12
Nodes (6): _as_bool(), Config, _find_config_file(), load_config(), _read_config_file(), TestConfig

### Community 8 - "Scanning Logic"
Cohesion: 0.15
Nodes (12): _block_ranges(), _html_context(), ImageOccurrence, _in_ranges(), _line_of(), _markdown_context(), _rst_context(), scan_html() (+4 more)

### Community 9 - "Eval Fixtures"
Cohesion: 0.13
Nodes (10): architecture_diagram(), badge(), bar_chart(), dashboard(), _font(), line_chart(), logo(), photo_scene() (+2 more)

### Community 10 - "Core Utilities"
Cohesion: 0.21
Nodes (3): hash_bytes(), hash_file(), hash_text()

### Community 11 - "Client Networking"
Cohesion: 0.13
Nodes (4): encode_image(), make_client(), TestClient, handler()

### Community 12 - "Eval Metrics"
Cohesion: 0.13
Nodes (6): EvalResult, load_expected(), load_ratings(), relative_to_fixture(), render_markdown(), write_results()

### Community 13 - "Image Tasks"
Cohesion: 0.15
Nodes (4): Description, ImageTask, render_diff(), RunResult

### Community 14 - "File Iteration"
Cohesion: 0.23
Nodes (5): iter_doc_files(), os_walk(), scan_file(), scan_path(), ScanResult

### Community 16 - "Planning and Results"
Cohesion: 0.20
Nodes (10): AltFix Implementation Plan, Phase 1: Scaffold, Phase 2: Scanner + Classifier + Patcher, Phase 3: Describer + Quality + Cache, Phase 4: Evaluation Infrastructure, Phase 5: Iterate on Prompts & Rules, Phase 6: PR + Review Commands, Phase 7: Demo + Polish (+2 more)

### Community 20 - "Project Goals"
Cohesion: 0.50
Nodes (4): AltFix Problem Statement & Goals, AltFix Goal, Architecture Summary, Success Targets

## Knowledge Gaps
- **14 isolated node(s):** `altfix`, `AltFix Goal`, `Success Targets`, `Architecture Summary`, `Phase 1: Scaffold` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 193 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `scan_text()` connect `Scanning Logic` to `Patching and Edits`, `Client and Caching`, `Scanning Tests`, `Pipeline Orchestration`, `File Iteration`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `run_fix()` (e.g. with `ImageClass` and `Config`) actually correct?**
  _`run_fix()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `altfix`, `AltFix Goal`, `Success Targets` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Patching and Edits` be split into smaller, more focused modules?**
  _Cohesion score 0.06128364389233954 - nodes in this community are weakly interconnected._
- **Why does `plan_edit()` connect `Patching and Edits` to `Client and Caching`, `Pipeline Orchestration`, `CLI Interface`, `Scanning Logic`, `Core Utilities`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `DescriptionCache` (e.g. with `run()` and `Describer`) actually correct?**
  _`DescriptionCache` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `Quality Checking` be split into smaller, more focused modules?**
  _Cohesion score 0.06464646464646465 - nodes in this community are weakly interconnected._