# AltFix: Automatic Alt-Text Generation for Documentation Images

## Problem
Thousands of README and docs images have missing or low-quality alt text (e.g., "image", "screenshot"). Screen-reader users receive no meaningful descriptions, creating a significant accessibility barrier. Current solutions rely on cloud APIs or require manual intervention at scale.

## Goal (One Sentence)
Scan documentation repositories for images with missing/poor alt text, generate concise alternative text using a local open-weight vision model with surrounding document context, and output reviewable patches that modify only the alt attributes.

## Success Targets (Measurable)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Detection recall | ≥ 95% | vs hand-labeled evaluation set |
| Quality-check pass rate | 100% | non-empty, ≤125 chars, no forbidden patterns |
| Diff purity | 100% | only alt text bytes changed |
| Human rating (30 samples) | ≥ 4.5/5 avg | 0=wrong, 1=ok, 2=good |

## Non-Goals
- No web UI, cloud APIs, or training
- No LangChain or external orchestration frameworks
- Badge/shields.io images: handled by simple rules, not the model
- Text-in-image OCR accuracy is "good enough" not perfect

## Deliverables
- `altfix` Python package (src layout, pyproject.toml)
- CLI commands: `scan`, `fix --dry-run`, `fix --apply`, `pr`, `review`
- Evaluation suite with real/realistic fixture repos and expected.json
- README with installation, quickstart, results table, model/license links
- Open-source code (MIT), local-only model inference (Ollama)

## Architecture Summary
```
scan.py      → find images in docs, classify quality
classify.py  → rule-based: missing/low/ok/decorative
describe.py  → Ollama client with context-aware prompts
quality.py   → validate output, retry on failure
patch.py     → character-span edits, idempotent diff
cli.py       → typer CLI, gh CLI integration for PRs
eval/        → fixture repos, expected.json, run.py, rate.py
```
