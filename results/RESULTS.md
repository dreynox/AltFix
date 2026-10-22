# AltFix evaluation results

Every number below comes from the run recorded in `results/results.json`.

## Run configuration

| Setting | Value |
| --- | --- |
| Model | `qwen3.5-9b` |
| Quantization | (not recorded) |
| Endpoint | `http://localhost:1234/v1` |
| Context length | 4096 |
| Temperature | 0.2 |
| Seed | 42 |
| Max tokens | 512 |
| Reasoning effort | none |
| Prompt version | `v1` |
| Cache | enabled |
| Started | 2026-10-22T12:02:06.263814+00:00 |
| Finished | 2026-10-22T12:03:19.027114+00:00 |

## Metrics

| Metric | Value |
| --- | --- |
| Images scanned | 28 |
| Images in ground truth | 28 |
| Detection recall | 100.0% |
| Detection precision | 100.0% |
| Classification accuracy | 100.0% |
| Quality check pass rate | 0.0% |
| Diff only touches alt text | 0.0% |
| Mean latency per image | 5594 ms |
| Median latency per image | 5599 ms |
| Cache hit rate | 0.0% |
| Images needing review | 13 |
| Human rating (0-2) | not rated yet (fill in `eval/ratings.csv`) |

## Detection detail

- True positives (flagged and should be fixed): 13
- False positives (flagged but should not be): 0
- False negatives (should be fixed but not flagged): 0
- True negatives: 15

## Generated alt text

| File | Line | Source | Old alt | New alt | Attempts | Cached | Latency (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| repo_charts/README.md | 7 | `docs/quarterly-revenue.png` | (empty) | [needs review] | 1 | no | 5277 |
| repo_charts/README.md | 19 | `docs/terminal-output.png` | (empty) | [needs review] | 1 | no | 5068 |
| repo_charts/README.md | 23 | `docs/terminal-output.png` | terminal | [needs review] | 1 | no | 5110 |
| repo_dashboard/README.md | 15 | `docs/dashboard.png` | screenshot | [needs review] | 1 | no | 5187 |
| repo_dashboard/README.md | 25 | `docs/dashboard.png` | (empty) | [needs review] | 1 | no | 6041 |
| repo_html/docs/index.html | 11 | `architecture.png` | (empty) | [needs review] | 1 | no | 5939 |
| repo_html/docs/index.html | 15 | `architecture.png` | (empty) | [needs review] | 1 | no | 6035 |
| repo_mixed/README.md | 17 | `docs/landscape.png` | diagram | [needs review] | 1 | no | 6110 |
| repo_mixed/README.md | 19 | `docs/landscape.png` | Screenshot | [needs review] | 1 | no | 5670 |
| repo_rst/docs/report.rst | 6 | `report.png` | (empty) | [needs review] | 1 | no | 5530 |
| repo_rst/docs/report.rst | 10 | `report.png` | (empty) | [needs review] | 1 | no | 5416 |
| repo_screenshots/README.md | 5 | `docs/login-screen.png` | (empty) | [needs review] | 1 | no | 5599 |
| repo_screenshots/README.md | 9 | `docs/login-screen.png` | login-screen | [needs review] | 1 | no | 5733 |
