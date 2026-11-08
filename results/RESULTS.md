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
| Started | 2026-11-08T15:30:49.761975+00:00 |
| Finished | 2026-11-08T15:30:49.776983+00:00 |

## Metrics

| Metric | Value |
| --- | --- |
| Images scanned | 28 |
| Images in ground truth | 28 |
| Detection recall | 100.0% |
| Detection precision | 100.0% |
| Classification accuracy | 100.0% |
| Quality check pass rate | 100.0% |
| Diff only touches alt text | 100.0% |
| Mean latency per image | 0 ms |
| Median latency per image | 0 ms |
| Cache hit rate | 100.0% |
| Images needing review | 0 |
| Human rating (0-2) | 1.9231 / 2 over 13 samples |

## Detection detail

- True positives (flagged and should be fixed): 13
- False positives (flagged but should not be): 0
- False negatives (should be fixed but not flagged): 0
- True negatives: 15

## Generated alt text

| File | Line | Source | Old alt | New alt | Attempts | Cached | Latency (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| repo_charts/README.md | 7 | `docs/quarterly-revenue.png` | (empty) | Bar chart of quarterly revenue comparing Q1 through Q4 | 1 | yes | 0 |
| repo_charts/README.md | 19 | `docs/terminal-output.png` | (empty) | Terminal window showing deployment steps and build output | 1 | yes | 0 |
| repo_charts/README.md | 23 | `docs/terminal-output.png` | terminal | Terminal window showing deployment steps and build output | 1 | yes | 0 |
| repo_dashboard/README.md | 15 | `docs/dashboard.png` | screenshot | Acme Analytics dashboard showing $48,210 total revenue and active users | 1 | yes | 0 |
| repo_dashboard/README.md | 25 | `docs/dashboard.png` | (empty) | Acme Analytics dashboard showing $48,210 total revenue and active users | 1 | yes | 0 |
| repo_html/docs/index.html | 11 | `architecture.png` | (empty) | Flowchart diagram illustrating the system architecture | 1 | yes | 0 |
| repo_html/docs/index.html | 15 | `architecture.png` | (empty) | Flowchart diagram illustrating the system architecture | 1 | yes | 0 |
| repo_mixed/README.md | 17 | `docs/landscape.png` | diagram | Landscape illustration featuring snow-capped mountains and pine tree | 1 | yes | 0 |
| repo_mixed/README.md | 19 | `docs/landscape.png` | Screenshot | Landscape illustration featuring snow-capped mountains and pine tree | 1 | yes | 0 |
| repo_rst/docs/report.rst | 6 | `report.png` | (empty) | Line graph displaying weekly active user trends from Monday to Sunday | 1 | yes | 0 |
| repo_rst/docs/report.rst | 10 | `report.png` | (empty) | Line graph displaying weekly active user trends from Monday to Sunday | 1 | yes | 0 |
| repo_screenshots/README.md | 5 | `docs/login-screen.png` | (empty) | Login screen with username, password fields and sign in button | 1 | yes | 0 |
| repo_screenshots/README.md | 9 | `docs/login-screen.png` | login-screen | Login screen with username, password fields and sign in button | 1 | yes | 0 |
