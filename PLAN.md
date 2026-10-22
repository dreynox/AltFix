# Plan: AltFix Implementation Phases

## Pre-work (Step 0) - DONE
- [x] AIM.md with problem, goal, targets, non-goals, deliverables
- [x] PLAN.md created

## Phase 1: Scaffold (Estimated: 30 min)
**Goal**: Project layout, pyproject.toml, MIT LICENSE, core Ollama client.

### Tasks
1. Create project structure: `src/altfix/`, `eval/`, `tests/`
2. Write `pyproject.toml` with dependencies (httpx, rich, typer, markdown-it-py, pytest)
3. Add MIT LICENSE
4. Implement `OllamaVisionClient` in `src/altfix/client.py` with:
   - `/api/chat` endpoint calls
   - Base64 image encoding
   - Configurable model name, temperature, timeout
   - Image resizing for large files
5. Smoke test: describe a sample image locally

### Deliverables
- Working package skeleton
- One verified image description via Ollama

---

## Phase 2: Scanner + Classifier + Patcher (Estimated: 45 min)
**Goal**: `altfix scan <path>` lists all problematic images with context.

### Tasks
1. **scan.py**: Regex/parse for:
   - Markdown inline: `![alt](src)`
   - Reference-style: `[text]: src`
   - HTML: `<img ...>`, `<picture>`
   - Extract: file, line/col span, current alt, src, surrounding context (heading, paragraph, caption, link text)
   - Skip fenced code blocks
2. **classify.py**: Rule-based classifier:
   - Missing: no alt or alt=""
   - Low-quality: "image", "screenshot", filename, <3 chars
   - OK: descriptive, > 10 chars
   - Decorative: badges (shields.io), spacers, emoji-only
3. **patch.py**: Character-span editor:
   - Markdown inline images
   - HTML img attributes
   - Idempotent: running twice = no change
   - Byte-exact outside edit spans
4. **Tests**: pytest for all three modules with synthetic inputs

### Deliverables
- `altfix scan` works on fixture repos
- All tests passing

---

## Phase 3: Describer + Quality + Cache (Estimated: 40 min)
**Goal**: `altfix fix --dry-run` generates and validates alt text end-to-end.

### Tasks
1. **describe.py**: Ollama integration
   - Prompt uses surrounding context (heading, paragraph, caption, link text)
   - Request: concise objective description ≤ 125 chars
   - Specifics: visible text in screenshots, data trends for charts, diagram type + entities
2. **quality.py**: Post-process validation
   - Strip quotes/markdown prefixes ("image of", "picture of")
   - Collapse whitespace, enforce length limit
   - Reject filename echoes (base64 hash of src path)
   - Retry once with stricter prompt if invalid
   - Fallback to safe label + flag for review on double failure
3. **Cache**: Disk cache by image_hash + context_hash (deterministic reruns)

### Deliverables
- `altfix fix --dry-run` end-to-end working
- Cache validated (rerun = instant, same output)

---

## Phase 4: Evaluation Infrastructure (Estimated: 30 min)
**Goal**: Create eval set and runners.

### Tasks
1. **eval/fixtures/**: 6 small repos' docs:
   - screenshots/, diagrams/, charts/, logos/, badges/, mixed/
   - Permissively licensed or synthetic
2. **expected.json**: Hand-labeled ground truth (file, line, should_fix: bool)
3. **eval/run.py**: Compute metrics:
   - Detection recall/precision
   - Quality-check pass rate
   - Diff-only-touches-alt-text
   - Mean latency per image
   - Cache hit rate
4. **eval/rate.py**: Generate CSV of 30 random (image, desc) pairs for manual 0/1/2 scoring

### Deliverables
- Eval suite runnable
- First results saved to results/results.json

---

## Phase 5: Iterate on Prompts & Rules (Estimated: 60 min)
**Goal**: Improve quality based on eval failures.

### Tasks
1. Analyze Phase 4 results, identify failure patterns
2. Update prompts in `describe.py` (generic improvements only)
3. Refine quality rules in `classify.py`/`quality.py`
4. Re-run eval for both models (qwen2.5vl:7b, gemma3:4b)
5. Compare results table

### Deliverables
- Improved pass rate
- Side-by-side model comparison

---

## Phase 6: PR + Review Commands (Estimated: 20 min)
**Goal**: Complete CLI feature set.

### Tasks
1. **altfix pr <path>**:
   - Create branch, commit changes with gh CLI if available
   - Otherwise print exact manual steps
2. **altfix review <path>**:
   - Interactive rich UI: accept/edit/skip per image
3. Add action.yml stretch (if all else green)

### Deliverables
- All CLI commands working
- GitHub Action wrapper (stretch)

---

## Phase 7: Demo + Polish (Estimated: 45 min)
**Goal**: Production-ready README and docs.

### Tasks
1. `altfix demo`: bundled sample, before/after with rich
2. README.md:
   - One-paragraph pitch
   - 3-command quickstart
   - Results table (real numbers from results/)
   - What we built vs reused
   - Model names + license links
   - Dependencies list
   - Reproduction steps
   - Limitations (text accuracy, charts)
   - Privacy note (everything local)
3. CONTRIBUTING.md: good-first-issue ideas

### Deliverables
- Complete README with all sections
- Final results table populated

---

## Commit Convention
Each phase commit message format: `phase N: <summary>`

Example:
```
git add .
git commit -m "phase 1: scaffold - pyproject.toml, MIT LICENSE, Ollama client"
```

---

## Hard Rules Checklist
- [ ] No fabricated numbers (all from results/)
- [ ] No invented image contents (fail safely)
- [ ] pytest for scan, classify, quality, patch with synthetic inputs
- [ ] Tests after each phase, fix broken code before proceeding
- [ ] Configurable model name (default qwen2.5vl:7b)
- [ ] Local inference only (no data leaves machine)
